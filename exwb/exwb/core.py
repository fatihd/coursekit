import json, os, re
from .db import now, get_meta, set_meta
from . import ingest, detect, ocr, script

# ---------- build pipeline ----------
def build(con, profile_path):
    base = os.path.dirname(os.path.abspath(profile_path))
    prof = json.load(open(profile_path, encoding="utf8"))
    set_meta(con, "profile", prof)
    script.apply(prof)
    if get_meta(con, "leaf_delta") is None: set_meta(con, "leaf_delta", prof.get("leaf_delta", 0))
    P = detect.cfg(prof.get("detect"))
    rel = lambda x: "" if not x else (x if os.path.isabs(x) else os.path.normpath(os.path.join(base, x)))
    for s in prof["sources"]:
        pages = ingest.PARSERS[s["format"]](rel(s["path"]))
        off = s.get("page_offset")
        if off is None: off = ingest.detect_offset(pages)
        con.execute("DELETE FROM page WHERE source=?", (s["id"],))
        con.execute("INSERT OR REPLACE INTO source(id,role,name,fmt,page_offset,url_template,images_dir,pdf,pdf_delta) VALUES(?,?,?,?,?,?,?,?,?)",
                    (s["id"], s.get("role", "book"), s.get("name", s["id"]), s["format"], off,
                     s.get("url_template", ""), rel(s.get("images_dir", "")), rel(s.get("pdf", "")), s.get("pdf_page_delta", 0)))
        con.executemany("INSERT INTO page(source,scan,printed,lines,w,h) VALUES(?,?,?,?,?,?)",
                        [(s["id"], n, n - off, json.dumps(pg["lines"], ensure_ascii=False), pg["w"], pg["h"]) for n, pg in pages.items()])
        print(f"ingested {s['id']}: {len(pages)} pages, printed offset {off}")
    con.commit()
    for s in prof["sources"]:
        pages = detect.load_pages(con, s["id"])
        if s.get("role", "book") == "key":
            rebuild_keysegs(con, s["id"], P, pages)
            set_meta(con, f"keyindex:{s['id']}", detect.key_page_index(pages, P))
        elif s.get("role", "book") == "book":
            added = 0
            have = {(r["start_scan"], r["start_line"]): r for r in con.execute("SELECT * FROM block WHERE source=?", (s["id"],))}
            synced = 0
            for b in detect.find_blocks(pages, P):
                old = have.get((b["scan"], b["line"]))
                if old is not None:                                  # refresh detection fields only on never-touched candidates
                    if old["status"] == "candidate" and old["origin"] == "auto" and untouched(con, old["id"]):
                        con.execute("UPDATE block SET section=?, section_basis=?, end_scan=?, end_line=?, key_ref=? WHERE id=?",
                                    (b["section"], b["basis"], b["end_scan"], b["end_line"], f'{b["section"]}:{b["ordinal"]}', old["id"])); synced += 1
                    apply_overrides(con, old["id"])
                    continue
                bid = con.execute("INSERT INTO block(source,label,section,section_basis,instruction,start_scan,start_line,end_scan,end_line,status,origin,key_ref,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (s["id"], "", b["section"], b["basis"], b["instruction"], b["scan"], b["line"], b["end_scan"], b["end_line"],
                     "candidate", "auto", f'{b["section"]}:{b["ordinal"]}', now(), now())).lastrowid
                regenerate(con, bid, P, log=False); added += 1
            redo = [r["id"] for r in con.execute("SELECT id FROM block WHERE source=? AND status='candidate' AND origin='auto' ORDER BY start_scan, start_line", (s["id"],))
                    if untouched(con, r["id"], items_only=True)]
            for bid in redo: regenerate(con, bid, P, log=False)
            print(f"{s['id']}: {added} new candidate blocks; refreshed {synced} untouched candidates (boundaries) and re-derived items of {len(redo)}; in-progress/done blocks kept")
    con.commit()

def untouched(con, bid, items_only=False):
    """No human edits since the block's last reset (items_only: ignore block-field edits)."""
    r = con.execute("SELECT MAX(id) m FROM log WHERE block_id=? AND field='reset'", (bid,)).fetchone()["m"] or 0
    q = "SELECT 1 FROM log WHERE block_id=? AND id>? AND field NOT IN ('reset','ocr','regenerate')" + (" AND item_id IS NOT NULL" if items_only else "")
    return not con.execute(q, (bid, r)).fetchone()

def reset(con, ids=None):
    """Discard review work: blocks back to 'candidate' with freshly detected boundaries + items. The log keeps the history."""
    P = _P(con); n = 0
    for src in [r["id"] for r in con.execute("SELECT id FROM source WHERE role='book'")]:
        det = {(b["scan"], b["line"]): b for b in detect.find_blocks(detect.load_pages(con, src), P)}
        for r in con.execute("SELECT * FROM block WHERE source=?", (src,)).fetchall():
            if ids and r["id"] not in ids: continue
            b = det.get((r["start_scan"], r["start_line"]))
            if b and r["origin"] == "auto":
                con.execute("UPDATE block SET section=?, section_basis=?, end_scan=?, end_line=?, key_ref=?, instruction=? WHERE id=?",
                            (b["section"], b["basis"], b["end_scan"], b["end_line"], f'{b["section"]}:{b["ordinal"]}', b["instruction"], r["id"]))
            con.execute("UPDATE block SET status='candidate', note='', label='', updated=? WHERE id=?", (now(), r["id"]))
            apply_overrides(con, r["id"])
            if any(overrides(con).get(_okey(r), {}).get(k) for k in ("merged_into", "ignored")): continue
            con.execute("INSERT INTO log(ts,block_id,field,old,new) VALUES(?,?,?,?,?)", (now(), r["id"], "reset", r["status"], "candidate"))
            regenerate(con, r["id"], P, log=False); n += 1
    con.commit()
    return n

def rebuild_keysegs(con, source, P=None, pages=None):
    """Key structure (§ / A. B. markers) from DjVu text or, where a marker was misread there, the local OCR text."""
    P = P or _P(con); pages = pages or detect.load_pages(con, source)
    con.execute("DELETE FROM keyseg WHERE source=?", (source,))
    for g in detect.find_keysegs(pages, P, ocr.ocr_text(con, source)):
        con.execute("INSERT INTO keyseg(source,section,part,pair,start_scan,start_line,end_scan,end_line) VALUES(?,?,?,?,?,?,?,?)",
                    (source, g["section"], g["part"], g["pair"], g["start_scan"], g["start_line"], g["end_scan"], g["end_line"]))
    con.commit()

def _P(con): return detect.cfg((get_meta(con, "profile") or {}).get("detect"))

# ---------- structure overrides (survive build/reset) ----------
def _okey(b): return f'{b["source"]}:{b["start_scan"]}:{b["start_line"]}'
def overrides(con): return get_meta(con, "overrides", {}) or {}
def set_override(con, b, **kw):
    o = overrides(con); d = o.get(_okey(b), {}); d.update(kw); o[_okey(b)] = d; set_meta(con, "overrides", o)

def apply_overrides(con, bid):
    b = con.execute("SELECT * FROM block WHERE id=?", (bid,)).fetchone()
    o = overrides(con).get(_okey(b))
    if not o: return
    for f in ("section", "end_scan", "end_line"):
        if f in o: con.execute(f"UPDATE block SET {f}=? WHERE id=?", (o[f], bid))
    if "section" in o: con.execute("UPDATE block SET section_basis='manual override' WHERE id=?", (bid,))
    if o.get("merged_into"): con.execute("UPDATE block SET status='skipped', note=? WHERE id=?", (f"merged into {o['merged_into']}", bid))
    if o.get("ignored"): con.execute("UPDATE block SET status='skipped', note=? WHERE id=?", (f"ignored: {o['ignored']}", bid))
    if o.get("hold"): con.execute("UPDATE block SET note=? WHERE id=?", (f"HELD (kept, not exported): {o['hold']}", bid))
    con.commit()

def merge_with_next(con, bid):
    """Merge a block with the next block of the same source; recorded as an override so build/reset keep it."""
    a = con.execute("SELECT * FROM block WHERE id=?", (bid,)).fetchone()
    b = con.execute("""SELECT * FROM block WHERE source=? AND status!='skipped' AND (start_scan>? OR (start_scan=? AND start_line>?))
                       ORDER BY start_scan, start_line LIMIT 1""", (a["source"], a["start_scan"], a["start_scan"], a["start_line"])).fetchone()
    if not b: return None
    subs = (overrides(con).get(_okey(a), {}).get("subspans")) or [[a["start_scan"], a["start_line"], a["end_scan"], a["end_line"]]]
    subs = subs + [[b["start_scan"], b["start_line"], b["end_scan"], b["end_line"]]]
    set_override(con, a, end_scan=b["end_scan"], end_line=b["end_line"], subspans=subs)
    set_override(con, b, merged_into=_okey(a))
    con.execute("INSERT INTO log(ts,block_id,field,old,new) VALUES(?,?,?,?,?)", (now(), bid, "merge", "", str(b["id"])))
    apply_overrides(con, a["id"]); apply_overrides(con, b["id"]); regenerate(con, a["id"], log=False)
    return a["id"]

def set_hold(con, bid, reason):
    """Keep a block (and its curated items) in the workbench but leave it out of export; reason '' releases it."""
    b = con.execute("SELECT * FROM block WHERE id=?", (bid,)).fetchone()
    o = overrides(con); d = o.get(_okey(b), {}); d.pop("ignored", None)
    if reason: d["hold"] = reason
    else: d.pop("hold", None)
    o[_okey(b)] = d; set_meta(con, "overrides", o)
    if b["status"] == "skipped": con.execute("UPDATE block SET status='candidate' WHERE id=?", (bid,))
    con.execute("UPDATE block SET note='' WHERE id=?", (bid,))
    con.execute("INSERT INTO log(ts,block_id,field,old,new) VALUES(?,?,?,?,?)", (now(), bid, "hold", "", reason))
    apply_overrides(con, bid)

def set_section(con, bid, section):
    b = con.execute("SELECT * FROM block WHERE id=?", (bid,)).fetchone()
    set_override(con, b, section=section); apply_overrides(con, bid)

def key_slots(con, section):
    """Ordered (pair, part) slots the key has for a section; missing letters inside a pair are filled (A,B,D -> A,B,C,D)."""
    rows = con.execute("SELECT DISTINCT pair, part FROM keyseg WHERE section=? ORDER BY pair, part", (section,)).fetchall()
    out = []
    for pair in sorted({r["pair"] for r in rows}):
        ps = [r["part"] for r in rows if r["pair"] == pair]
        out += [(pair, chr(c)) for c in range(ord("A"), ord(max(ps)) + 1)]
    return out

def _groups(items):
    """Contiguous runs: ('L', idx...) word list, ('he', ...) Hebrew numbered, ('en', ...) English."""
    g = []
    for k, it in enumerate(items):
        kind = "en" if detect.lat_n(it["prompt"]) > detect.heb_n(it["prompt"]) else ("L" if it["num"].startswith("L") else "he")
        if it.get("_sub") is not None: kind = f'{it["_sub"]}:{kind}'
        if g and g[-1][0] == kind: g[-1][1].append(k)
        else: g.append([kind, [k]])
    return g

def assign_slots(con, bid, items):
    """Give the block's item groups the section's key parts in order (after earlier blocks of the section)."""
    b = con.execute("SELECT * FROM block WHERE id=?", (bid,)).fetchone()
    slots = key_slots(con, b["section"])
    if not slots or not items: return items
    used = 0
    for o in con.execute("""SELECT id FROM block WHERE source=? AND section=? AND status!='skipped' AND (start_scan<? OR (start_scan=? AND start_line<?))""",
                         (b["source"], b["section"], b["start_scan"], b["start_scan"], b["start_line"])):
        used += len({r["part"] for r in con.execute("SELECT DISTINCT part FROM item WHERE block_id=?", (o["id"],))})
    mine = slots[used:]
    if not mine: return items
    g = _groups(items)
    while len(g) > len(mine) and any(x[0].endswith("L") for x in g[:-1]):
        k = next(i for i, x in enumerate(g[:-1]) if x[0].endswith("L")); g[k + 1][1][:0] = g[k][1]; del g[k]
    for (pair, part), (_, idx) in zip(mine, g):
        for k in idx: items[k]["part"] = part
    con.execute("UPDATE block SET key_ref=? WHERE id=?", (f'{b["section"]}:{mine[0][0]}', bid))
    return items

def _align_lists_with_key(con, bid, items):
    """If a part's unnumbered list (L1..) has a different count than the key's list but exactly as many words, one entry per word."""
    try: segs = key_candidates(con, bid)["segments"]
    except Exception: return items
    for part in {i["part"] for i in items}:
        n = sum(1 for sg in segs if sg["part"] == part for k in sg["items"] if k["num"].startswith("L"))
        mine = [i for i in items if i["part"] == part and i["num"].startswith("L")]
        if not n or not mine or len(mine) == n: continue
        words = [w for i in mine for w in i["prompt"].split() if detect.HEB.search(w) or detect.LAT.search(w)]
        if len(words) != n: continue
        new = [dict(part=part, num=f"L{k}", prompt=w.strip(".,;:׃"), note="list split per word to match the key's count") for k, w in enumerate(words, 1)]
        at = items.index(mine[0]); items = [i for i in items if i not in mine]; items[at:at] = new
    return items

def curate(con, bid, items, author="", note=""):
    """Store a curated item list for a block (kept across build/reset) and re-derive the block from it."""
    b = con.execute("SELECT * FROM block WHERE id=?", (bid,)).fetchone()
    con.execute("INSERT OR REPLACE INTO curated(okey,items,author,note,ts) VALUES(?,?,?,?,?)", (_okey(b), json.dumps(items, ensure_ascii=False), author, note, now()))
    con.execute("INSERT INTO log(ts,block_id,field,old,new) VALUES(?,?,?,?,?)", (now(), bid, "curated", "", f"{len(items)} items"))
    regenerate(con, bid, log=False)

def autofix(con, bid):
    """Pair-aware clean-up of every item (trailing ':', garbled (f.)/(m.)/(pl.), final ך/ו read as ף/ד); notes say what changed."""
    for it in con.execute("SELECT * FROM item WHERE block_id=?", (bid,)).fetchall():
        p, a = it["prompt"] or "", it["answer"] or ""
        p_he = detect.heb_n(p) > detect.lat_n(p)
        he, en = (p, a) if p_he else (a, p)
        if he.strip(): he2, en2, notes = detect.fix_pair(he, en)
        else: he2 = he; en2, notes = detect.fix_marks(en, "")
        if not notes and he2 == he: continue
        np, na = (he2, en2) if p_he else (en2, he2)
        note = "; ".join(x for x in [it["note"], ("auto: " + ", ".join(notes)) if notes else ""] if x)
        con.execute("UPDATE item SET prompt=?, answer=?, note=? WHERE id=?", (np, na, note, it["id"]))
    con.commit()

def regenerate(con, bid, P=None, log=True):
    P = P or _P(con)
    b = con.execute("SELECT * FROM block WHERE id=?", (bid,)).fetchone()
    pages = detect.load_pages(con, b["source"])
    alt = ocr.ocr_text(con, b["source"])
    subs = (overrides(con).get(_okey(b), {}).get("subspans")) or [[b["start_scan"], b["start_line"], b["end_scan"], b["end_line"]]]
    items = []
    for n, (s1, l1, s2, l2) in enumerate(subs):
        lines = detect.span_lines(pages, s1, l1, s2, l2, skip_first=(b["origin"] == "auto"))
        sides = detect.line_sides(lines)                 # side from DjVu text; text itself from local OCR when cached
        lines = [(s, i, detect.choose_text(x, alt.get((s, i)), sd)[0]) for (s, i, x), sd in zip(lines, sides)]
        part = detect.candidate_items(lines, P, sides)
        for it in part: it["_sub"] = n if len(subs) > 1 else None
        items += part
    items = assign_slots(con, bid, items)
    items = _align_lists_with_key(con, bid, items)
    cur = con.execute("SELECT * FROM curated WHERE okey=?", (_okey(b),)).fetchone()
    if cur:                                              # curated transcription replaces derived items; OCR kept per (part,num)
        raw = {(i["part"], i["num"]): i["prompt"] for i in items}
        items = [dict(part=c["part"], num=c["num"], prompt=c.get("prompt", ""), answer=c.get("answer", ""),
                      ocr=raw.get((c["part"], c["num"]), ""), note=c.get("note", ""), hint=c.get("hint", ""), explain=c.get("explain", ""),
                      data=json.dumps(c["data"], ensure_ascii=False) if c.get("data") else "")
                 for c in json.loads(cur["items"])]
    con.execute("DELETE FROM item WHERE block_id=?", (bid,))
    for k, it in enumerate(items):
        con.execute("INSERT INTO item(block_id,ord,part,num,prompt_ocr,prompt,answer_ocr,answer,note,hint,explain,data) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (bid, k, it["part"], it["num"], it.get("ocr", it["prompt"]), it["prompt"], "", it.get("answer", ""), it.get("note", ""), it.get("hint", ""), it.get("explain", ""), it.get("data", "")))
    if cur: con.commit(); return
    con.commit()
    try: prefill_answers(con, bid)                       # candidates start pre-answered from the key (by label)
    except Exception: pass
    autofix(con, bid)
    if log: con.execute("INSERT INTO log(ts,block_id,field,old,new) VALUES(?,?,?,?,?)", (now(), bid, "regenerate", "", ""))
    con.commit()

# ---------- queries ----------
def url_for(con, source, scan):
    s = con.execute("SELECT * FROM source WHERE id=?", (source,)).fetchone()
    if not s or not s["url_template"]: return ""
    return s["url_template"].format(scan=scan, leaf=scan + (get_meta(con, "leaf_delta", 0) or 0))

def state(con):
    srcs = [dict(r) for r in con.execute("SELECT * FROM source")]
    blocks = []
    for r in con.execute("""SELECT b.*, (SELECT COUNT(*) FROM item WHERE block_id=b.id) n,
            (SELECT COUNT(*) FROM item WHERE block_id=b.id AND answer!='') na FROM block b
            ORDER BY b.source, b.start_scan, b.start_line"""):
        d = dict(r); d["printed"] = _printed(con, r["source"], r["start_scan"]); blocks.append(d)
    return {"sources": srcs, "blocks": blocks, "leaf_delta": get_meta(con, "leaf_delta", 0),
            "profile_name": (get_meta(con, "profile") or {}).get("name", ""),
            "script": {k: script.ACTIVE[k] for k in ("name", "rtl", "keyboard", "label")}}

def _printed(con, source, scan):
    r = con.execute("SELECT printed FROM page WHERE source=? AND scan=?", (source, scan)).fetchone()
    return r["printed"] if r else None

def page(con, source, scan):
    r = con.execute("SELECT * FROM page WHERE source=? AND scan=?", (source, scan)).fetchone()
    if not r: return None
    L = json.loads(r["lines"])
    s = con.execute("SELECT pdf, images_dir FROM source WHERE id=?", (source,)).fetchone()
    altm = ocr.ocr_text(con, source); alt = {i: altm.get((scan, i)) for i in range(len(L))}
    sides = detect.line_sides([(scan, i, l["t"]) for i, l in enumerate(L)])
    used = [bool(alt[i]) and detect.choose_text(l["t"], alt[i], sides[i])[1] for i, l in enumerate(L)]
    return {"source": source, "scan": scan, "printed": r["printed"], "lines": [l["t"] for l in L], "ocr": [alt.get(i) for i in range(len(L))], "ocr_used": used, "dirs": [l.get("d", "ltr") for l in L],
            "boxes": [l.get("b") for l in L], "w": r["w"], "h": r["h"], "has_image": bool(s and (s["pdf"] or s["images_dir"])),
            "url": url_for(con, source, scan), "max": con.execute("SELECT MAX(scan) m FROM page WHERE source=?", (source,)).fetchone()["m"]}

def block(con, bid):
    b = con.execute("SELECT * FROM block WHERE id=?", (bid,)).fetchone()
    if not b: return None
    d = dict(b); d["printed"] = _printed(con, b["source"], b["start_scan"]); d["url"] = url_for(con, b["source"], b["start_scan"])
    d["items"] = [dict(r) for r in con.execute("SELECT * FROM item WHERE block_id=? ORDER BY ord", (bid,))]
    return d

def next_unfinished(con, after_id=None):
    rows = [r for r in con.execute("SELECT id,status FROM block WHERE status IN ('candidate','in_progress') ORDER BY source,start_scan,start_line")]
    if not rows: return None
    order = [r["id"] for r in con.execute("SELECT id FROM block ORDER BY source,start_scan,start_line")]
    if after_id in order:
        idx = order.index(after_id)
        ok = {r["id"] for r in rows}
        for i in order[idx + 1:] + order[:idx]:
            if i in ok: return i
    return rows[0]["id"]

# ---------- edits ----------
BFIELDS = ("label", "section", "instruction", "note", "key_ref", "status")
def update_block(con, bid, data):
    old = con.execute("SELECT * FROM block WHERE id=?", (bid,)).fetchone()
    for f in BFIELDS:
        if f in data and data[f] != old[f]:
            con.execute(f"UPDATE block SET {f}=?, updated=? WHERE id=?", (data[f], now(), bid))
            con.execute("INSERT INTO log(ts,block_id,field,old,new) VALUES(?,?,?,?,?)", (now(), bid, f, old[f], data[f]))
    con.commit()

def replace_items(con, bid, items):
    cur = {r["id"]: r for r in con.execute("SELECT * FROM item WHERE block_id=?", (bid,))}
    keep = set(); changed = False
    for k, it in enumerate(items):
        iid = it.get("id")
        if iid in cur:
            keep.add(iid); o = cur[iid]
            for f in ("prompt", "answer", "part", "num", "note", "hint", "explain"):
                if (it.get(f) or "") != (o[f] or ""):
                    con.execute("INSERT INTO log(ts,block_id,item_id,field,old,new) VALUES(?,?,?,?,?,?)", (now(), bid, iid, f, o[f], it.get(f) or "")); changed = True
            con.execute("UPDATE item SET ord=?,part=?,num=?,prompt=?,answer=?,note=?,hint=?,explain=? WHERE id=?",
                        (k, it.get("part", ""), it.get("num", ""), it.get("prompt", ""), it.get("answer", ""), it.get("note", ""), it.get("hint", ""), it.get("explain", ""), iid))
            if (o["ord"] != k): changed = True
        else:
            con.execute("INSERT INTO item(block_id,ord,part,num,prompt_ocr,prompt,answer_ocr,answer,note,hint,explain) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (bid, k, it.get("part", ""), it.get("num", ""), "", it.get("prompt", ""), "", it.get("answer", ""), it.get("note", ""), it.get("hint", ""), it.get("explain", "")))
            changed = True
    for iid, o in cur.items():
        if iid not in keep:
            con.execute("INSERT INTO log(ts,block_id,item_id,field,old,new) VALUES(?,?,?,?,?,?)", (now(), bid, iid, "deleted", o["prompt"], "")); con.execute("DELETE FROM item WHERE id=?", (iid,)); changed = True
    if changed:
        con.execute("UPDATE block SET updated=?, status=CASE WHEN status='candidate' THEN 'in_progress' ELSE status END WHERE id=?", (now(), bid))
    con.commit()

def create_block(con, source, s_scan, s_line, e_scan, e_line, section="", note=""):
    """Manual 'insert missing block': e_* exclusive. Items are generated from the selected lines."""
    ordn = con.execute("SELECT COUNT(*) c FROM block WHERE source=? AND section=?", (source, section)).fetchone()["c"] + 1
    bid = con.execute("INSERT INTO block(source,label,section,section_basis,instruction,start_scan,start_line,end_scan,end_line,status,origin,note,key_ref,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (source, "", section, "manual", "", s_scan, s_line, e_scan, e_line, "in_progress", "manual", note, f"{section}:{ordn}" if section else "", now(), now())).lastrowid
    regenerate(con, bid, log=False)
    return bid

def delete_block(con, bid, reason="not an exercise"):   # manual blocks are removed; auto ones are ignored for good (override)
    b = con.execute("SELECT * FROM block WHERE id=?", (bid,)).fetchone()
    if b and b["origin"] == "manual":
        con.execute("DELETE FROM item WHERE block_id=?", (bid,)); con.execute("DELETE FROM block WHERE id=?", (bid,)); con.commit(); return "deleted"
    set_override(con, b, ignored=reason)
    con.execute("INSERT INTO log(ts,block_id,field,old,new) VALUES(?,?,?,?,?)", (now(), bid, "ignored", b["status"], reason))
    apply_overrides(con, bid); return "skipped"

# ---------- key ----------
def key_candidates(con, bid):
    b = con.execute("SELECT * FROM block WHERE id=?", (bid,)).fetchone()
    sec, _, ordn = (b["key_ref"] or "").partition(":")
    sec = sec or b["section"]
    try: ordn = int(ordn)
    except ValueError: ordn = 1
    out, guesses = [], []
    for ks in con.execute("SELECT * FROM source WHERE role='key'"):
        pages = detect.load_pages(con, ks["id"]); alt = ocr.ocr_text(con, ks["id"])
        parts = {r["part"] for r in con.execute("SELECT DISTINCT part FROM item WHERE block_id=?", (bid,))}
        for g in con.execute("SELECT * FROM keyseg WHERE source=? AND section=? AND pair=? ORDER BY start_scan,start_line", (ks["id"], sec, ordn)):
            if parts and g["part"] not in parts and len(parts) < len(key_slots(con, sec)): continue
            lines = detect.drop_footnotes(detect.span_lines(pages, g["start_scan"], g["start_line"], g["end_scan"], g["end_line"]), alt)
            text = " ".join(detect.norm(detect.choose_text(x, alt.get((sc, i)), sd)[0]) for (sc, i, x), sd in zip(lines, detect.line_sides(lines)))
            side = "he" if detect.heb_n(text) > detect.lat_n(text) else "la"
            items = detect.split_items(text, side, tolerant=(side == "he")) or [(str(i), s) for i, s in enumerate(detect.split_sentences(text), 1)]
            out.append({"source": ks["id"], "part": g["part"], "scan": g["start_scan"], "printed": _printed(con, ks["id"], g["start_scan"]),
                        "url": url_for(con, ks["id"], g["start_scan"]), "text": text, "items": [{"num": n, "text": t} for n, t in items]})
        gs = detect.key_guess(get_meta(con, f"keyindex:{ks['id']}", {}) or {}, sec)
        if out and out[0]["source"] == ks["id"]:
            gs = {"scan": out[0]["scan"], "basis": "matched key segment", "scans": sorted({o["scan"] for o in out})}
        if gs:
            gs.update(source=ks["id"], name=ks["name"], section=sec, printed=_printed(con, ks["id"], gs["scan"]), url=url_for(con, ks["id"], gs["scan"]))
            guesses.append(gs)
    return {"segments": out, "guesses": guesses}

def prefill_answers(con, bid, force=False):
    """Fill empty answers from the key: by item label (L3 <-> L3, 4 <-> 4); positionally only when counts match (or force)."""
    cands = key_candidates(con, bid)["segments"]
    items = [dict(r) for r in con.execute("SELECT * FROM item WHERE block_id=? ORDER BY ord", (bid,))]
    report = []
    for part in sorted({i["part"] for i in items}):
        mine = [i for i in items if i["part"] == part]
        ks = [c for c in cands if c["part"] == part]
        if not ks: report.append(f"part {part}: no key segment found"); continue
        k = [kk for c in ks for kk in c["items"]]
        bynum = {kk["num"]: kk["text"] for kk in k}
        pairs = [(it, bynum[it["num"]]) for it in mine if it["num"] in bynum]
        how = "by number"
        if force or (len(k) == len(mine) and len(pairs) < len(mine) / 2):
            pairs, how = [(it, kk["text"]) for it, kk in zip(mine, k)], "by position"
        n = 0
        for it, txt in pairs:
            if not it["answer"]:
                con.execute("UPDATE item SET answer=?, answer_ocr=? WHERE id=?", (txt, txt, it["id"])); n += 1
        miss = len(mine) - len(pairs)
        report.append(f"part {part}: filled {n} {how}" + (f"; {miss} items have no key entry with the same number (key has {len(k)}, block {len(mine)})" if miss > 0 else ""))
    con.commit()
    return report

# ---------- export ----------
def export(con, only="done"):
    out = []
    q = "SELECT * FROM block WHERE status!='skipped'" + (" AND status='done'" if only == "done" else "") + " ORDER BY source,start_scan,start_line"
    held = {k for k, v in overrides(con).items() if v.get("hold")}
    for b in con.execute(q):
        if _okey(b) in held: continue
        its = [dict(r) for r in con.execute("SELECT * FROM item WHERE block_id=? ORDER BY ord", (b["id"],))]
        out.append({"exercise_id": f"ex{b['id']:04d}", "section": b["section"], "exercise_number": b["key_ref"] or b["label"],
                    "instruction": b["instruction"], "review_status": b["status"], "origin": b["origin"],
                    "items": [{"part": i["part"], "num": i["num"], "prompt": i["prompt"], "answer": i["answer"],
                               **({"hint": i["hint"]} if i.get("hint") else {}), **({"explain": i["explain"]} if i.get("explain") else {}), **({"data": json.loads(i["data"])} if i.get("data") else {}),
                               "prompt_ocr": i["prompt_ocr"], "answer_ocr": i["answer_ocr"]} for i in its],
                    "source": {"archive_url": url_for(con, b["source"], b["start_scan"]), "scan_page": b["start_scan"],
                               "end_scan_page": b["end_scan"], "printed_page": _printed(con, b["source"], b["start_scan"])},
                    "note": b["note"]})
    return out
