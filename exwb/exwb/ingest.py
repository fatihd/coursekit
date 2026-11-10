"""Parsers turning OCR files into {scan: {'lines': [{'t','b','d'}], 'w', 'h'}}.

Lines whose words are mostly Hebrew are re-ordered right-to-left by word x position
(OCR exports often store bidi lines in a scrambled order); 'd' records the direction used.
"""
import re, html, collections
from .detect import line_is_rtl

def _clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).replace("‎", "").replace("‏", "").strip()

def _line(words):
    """words: [(text, [x0,y0,x1,y1])] in file order -> line dict in reading order."""
    words = [(t, b) for t, b in words if t]
    if not words: return None
    txt = " ".join(t for t, _ in words)
    d = "ltr"
    if line_is_rtl(txt) and all(b for _, b in words):
        words = sorted(words, key=lambda w: -w[1][0]); d = "rtl"
        txt = " ".join(t for t, _ in words)
    bs = [b for _, b in words if b]
    box = [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)] if bs else None
    return {"t": txt.strip(), "b": box, "d": d}

def parse_djvu_xml(path):
    t = open(path, encoding="utf8").read()
    pages = {}
    for o in re.split(r"(?=<OBJECT )", t)[1:]:
        m = re.search(r'name="PAGE" value="[^"]*?_(\d+)\.djvu"', o) or re.search(r'usemap="[^"]*?_(\d+)\.djvu"', o)
        if not m: continue
        w = re.search(r'width="(\d+)"', o); h = re.search(r'height="(\d+)"', o)
        scan = int(m.group(1)); lines = []
        for ln in re.findall(r"<LINE>(.*?)</LINE>", o, re.S):
            ws = []
            for c, wd in re.findall(r'<WORD coords="([^"]*)"[^>]*>(.*?)</WORD>', ln, re.S):
                a = [int(v) for v in c.split(",")[:4]]
                ws.append((html.unescape(wd).strip(), [min(a[0], a[2]), min(a[1], a[3]), max(a[0], a[2]), max(a[1], a[3])]))
            L = _line(ws)
            if L: lines.append(L)
        pages[scan] = {"lines": lines, "w": int(w.group(1)) if w else None, "h": int(h.group(1)) if h else None}
    return pages

def parse_hocr(path):
    t = open(path, encoding="utf8").read()
    pages = {}
    for chunk in re.split(r'(?=<div class=["\']ocr_page["\'])', t)[1:]:
        m = re.search(r'id=["\']page_(\d+)["\']', chunk)
        if not m: continue
        pb = re.search(r"bbox (\d+) (\d+) (\d+) (\d+)", chunk)
        scan = int(m.group(1)); lines = []; cur = None
        for mm in re.finditer(r'<span class=["\']ocr_line["\'][^>]*title=["\']([^"\']*)["\']|'
                              r'<span class=["\']ocrx_word["\'][^>]*title=["\']([^"\']*)["\'][^>]*>(.*?)</span>', chunk, re.S):
            if mm.group(1) is not None:
                cur = []; lines.append(cur)
            elif cur is not None:
                b = re.search(r"bbox (\d+) (\d+) (\d+) (\d+)", mm.group(2) or "")
                cur.append((_clean(mm.group(3)), [int(x) for x in b.groups()] if b else None))
        out = [L for L in (_line(ws) for ws in lines) if L]
        pages[scan] = {"lines": out, "w": int(pb.group(3)) if pb else None, "h": int(pb.group(4)) if pb else None}
    return pages

def parse_text(path, first_scan=1):
    t = open(path, encoding="utf8").read()
    parts = t.split("\f") if "\f" in t else [t]
    return {first_scan + i: {"lines": [{"t": l.strip(), "b": None, "d": "ltr"} for l in p.splitlines() if l.strip()], "w": None, "h": None}
            for i, p in enumerate(parts)}

PARSERS = {"djvu-xml": parse_djvu_xml, "hocr": parse_hocr, "text": parse_text}

def detect_offset(pages):
    """Vote for scan - printed_number using bare numbers at page tops/bottoms."""
    votes = collections.Counter()
    for scan, pg in pages.items():
        lines = pg["lines"]
        for l in lines[:1] + lines[-1:]:
            for m in re.finditer(r"(?:^|\s)(\d{1,3})(?:\s|$)", l["t"]):
                n = int(m.group(1))
                if 1 <= n <= 999 and scan - n >= 0: votes[scan - n] += 1
    return votes.most_common(1)[0][0] if votes else 0
