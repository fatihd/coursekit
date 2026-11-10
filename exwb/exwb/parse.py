"""Split a key's grammatical parse ("2 sing. masc. impf. Qal of שׁמר. Thou wilt keep") into structured fields."""
import re

STEMS = [("Hithpa'el", r"Hithpa(?:'?el|\.)|Hithp\."), ("Hithpo'lel", r"Hithpo'?lel"), ("Po'lel", r"Po'?lel"), ("Niph'al", r"Niph(?:'?al|\.)"),
         ("Pi'el", r"Pi(?:'?el|\.)"), ("Pu'al", r"Pu(?:'?al|\.)"), ("Hiph'il", r"Hiph(?:'?il|\.)"), ("Hoph'al", r"Hoph(?:'?al|\.)"), ("Qal", r"Qal")]
FORMS = [("cohortative", r"cohortat(?:ive|\.)"), ("jussive", r"jussive|juss\."), ("imperative", r"imperat(?:ive|\.)|imper\."),
         ("infinitive construct", r"(?:cstr\.|construct) inf\.|inf\.\s*(?:cstr\.|construct)"), ("infinitive absolute", r"inf\.\s*abs\.|abs\. inf\."),
         ("participle", r"ptc\.|participle"), ("imperfect", r"impf\.|imperfect"), ("perfect", r"(?<![a-z])pf\.|perfect")]
HEB = r"[א-ת][֑-ׇא-ת]*"

def _first(alts, text):
    best = None
    for name, rx in alts:
        m = re.search(rx, text)
        if m and (best is None or m.start() < best[1]): best = (name, m.start())
    return best[0] if best else None

PARSE_START = re.compile(r"\s*(?:\d|sing|plur|pl\.|masc|fem|inf|abs|cstr|ptc|\(scriptio)")

SUFF = re.compile(r"(?:with\s+)?(\d\s*(?:sing|plur|pl|s)\.?\s*(?:masc\.|fem\.|m\.|f\.)?\s*suff\w*\.?)")

def _fields(head):
    d = {}
    sf = SUFF.search(head)
    if sf: d["suffix"] = sf.group(1).strip(); head = head[:sf.start()] + head[sf.end():]
    m = re.match(r"\s*(\d)(?:\s*(?:or|,)\s*(\d))?\s", head)
    if m: d["person"] = m.group(1) + (f" or {m.group(2)}" if m.group(2) else "")
    g = re.findall(r"\b(masc|fem|m|f)\.", head)
    if g: d["gender"] = " or ".join(dict.fromkeys("masc." if x.startswith("m") else "fem." for x in g))
    n = re.search(r"\b(sing|plur|pl|plu|dual|du|s)\.?(?=\s|$)", head)
    if n: d["number"] = {"sing": "sing.", "s": "sing.", "plur": "plur.", "pl": "plur.", "plu": "plur.", "dual": "dual", "du": "dual"}[n.group(1)]
    f = _first(FORMS, head); st = _first(STEMS, head)
    if f: d["form"] = f
    if st: d["stem"] = st
    sm = re.search(r"\b(abs|cstr)\.", head)
    if sm and not (f or "").startswith("infinitive"): d["state"] = "absolute" if sm.group(1) == "abs" else "construct"
    if "suffix" not in d and re.search(r"suff", head): d["suffix"] = "yes"
    if re.search(r"waw consec", head): d["waw"] = "consecutive"
    elif re.search(r"simple waw", head): d["waw"] = "simple"
    return d

def _split_alt(t):
    """first analysis, alternative analysis ('… or 3 sing. …', '…; or …', '…; also …')."""
    m = re.search(r"(?:;\s*(?:or|also|may also be|it might also be|might also be)\s+|\s+or\s+(?=(?:\d|sing|plur|pl\.|masc|fem|inf|cstr|abs|ptc|2 s|3 s)))", t)
    return (t[:m.start()], t[m.end():].strip(" .")) if m else (t, "")

def parse_answer(text):
    """{person, gender, number, form, stem, state, root, suffix, waw, gloss, alt} for the first analysis; {} if not a parse."""
    t = text.strip()
    if not PARSE_START.match(t):                     # 'Translation (parse)' style
        for pm in re.finditer(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)", t):
            inner = pm.group(1)
            if _first(STEMS, inner) or _first(FORMS, inner):
                first, alt = _split_alt(inner)
                d = _fields(first)
                rm = re.search(r"\bof\s+(" + HEB + r")", inner)
                if rm: d["root"] = rm.group(1)
                d["gloss"] = re.sub(r"\s+", " ", re.split(r";\s*or\b", t[:pm.start()] + t[pm.end():])[0]).strip(" .;")
                if alt: d["alt"] = alt
                ao = re.search(r";\s*or\s+(.*)$", t[pm.end():])
                if ao and "alt" not in d: d["alt"] = ao.group(1).strip(" .")
                return d
        return {}
    t0 = re.sub(r"\s*\((?:or|also)[^()]*\)", "", t)          # '(or inf. cstr.)' asides
    first, alt = _split_alt(t0)
    rm = re.search(r"\bof\s+(" + HEB + r")", t0)
    if not rm and not _first(STEMS, first): return {}
    d = _fields(first[:rm.start()] if rm and rm.start() < len(first) else first)
    if alt:                                        # '2 sing. masc. or 3 sing. fem. impf. Qal': shared form/stem follow the 'or'
        shared = _fields(alt)
        for k in ("form", "stem"):
            if k not in d and k in shared: d[k] = shared[k]
    if rm: d["root"] = rm.group(1)
    tail = (first[rm.end():] if rm.start() < len(first) else t0[rm.end():]) if rm else ""
    gm = re.search(r"\.\s+([A-Z(][^;]*?)\s*(?:;|$)", tail) or re.match(r",\s+([A-Z][^;]*?)\s*(?:;|$)", tail)
    if gm and not re.match(r"(?:Cf|See|With)\b|\(", gm.group(1)) and not re.search(r"\b(?:Qal|Niph|Pi|Pu|Hiph|Hoph)\.\)?$", gm.group(1)): d["gloss"] = gm.group(1).strip(" .")
    if alt: d["alt"] = alt
    return d
