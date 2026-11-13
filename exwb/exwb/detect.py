"""Rule-based candidate generation. No AI. All behaviour is driven by the profile (regexes)."""
import re, json
from .db import now

HEB = re.compile(r"[֐-׿]")
SCRIPT_RTL = True
LAT = re.compile(r"[A-Za-z]")
BIDI = dict.fromkeys([0x200e, 0x200f])

def norm(s): return s.translate(BIDI).strip()
def heb_n(s): return len(HEB.findall(s))
def lat_n(s): return len(LAT.findall(s))
STOP = set("""and are but did for from had has have her him his not our out shall she that the their them they this those
these thou thee thy upon was were what which who whom will with you your said say saw see went come came give gave take took
make made man men king god day land how all also into over under before after when where there then than been""".split())

def is_english(s):
    """True for real English prose: >=2 common (3+ letter) English words, a fair share of the Latin tokens,
    and more English words than Hebrew words. Hebrew misread as Latin ('soy my', 'SPIN ms Oe oy') fails."""
    ws = re.findall(r"[A-Za-z]+", s)
    hits = sum(w.lower() in STOP for w in ws)
    hw = sum(1 for t in s.split() if HEB.search(t))
    return hits >= 2 and hits * 4 >= len(ws) and hits > hw

SHORT = set("a an as at be by do he i if in is it me my no of on or so to up us we".split())

def line_is_rtl(s):
    """Reverse word order only when Hebrew words outnumber English-looking words (prose with Hebrew examples stays LTR)."""
    hw = sum(1 for t in s.split() if HEB.search(t))
    hits = sum(w.lower() in STOP or w.lower() in SHORT for w in re.findall(r"[A-Za-z]+", s))
    return SCRIPT_RTL and hw >= 2 and hits <= hw

def line_kind(s):
    """he = Hebrew (incl. garbled), la = English prose, x = Latin junk (inherits neighbour), o = digits/punct only."""
    t = norm(s)
    if is_english(t): return "la"
    if heb_n(t) >= 1: return "he"
    if lat_n(t) >= 1: return "x"
    return "o"

def kind(s):
    h, l = heb_n(s), lat_n(s)
    if h >= 2 and h >= l: return "he"
    if l >= 3 and l > h: return "la"
    return "other"

DEFAULTS = {
    "block_start": [r"^\W*(?:EXERCISE|Exercise)\b[\.,\s—-]"],
    "section_heading": r"^[^\w§]*(?:§§?|8|S)[\s\.]*(\d{1,3})\s*[\.,\)]*\s*['‘’]?[A-Z][A-Z ,\.'‘’\-\(\)]{4,}",
    "first_scan": 1, "last_scan": 10**6, "max_pages": 6,
    "hebrew_part": "A", "latin_part": "B",
    "key_section": r"^§\s*(\d{1,3})\s*[\.,:;]?\W*$", "key_part": r"^([A-D])\.$",
    "key_first_scan": 1,
}

def cfg(p): 
    d = dict(DEFAULTS); d.update(p or {}); return d

def load_pages(con, source):
    out = {}
    for r in con.execute("SELECT scan, lines FROM page WHERE source=? ORDER BY scan", (source,)):
        out[r["scan"]] = [l["t"] for l in json.loads(r["lines"])]
    return out

def section_positions(pages, P):
    sec_re = re.compile(P["section_heading"])
    lone_re = re.compile(r"^\W*(?:§§?|8|S)\W*(\d{1,3})\W*$")
    body, hdr_first = [], {}
    for scan in sorted(pages):
        if not (P["first_scan"] <= scan <= P["last_scan"]): continue
        L = pages[scan]
        for i, x in enumerate(L):
            m = sec_re.match(norm(x))
            if not m and 0 < i < len(L) - 2:
                m = lone_re.match(norm(x)); nx = norm(L[i + 1])
                if m and not (re.match(r"^\W*[A-Z][A-Z ,\.'\-]{5,}", nx) and sum(c.isupper() for c in nx) >= 6): m = None
            if not m: continue
            t = norm(x)
            if i == 0 or i == len(L) - 1 or re.match(r"^\d{1,3}\s+[§8S]", t):
                hdr_first.setdefault(m.group(1), scan)
            else: body.append((scan, i, m.group(1), "body"))
    have = {b[2] for b in body}
    pos = list(body)
    for s, scan in hdr_first.items():           # running-header-only: look for the known number's heading nearby (§ often misread)
        if s in have: continue
        near = re.compile(r"^\W*(?:§§?|[68S$%])?\W{0,2}" + s + r"\s*[\.,]\s*['‘’]?[A-Z][A-Z]{2,}")
        hit = next(((sc, i) for sc in (scan, scan + 1) for i, x in enumerate(pages.get(sc, []))
                    if 0 < i < len(pages[sc]) - 1 and near.match(norm(x))), None)
        # a section seen only in a running header starts somewhere on that page: exercises at the top of the page
        # still belong to the previous section (Davidson puts exercises at the end of a section)
        pos.append((hit[0], hit[1], s, "body (number-guided)") if hit else (scan, 10**5, s, "running-header"))
    pos.sort(key=lambda p: (p[0], p[1]))
    return pos

def section_at(pos, scan, line):
    cur = ("", "")
    for ps, pl, s, basis in pos:
        if (ps, pl) < (scan, line): cur = (s, basis)
        else: break
    return cur

def find_blocks(pages, P):
    starts = [re.compile(r) for r in P["block_start"]]
    pos = section_positions(pages, P)
    st = []
    for scan in sorted(pages):
        if not (P["first_scan"] <= scan <= P["last_scan"]): continue
        for i, x in enumerate(pages[scan]):
            t = norm(x)
            if any(r.match(t) for r in starts) and not t.lower().startswith("the exercises"):
                st.append((scan, i, t))
    out = []
    boundaries = sorted({(p[0], p[1]) for p in pos if p[3] != "running-header"} | {(s[0], s[1]) for s in st})
    for scan, i, t in st:
        nxt = [b for b in boundaries if b > (scan, i)]
        end = nxt[0] if nxt else (scan, 10**6)
        if end[0] > scan + P["max_pages"]: end = (scan + P["max_pages"], 0)
        sec, basis = section_at(pos, scan, i)
        out.append(dict(scan=scan, line=i, instruction=t, end_scan=end[0], end_line=int(end[1]) if end[1] != 0.5 else 0,
                        section=sec, basis=basis))
    firsts = [int(p[2]) for p in pos if p[2].isdigit()]
    for b in out:                                  # exercises before the first heading belong to the section before it
        if not b["section"] and firsts and firsts[0] > 1:
            b["section"], b["basis"] = str(firsts[0] - 1), f"inferred: before first heading (§{firsts[0]})"
    # ordinal within section => which key (A,B) pair this exercise corresponds to
    cnt = {}
    for b in out:
        cnt[b["section"]] = cnt.get(b["section"], 0) + 1
        b["ordinal"] = cnt[b["section"]]
    return out

def span_lines(pages, s_scan, s_line, e_scan, e_line, skip_first=True):
    """Lines in [start, end) excluding running headers; returns [(scan,line,text)]."""
    out = []
    for scan in range(s_scan, e_scan + 1):
        L = pages.get(scan, [])
        for i, x in enumerate(L):
            if (scan, i) < (s_scan, s_line + (1 if skip_first else 0)): continue
            if (scan, i) >= (e_scan, e_line): break
            if (i == 0 or i == len(L) - 1) and (re.match(r"^\W*\d{1,3}\W*$", norm(x)) or
                                                 re.search(r"\b\d{1,3}\s*$|^\W*\d{1,3}\b", norm(x)) and kind(x) != "he" and len(norm(x)) < 70):
                continue                                   # running header / folio
            out.append((scan, i, x))
    return out

NUMTOK = re.compile(r"^\W*(\d{1,3})\W*$")
def first_number_index(text, tolerant=False):
    """Token index where split_numbered's first accepted item number sits (None if no numbering)."""
    return split_numbered(text, tolerant, _first=True)

def split_numbered(text, tolerant=False, min_items=3, _first=False):
    """Split at item numbers 1,2,3,... ; tolerant=True (Hebrew) also accepts a skipped number
    (k+1) and a truncated one ('3' where 13 is expected), and keeps text before the first number."""
    toks = text.split()
    bounds, k = [], 1
    for i, t in enumerate(toks):
        m = NUMTOK.match(t)
        if not m: continue
        v = int(m.group(1)); sv, sk = str(v), str(k)
        if v == k: bounds.append((i, sk)); k += 1
        elif tolerant and v in (k + 1, k + 2): bounds.append((i, sv)); k = v + 1
        elif tolerant:
            hit = next((c for c in (k, k + 1, k + 2) if len(sv) < len(str(c)) and str(c).endswith(sv)), None)
            if hit: bounds.append((i, str(hit))); k = hit + 1
    if len(bounds) < (2 if tolerant else min_items): return None
    if _first: return bounds[0][0]
    items = []
    if tolerant and bounds[0][0] > 0:
        lead, need = " ".join(toks[:bounds[0][0]]), int(bounds[0][1]) - 1
        parts = [p.strip() for p in re.split(r"(?<=[:׃\.\?!])\s+", lead) if re.search(r"\w", p)]
        if need > 1 and len(parts) == need: items += [(str(j), p) for j, p in enumerate(parts, 1)]
        else: items.append((str(need or 1), lead))
    for j, (p, n) in enumerate(bounds):
        end = bounds[j + 1][0] if j + 1 < len(bounds) else len(toks)
        items.append((n, " ".join(toks[p + 1:end])))
    return items

NOISE = re.compile(r"^(?:\W*\d{4,}\W*|[\W\d_]*0{3,}[\W\d_]*|[\W_]*0+[\W_]*|.*(.)\1\1.*|.*[\*₪].*|[^\w\s]+)$")
def clean_ocr(text):
    """Drop scan-noise tokens from local OCR (digit runs, '000', tripled letters, symbol junk). Raw OCR stays in the ocr table."""
    return " ".join(t for t in text.split() if not (NOISE.match(t) and not re.fullmatch(r"\W*\d{1,3}\W*", t)))

def text_score(text, side):
    """Share of tokens that look right for the side: Hebrew tokens without Latin (he) / plain words (la). Item numbers ignored."""
    toks = [t for t in text.split() if re.search(r"\w", t) and not re.fullmatch(r"\W*\d{1,3}\W*", t)]
    if not toks: return 0.0
    if side == "he": good = sum(bool(HEB.search(t)) and not LAT.search(t) for t in toks)
    else: good = sum(bool(re.fullmatch(r"\W*[A-Za-z][A-Za-z'’\-]*\W*", t)) for t in toks)
    return good / len(toks)

def choose_text(djvu, ocr_raw, side):
    """(text, used_ocr): local OCR replaces the DjVu line only when it is substantially better and not much shorter."""
    if not ocr_raw: return djvu, False
    o, d = clean_ocr(ocr_raw), norm(djvu)
    if not o: return djvu, False
    so, sd = text_score(o, side), text_score(d, side)
    nd = len([t for t in d.split() if re.search(r"\w", t)]) or 1
    if len(o.split()) < 0.6 * nd: return djvu, False
    return (o, True) if (so >= sd + 0.1 or (so >= 0.9 and so >= sd and side == "he")) else (djvu, False)

LISTSEP = {"la": r"\s*[;:]\s+|\s*;\s*", "he": r"\s*[\.;,:]\s+|\s*[;׃]\s*"}
def split_list(text, side):
    """Split an unnumbered word/phrase list ('His law; his lips; ...') into entries; None if it doesn't look like a list."""
    parts = [p.strip(" .;:,") for p in re.split(LISTSEP[side], text)]
    parts = [p for p in parts if re.search(r"\w", p)]
    if len(parts) < 3 and side == "la":                  # comma lists of short pieces (transliterations, word lists)
        cp = [p.strip(" .;:") for p in re.split(r"\s*,\s+", text) if re.search(r"\w", p)]
        if len(cp) >= 5 and sum(len(p.split()) for p in cp) / len(cp) <= 3: parts = cp
    return parts if len(parts) >= 3 else None

def split_items(text, side, tolerant=False):
    """[(num, text)]: an unnumbered lead-in list becomes L1, L2, ...; then numbered items 1, 2, ..."""
    nums = split_numbered(text, tolerant=tolerant)
    if not nums: 
        lst = split_list(text, side)
        return [(f"L{k}", t) for k, t in enumerate(lst, 1)] if lst else None
    toks = text.split()
    first = first_number_index(text, tolerant)
    lead = " ".join(toks[:first]) if first else ""
    if tolerant and lead and int(nums[0][0]) > 1 and not nums[0][0].startswith("L"):
        lead = ""                                        # lead already became items 1..n-1 in split_numbered
    lst = split_list(lead, side) if lead else None
    if lst:
        body = [it for it in nums if not (tolerant and it[1] == lead)]
        if body and body[0][0] == "2" and len(lst) > 1 and len(lst[-1].split()) >= 4:
            body = [("1", lst.pop())] + body                 # item 1 lost its numeral and ran into the list
        return [(f"L{k}", t) for k, t in enumerate(lst, 1)] + body
    return nums

def mark_garbled(text):
    """Wrap Latin-only tokens inside Hebrew text as ⟨tok⟩ so OCR garbage is easy to spot (raw OCR stays in page)."""
    return " ".join(f"⟨{t}⟩" if LAT.search(t) and not HEB.search(t) else t for t in text.split())

SENT = re.compile(r"(?<=[\.\?!;])\s+(?=[A-Z“\"'\(\[])")
def split_sentences(text):
    return [s.strip() for s in SENT.split(text) if re.search(r"[A-Za-z]{2}", s)]

def line_sides(lines):
    """Per line 'he' / 'la' / None. Ambiguous lines (Latin junk, bare numbers) inherit the previous line's side."""
    out, cur = [], None
    for _, _, x in lines:
        k = line_kind(x)
        if k in ("he", "la"): cur = k
        elif cur is None: cur = "he" if k == "x" else None
        out.append(cur)
    return out

def candidate_items(lines, P, sides=None):
    """lines: [(scan,line,text)] -> candidate items (prompt side only). sides: optional precomputed line_sides."""
    sides = sides or line_sides(lines)
    he = [norm(x) for (_, _, x), sd in zip(lines, sides) if sd == "he"]
    la = [norm(x) for (_, _, x), sd in zip(lines, sides) if sd == "la"]
    items = []
    if he:
        nums = split_items(" ".join(he), "he", tolerant=True)
        if nums:
            for n, t in nums:
                mt = mark_garbled(t)
                items.append(dict(part=P["hebrew_part"], num=n, prompt=mt, note="⟨…⟩ = OCR read Hebrew as Latin" if mt != t else ""))
        else:
            for k, x in enumerate(he, 1):
                items.append(dict(part=P["hebrew_part"], num=str(k), prompt=mark_garbled(x), note="no numerals found: one item per line"))
    ltext = ""
    for x in la:
        ltext = (ltext[:-1] + x) if ltext.endswith("-") and x[:1].islower() else (ltext + " " + x)
    for k, s in enumerate(split_sentences(ltext.strip()), 1):
        note = "footnote?" if re.match(r"^[\d\*†‡]+\s", s) else ""
        items.append(dict(part=P["latin_part"], num=str(k), prompt=s, note=note))
    return items

FOOTNOTE = re.compile(r"^\W?\d{1,2}[°\*’']?\s+(?!\d)\S")
ANSWER_NUM = re.compile(r"^\W?\d{1,2}\.\s")
def drop_footnotes(lines, alt=None):
    """Key pages: skip footnote blocks (line starting 'N text' with mostly Latin script, until the next 'N.' answer or page).
    Checked on the DjVu text and the local OCR text (alt)."""
    out, fn, page = [], False, None
    for s, i, x in lines:
        ts = [norm(x)] + ([norm(alt[(s, i)])] if alt and alt.get((s, i)) else [])
        if s != page: fn, page = False, s
        if any(ANSWER_NUM.match(t) for t in ts): fn = False
        elif any(FOOTNOTE.match(t) and lat_n(t) > heb_n(t) for t in ts): fn = True
        if not fn: out.append((s, i, x))
    return out

def find_keysegs(pages, P, alt=None):
    """Key structure: '§ N' heading lines then 'A.' 'B.' part markers. pair = nth A..B group in the section."""
    sec_re, part_re = re.compile(P["key_section"]), re.compile(P["key_part"])
    marks = []   # (scan,line,kind,value)
    for scan in sorted(pages):
        if scan < P["key_first_scan"]: continue
        for i, x in enumerate(pages[scan]):
            ts = [norm(x)] + ([norm(alt[(scan, i)])] if alt and alt.get((scan, i)) else [])
            m = next((sec_re.match(t) for t in ts if sec_re.match(t)), None)
            if m: marks.append((scan, i, "s", m.group(1))); continue
            m = next((part_re.match(t) for t in ts if part_re.match(t)), None)
            if m: marks.append((scan, i, "p", m.group(1)))
    # section numbers only move forward (<= +6); a lower number that ends a plausible next number is that number
    # ('1' after §40 = §41), anything else is a stray ('§ 124' = '§ 12. 4').
    fixed, top = [], 0
    for scan, i, kd, v in marks:
        if kd == "s":
            n = int(v)
            if not (top <= n <= top + 6):
                n = next((c for c in range(top, top + 7) if c > 9 and str(c).endswith(v) and len(v) < len(str(c))), None)
                if n is None: continue
            top = n; v = str(n)
        fixed.append((scan, i, kd, v))
    marks = fixed
    # part markers before the first readable heading: each letter restart (A after B) is one more section
    k0 = next((k for k, m in enumerate(marks) if m[2] == "s"), len(marks))
    pre = [m[3] for m in marks[:k0]]
    restarts = sum(1 for a, b in zip(pre, pre[1:]) if b <= a)
    first = int(marks[k0][3]) if k0 < len(marks) else 1
    start = first - 1 - restarts
    segs, sec, pair, last_part = [], (str(start) if start >= 1 else None), 0, None
    for k, (scan, i, kd, v) in enumerate(marks):
        if kd == "s":
            if v != sec: sec, pair, last_part = v, 0, None
            continue
        if sec is None: continue
        if k < k0 and last_part is not None and v <= last_part:
            sec, pair, last_part = str(int(sec) + 1), 0, None
        if last_part is None or v <= last_part: pair += 1       # letter restarted => new pair
        last_part = v
        nxt = marks[k + 1] if k + 1 < len(marks) else (scan, 10**6)
        segs.append(dict(section=sec, part=v, pair=pair, start_scan=scan, start_line=i, end_scan=nxt[0], end_line=nxt[1]))
    return segs

HDR_SEC = re.compile(r"[§%]\s*,?\s*(\d{1,3})\b")
def key_page_index(pages, P):
    """section -> [[scan, basis]] from key headings ('§ 14.') and running headers ('§ 13. B-§ 14. A.')."""
    sec_re = re.compile(P["key_section"]); idx = {}
    def add(sec, scan, basis):
        L = idx.setdefault(sec, [])
        if [scan, basis] not in L: L.append([scan, basis])
    for scan in sorted(pages):
        if scan < P["key_first_scan"]: continue
        L = pages[scan]
        for i, x in enumerate(L):
            t = norm(x)
            m = sec_re.match(t)
            if m: add(m.group(1), scan, "heading")
            elif i == 0 or i == len(L) - 1:
                nums = [int(n) for n in HDR_SEC.findall(t)]
                if nums and max(nums) - min(nums) <= 3:
                    for n in range(min(nums), max(nums) + 1): add(str(n), scan, "running-header")
    for L in idx.values(): L.sort()
    return idx

def key_guess(idx, section):
    """Best key scan for a section: its heading page, else first running-header page, else between neighbours."""
    if not section: return None
    if section in idx:
        L = idx[section]
        h = [s for s, b in L if b == "heading"]
        return {"scan": h[0] if h else L[0][0], "basis": "heading" if h else "running header", "scans": sorted({s for s, _ in L})}
    try: n = int(section)
    except ValueError: return None
    known = sorted((int(k), v) for k, v in idx.items() if k.isdigit())
    lo = [v for k, v in known if k < n]; hi = [v for k, v in known if k > n]
    if not lo and not hi: return None
    a = max(s for s, _ in lo[-1]) if lo else None; b = min(s for s, _ in hi[0]) if hi else None
    return {"scan": a if a is not None else b, "basis": "guess: between neighbouring sections", "scans": [x for x in (a, b) if x is not None]}


# ---------- pair-aware clean-up (Hebrew side <-> English side of one item) ----------
VALID_MARK = {"f.", "m.", "pl.", "sg.", "sing.", "du.", "perf.", "impf.", "lit.", "masc.", "fem.", "plur.", "acc.", "dat.", "ptc.", "inf."}
ABBR = {"erf.": "perf.", "perf": "perf.", "daz.": "dat.", "da¢.": "dat.", "dz.": "dat.", "pic.": "ptc.", "gic.": "ptc.", "ptc": "ptc."}
MARK = re.compile(r"\(([^()\s]{0,4})\)")
F_SHAPES = {"/", "/.", "f", "ƒ.", "J.", "/,", "f,", "f/", "f7", "~/.", "7/."}
M_SHAPES = {"#.", "#", "wz.", "mm.", "mz.", "m", "7.", "77.", "2.", "#,", "77", "7", "w.", ".", "/w.", "w"}  # italic m. is often read as w. (verified: key §19 A)
PRON_GENDER = re.compile(r"\b(thy|thee|thine|your|their|them|ye|you)\s*$", re.I)
FINAL_OK = {"יוסף", "כסף", "עוף", "אף", "סוף", "כנף", "טרף", "חרף", "אלף", "ערף", "שרף", "רדף", "גוף",
            "דוד", "מאד", "עוד", "אחד", "בעד", "עד", "כבד", "חסד", "נגד", "לבד", "פקד", "יחד", "סוד", "ציד", "יד", "ביד",
            "דבר", "גדעד", "פחד", "עבד", "למד", "עמד", "ילד", "ירד", "צעד", "כד", "מועד", "חמד", "שדד", "אבד", "בגד", "נקד", "שקד", "רעד", "פרד"}

def _bare(w):
    return "".join(LETTERS_RE.findall(w))
LETTERS_RE = re.compile(r"[\u05d0-\u05ea]")

def _he_gender(he):
    """m / f from short Hebrew: suffix -ם (כֶם/הֶם) vs -ן (כֶן/הֶן); None if unclear."""
    ws = [_bare(w) for w in he.split() if _bare(w)]
    if not ws or len(ws) > 3: return None
    m = sum(w.endswith(("כם", "הם")) or (len(w) > 3 and w.endswith("ם")) for w in ws)
    f = sum(w.endswith(("כן", "הן")) or (len(w) > 3 and w.endswith("ן")) for w in ws)
    return "m" if m > f else "f" if f > m else None

def fix_marks(en, he):
    """Garbled italic (f.) (m.) (pl.) in English, decided by the Hebrew suffix when short, else by OCR shape."""
    notes = []
    def rep(m):
        c = m.group(1)
        if c.lower() in VALID_MARK or re.fullmatch(r"[A-Za-z]{2,}|O|\d+", c): return m.group(0)
        if c in ABBR: new = ABBR[c]
        elif c[:1] in ("p", "P") and len(c) >= 2: new = "pl."
        else:
            g = None
            if PRON_GENDER.search(en[:m.start()]): g = _he_gender(he)
            g = g or ("f" if c in F_SHAPES else "m" if c in M_SHAPES else None)
            if not g: return m.group(0)
            new = g + "."
        notes.append(f"({c})→({new})"); return f"({new})"
    out = MARK.sub(rep, en)
    if re.search(r"\bQa/", out): out = re.sub(r"\bQa/", "Qal", out); notes.append("Qa/→Qal")
    return out, notes

def fix_finals(he, en):
    """OCR reads final ך/ו as ף or ד: fix only as many words as the English has matching pronouns."""
    n_thy = len(re.findall(r"\b(thy|thee|thine)\b", en, re.I)); n_his = len(re.findall(r"\b(his|him)\b", en, re.I))
    toks, notes = he.split(), []
    for k, t in enumerate(toks):
        b = _bare(t)
        if len(b) < 3 or b in FINAL_OK or b[1:] in FINAL_OK or b[-1] not in "ףד": continue
        if n_thy and not n_his: new = "ך"; n_thy -= 1
        elif n_his and not n_thy and b[-1] == "ף": new = "ו"; n_his -= 1
        else: continue
        i = max(j for j, ch in enumerate(t) if ch in "ףד")
        toks[k] = t[:i] + new + t[i + 1:]; notes.append(f"{b[-1]}→{new}")
    if n_his and not re.search(r"\bher\b", en, re.I) and len([t for t in toks if _bare(t)]) <= 2:
        for k, t in enumerate(toks):
            b = _bare(t)
            if n_his and len(b) >= 2 and b[-1] == "ה" and b not in FINAL_OK:
                i = max(j for j, ch in enumerate(t) if ch == "ה"); toks[k] = t[:i] + "ו" + t[i + 1:]
                notes.append("ה→ו"); n_his -= 1
    return " ".join(toks), notes

def strip_end(he):
    return re.sub(r"[\s:׃]+$", "", he)

def fix_pair(he, en):
    """(he, en, notes) for one item; the raw OCR stays in prompt_ocr/answer_ocr."""
    he2 = strip_end(he)
    en2, n1 = fix_marks(en, he2)
    he2, n2 = fix_finals(he2, en2) if en2.strip() else (he2, [])
    return he2, en2, n1 + n2
