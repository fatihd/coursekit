"""Local, line-level OCR (tesseract) on the original scan, cropped with the DjVu line boxes.

The language per line follows the candidate classifier (Hebrew vs English side of the exercise).
Bitmaps come from the PDF's own page image at DjVu resolution (pdfimages), so DjVu boxes map 1:1;
if no such image exists the page is rendered with pdftoppm at a matching width.
Results are cached in the `ocr` table and preferred over the DjVu text when items are (re)derived.
"""
import json, os, re, shutil, subprocess, glob
from concurrent.futures import ThreadPoolExecutor
from . import detect
from .db import now

ENGINE = "tesseract"
DEFAULTS = {"he": "heb", "la": "eng+heb", "psm": ["7", "6", "13"], "pad": 10, "workers": 4,
            "he_variants": [["heb", "7"], ["heb", "6"], ["heb", "13"], ["heb+script/Hebrew", "6"]]}
POINTS = re.compile(r"[\u05b0-\u05bc\u05c1\u05c2\u05c7]")
LETTERS = re.compile(r"[\u05d0-\u05ea]")
FINALS = str.maketrans("ךםןףץ", "כמנפצ")

def _skel(t):
    return "".join(LETTERS.findall(detect.clean_ocr(t))).translate(FINALS)

def pick_hebrew(texts):
    """Among OCR variants of one Hebrew line keep the best-pointed one whose consonants agree with the consensus."""
    import difflib
    c = [t for t in texts if len(LETTERS.findall(t)) >= 2]
    if not c: return next((t for t in texts if t), "")
    sk = [_skel(t) for t in c]
    sim = lambda a, b: difflib.SequenceMatcher(None, a, b).ratio()
    medoid = max(range(len(c)), key=lambda i: sum(sim(sk[i], sk[j]) for j in range(len(c)) if j != i))
    dens = lambda t: len(POINTS.findall(t)) / max(1, len(LETTERS.findall(t)))
    ok = [i for i in range(len(c)) if sim(sk[i], sk[medoid]) >= 0.85]
    return c[max(ok, key=lambda i: (dens(c[i]), i == medoid))]

def available(need=("heb", "eng")):
    if not (shutil.which("tesseract") and shutil.which("pdfimages") and shutil.which("pdftoppm")):
        return {"ok": False, "why": "needs tesseract + poppler (brew install tesseract poppler)"}
    langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout.split()
    missing = [l for l in need if l not in langs]
    return {"ok": not missing, "engine": ENGINE, "why": f"missing tessdata: {missing}" if missing else ""}

def _read_pbm(path):
    d = open(path, "rb").read()
    tok, pos = [], 0
    while len(tok) < 3:
        m = re.compile(rb"\s*(#[^\n]*\n\s*)*(\S+)").match(d, pos); tok.append(m.group(2)); pos = m.end()
    assert tok[0] == b"P4", "not a P4 bitmap"
    w, h = int(tok[1]), int(tok[2]); data = d[pos + 1:]
    rb = (w + 7) // 8
    sample = data[: rb * min(h, 600)]
    inv = sum(bin(c).count("1") for c in sample) * 2 > len(sample) * 8      # mostly "black" => text is 0 bits
    return {"w": w, "h": h, "rb": rb, "data": data, "inv": inv}

def page_bitmap(pdf, page, cache, w=None, h=None):
    """1-bit page image whose pixel grid matches the DjVu coordinates (w x h)."""
    os.makedirs(cache, exist_ok=True)
    out = os.path.join(cache, f"{os.path.splitext(os.path.basename(pdf))[0]}-{page:04d}.pbm")
    if not os.path.exists(out):
        tmp = os.path.join(cache, f"_img{page}")
        subprocess.run(["pdfimages", "-f", str(page), "-l", str(page), pdf, tmp], capture_output=True, check=False)
        found = None
        for f in sorted(glob.glob(tmp + "-*.pbm")):
            hd = open(f, "rb").read(64).split()
            if w is None or (int(hd[1]) == w and int(hd[2]) == h): found = f; break
        if found: os.replace(found, out)
        for f in glob.glob(tmp + "-*"): os.remove(f)
        if not found:
            info = subprocess.run(["pdfinfo", "-f", str(page), "-l", str(page), pdf], capture_output=True, text=True).stdout
            m = re.search(r"Page\s+\d+\s+size:\s+([\d\.]+)\s+x", info) or re.search(r"Page size:\s+([\d\.]+)\s+x", info)
            dpi = round(w / (float(m.group(1)) / 72)) if (w and m) else 300
            subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(dpi), "-mono", "-singlefile", pdf, out[:-4]],
                           capture_output=True, check=False)
    return _read_pbm(out)

def _crop(bm, box):
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(bm["w"], x1), min(bm["h"], y1)
    b0, b1 = x0 // 8, (x1 + 7) // 8; rb, d = bm["rb"], bm["data"]
    rows = [d[r * rb + b0: r * rb + b1] for r in range(y0, y1)]
    if bm["inv"]: rows = [bytes(255 - c for c in r) for r in rows]
    return b"P4\n%d %d\n" % ((b1 - b0) * 8, y1 - y0) + b"".join(rows)

def _tess(img, lang, psm):
    r = subprocess.run(["tesseract", "stdin", "stdout", "-l", lang, "--psm", psm], input=img, capture_output=True,
                       env={**os.environ, "OMP_THREAD_LIMIT": "1"}, timeout=60)
    return detect.norm(r.stdout.decode("utf8", "replace").replace("\n", " ")).replace("‎", "").replace("‏", "")

def _tess_line(img, lang, psms):
    """psm 7 (single line) returns nothing when a crop catches bits of neighbouring lines; fall back to 6, then 13."""
    for psm in ([psms] if isinstance(psms, str) else psms):
        t = _tess(img, lang, str(psm))
        if re.search(r"\w", t): return t
    return ""

def line_boxes(lines):
    """DjVu line boxes, de-overlapped vertically (some boxes swallow part of the next line)."""
    out = []
    for i, l in enumerate(lines):
        b = list(l.get("b") or [])
        if not b: out.append(None); continue
        nxt = next((x["b"] for x in lines[i + 1:] if x.get("b") and x["b"][1] > b[1] + 10), None)
        if nxt and nxt[1] < b[3] and nxt[1] - b[1] > 25: b[3] = nxt[1] + 4
        prv = next((x["b"] for x in reversed(lines[:i]) if x.get("b") and x["b"][1] < b[1] - 10 and x["b"][0] < b[2] and x["b"][2] > b[0]), None)
        if prv and prv[3] > b[1] and b[3] - prv[3] > 25: b[1] = prv[3] - 4
        out.append(b)
    return out

def _conf(con):
    prof = json.loads(con.execute("SELECT v FROM meta WHERE k='profile'").fetchone()["v"])
    C = dict(DEFAULTS); C.update(prof.get("ocr") or {}); return C

LANGS = set(subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout.split()) if shutil.which("tesseract") else set()

def ocr_lines(con, source, todo, project, force=False):
    """todo: [(scan, line, side)] with side 'he'/'la'/None. OCRs uncached lines of one source; returns count."""
    C = _conf(con)
    src = con.execute("SELECT * FROM source WHERE id=?", (source,)).fetchone()
    if not src["pdf"]: raise RuntimeError(f"source {source} has no 'pdf' in the profile")
    by_scan = {}
    for scan, i, side in todo:
        if (not force or (force == "he" and side != "he")) and con.execute("SELECT 1 FROM ocr WHERE source=? AND scan=? AND line=? AND engine=?", (source, scan, i, ENGINE)).fetchone():
            continue
        by_scan.setdefault(scan, []).append((i, C["he"] if side == "he" else C["la"]))
    results, cache, p = [], os.path.join(project, "cache"), int(C["pad"])
    for scan, items in by_scan.items():
        r = con.execute("SELECT lines, w, h FROM page WHERE source=? AND scan=?", (source, scan)).fetchone()
        if not r: continue
        boxes = line_boxes(json.loads(r["lines"]))
        bm = page_bitmap(src["pdf"], scan + (src["pdf_delta"] or 0), cache, r["w"], r["h"])
        work = [(i, lang, _crop(bm, [boxes[i][0] - p, boxes[i][1] - p, boxes[i][2] + p, boxes[i][3] + p])) for i, lang in items if i < len(boxes) and boxes[i]]
        def run(w):
            if w[1] == C["he"]:
                return pick_hebrew([_tess(w[2], lang, str(psm)) for lang, psm in C["he_variants"] if lang in LANGS])
            return _tess_line(w[2], w[1], C["psm"])
        with ThreadPoolExecutor(int(C["workers"])) as ex:
            texts = list(ex.map(run, work))
        L0 = json.loads(r["lines"])
        results += [(scan, i, lang, t, json.dumps(L0[i].get("b"))) for (i, lang, _), t in zip(work, texts)]
    con.executemany("INSERT OR REPLACE INTO ocr(source,scan,line,engine,lang,text,ts,box) VALUES(?,?,?,?,?,?,?,?)",
                    [(source, s, i, ENGINE, lang, t, now(), bx) for s, i, lang, t, bx in results])
    con.commit()
    return len(results)

def _span_todo(pages, s_scan, s_line, e_scan, e_line, skip_first):
    span = detect.span_lines(pages, s_scan, s_line, e_scan, e_line, skip_first=skip_first)
    return [(s, i, side) for (s, i, _), side in zip(span, detect.line_sides(span))]

def ocr_block(con, bid, project, force=False, key=True, log=print):
    """OCR an exercise block (book lines) and, with key=True, its key segments (or the guessed key pages)."""
    b = con.execute("SELECT * FROM block WHERE id=?", (bid,)).fetchone()
    pages = detect.load_pages(con, b["source"])
    n_book = ocr_lines(con, b["source"], _span_todo(pages, b["start_scan"], b["start_line"], b["end_scan"], b["end_line"], b["origin"] == "auto"), project, force)
    n_key = 0
    if key:
        sec, _, ordn = (b["key_ref"] or "").partition(":"); sec = sec or b["section"]
        ordn = int(ordn) if ordn.isdigit() else 1
        for ks in con.execute("SELECT * FROM source WHERE role='key'").fetchall():
            if not ks["pdf"]: continue
            kp = detect.load_pages(con, ks["id"]); todo = []
            segs = con.execute("SELECT * FROM keyseg WHERE source=? AND section=? AND pair=?", (ks["id"], sec, ordn)).fetchall()
            for g in segs:
                todo += _span_todo(kp, g["start_scan"], g["start_line"], g["end_scan"], min(g["end_line"], 10**5), True)
            if not segs:
                idx = json.loads((con.execute("SELECT v FROM meta WHERE k=?", (f"keyindex:{ks['id']}",)).fetchone() or {"v": "{}"})["v"])
                gs = detect.key_guess(idx, sec)
                for sc in (gs or {}).get("scans", [])[:3]:
                    todo += _span_todo(kp, sc, 0, sc, 10**5, False)
            n_key += ocr_lines(con, ks["id"], todo, project, force)
    con.execute("INSERT INTO log(ts,block_id,field,old,new) VALUES(?,?,?,?,?)", (now(), bid, "ocr", "", f"{ENGINE}: {n_book} book + {n_key} key lines"))
    con.commit()
    log(f"block {bid}: OCR'd {n_book} book + {n_key} key lines")
    return n_book + n_key

def ocr_text(con, source):
    """{(scan, line): text} of cached local OCR for a source; rows whose stored DjVu box no longer matches the line are ignored."""
    boxes = {}
    for r in con.execute("SELECT scan, lines FROM page WHERE source=?", (source,)):
        boxes[r["scan"]] = [json.dumps(l.get("b")) for l in json.loads(r["lines"])]
    out = {}
    for r in con.execute("SELECT scan, line, text, box FROM ocr WHERE source=? AND engine=?", (source, ENGINE)):
        B = boxes.get(r["scan"], [])
        if r["line"] < len(B) and (r["box"] is None or r["box"] == B[r["line"]]): out[(r["scan"], r["line"])] = r["text"]
    return out
