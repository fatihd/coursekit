"""Corpus expansion for the Davidson course (ROADMAP P12-T5, AGENTS.md §0).

Two sources of new ladder sentences, both placed in the first unit whose words and grammar they need:

* `corpus.json` — sentences written for this course. Every Hebrew word must be attested: the same
  pointed form (accents and metheg ignored) in the Hebrew Bible (OSHB), in Davidson's own exercises,
  or in the course word list. Its OSHB analyses give the lemma (must be a course word) and the grammar
  it shows (article, suffix, stem, conjugation, ...). `corpus-forms.json` keeps those analyses so the
  course builds without the OSHB cache.
* `bible-excerpts.json` — whole verses of the Hebrew Bible that use only course words, with the
  World English Bible (public domain) as the translation.

    python build/davidson_corpus.py forms [--check]   # analyse corpus.json words -> corpus-forms.json
    python build/davidson_corpus.py bible [--check]   # select verses -> bible-excerpts.json
    python build/davidson_corpus.py report            # sentences per unit
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "build" / "_sources" / "davidson"
CORPUS = SRC / "corpus.json"
FORMS = SRC / "corpus-forms.json"
BIBLE = SRC / "bible-excerpts.json"
GRAMMAR = SRC / "grammar-units.json"
CURATED = ROOT / "exwb" / "curated"
VOCAB = ROOT / "courses" / "biblical-hebrew-davidson" / "content" / "vocab.csv"
OSHB = ROOT / "build" / "_oer" / "morphhb" / "books"
WEB = ROOT / "build" / "_oer" / "web" / "engwebp_vpl.txt"
OSIS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"

HEB = re.compile(r"[א-ת]")
MARKS = re.compile(r"[\u0591-\u05af\u05bd\u05bf\u05c0\u05c3-\u05c6]")
PREFIX_LEMMAS = {"b", "l", "k", "m", "c", "d", "i"}
STEMS = {"N": "niphal", "p": "piel", "P": "pual", "h": "hiphil", "H": "hophal", "t": "hitpael",
         "o": "piel", "O": "pual", "r": "hitpael", "m": "piel", "M": "pual", "l": "piel", "L": "pual",
         "Q": "pual", "v": "hitpael"}
CONJ = {"q": "weqatal", "i": "yiqtol", "w": "wayyiqtol", "h": "jussive", "j": "jussive", "v": "imperative",
        "r": "participle", "s": "participle", "a": "infinitive", "c": "infinitive"}
PE_ALEPH = {"אכל", "אמר", "אבד", "אבה", "אפה"}
LEMMA_FEATURES = {2009: "particle", 2005: "particle", 5750: "particle", 227: "particle", 369: "question",
                  3426: "question"}

BOOKS = ["Gen", "Exod", "Lev", "Num", "Deut", "Josh", "Judg", "Ruth", "1Sam", "2Sam", "1Kgs", "2Kgs", "1Chr",
         "2Chr", "Ezra", "Neh", "Esth", "Job", "Ps", "Prov", "Eccl", "Song", "Isa", "Jer", "Lam", "Ezek", "Dan",
         "Hos", "Joel", "Amos", "Obad", "Jonah", "Mic", "Nah", "Hab", "Zeph", "Hag", "Zech", "Mal"]
WEB_BOOKS = ["GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA", "1KI", "2KI", "1CH", "2CH",
             "EZR", "NEH", "EST", "JOB", "PSA", "PRO", "ECC", "SNG", "ISA", "JER", "LAM", "EZK", "DAN", "HOS",
             "JOL", "AMO", "OBA", "JON", "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL"]
BOOK_NAMES = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
              "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah",
              "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Songs", "Isaiah", "Jeremiah",
              "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum",
              "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi"]


def norm(word: str) -> str:
    w = unicodedata.normalize("NFD", word.replace("/", ""))
    w = MARKS.sub("", w).replace("ׇ", "ָ").replace("ֺ", "ֹ")
    w = re.sub(r"[^א-תְ-ּׁׂ]", "", w)
    return unicodedata.normalize("NFC", w)


def words_of(text: str) -> list[str]:
    return [w for w in (norm(t) for t in re.split(r"[\s־]+", text)) if HEB.search(w)]


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------------------- course data

@lru_cache(maxsize=1)
def vocab() -> list[dict]:
    with VOCAB.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def strong_units() -> dict[int, int]:
    out: dict[int, int] = {}
    for r in vocab():
        for s in re.findall(r"\d+", r["strong"] or ""):
            out[int(s)] = min(out.get(int(s), 999), int(r["unit"]))
    return out


@lru_cache(maxsize=1)
def strong_roots() -> dict[int, str]:
    out: dict[int, str] = {}
    for r in vocab():
        for s in re.findall(r"\d+", r["strong"] or ""):
            if r["category"] == "verb" and r["root"]:
                out.setdefault(int(s), r["root"])
    return out


@lru_cache(maxsize=1)
def grammar() -> dict:
    return json.loads(GRAMMAR.read_text(encoding="utf-8"))


def feature_unit(feature: str) -> int:
    feats = grammar()["features"]
    if feature not in feats:
        raise KeyError(f"unknown grammar feature {feature!r}")
    return feats[feature]["unit"]


# ---------------------------------------------------------------- OSHB

def oshb_verses():
    """(book index, chapter, verse, [(text, lemma, morph)], display text) for every verse with only Hebrew
    words and no Ketiv/Qere."""
    for bi, book in enumerate(BOOKS):
        path = OSHB / f"{book}.xml"
        if not path.is_file():
            continue
        for v in ET.parse(path).getroot().iter(f"{OSIS}verse"):
            _, ch, vs = v.get("osisID").split(".")
            words, shown, ok = [], "", True
            for node in v:
                if node.tag == f"{OSIS}w":
                    morph = node.get("morph", "")
                    if not morph.startswith("H") or node.get("type") == "x-ketiv" or not (node.text or "").strip():
                        ok = False
                        break
                    words.append((node.text.strip(), node.get("lemma", ""), morph))
                    shown += ("" if not shown or shown.endswith("־") else " ") + node.text.strip()
                elif node.tag == f"{OSIS}seg" and node.get("type") == "x-maqqef":
                    shown += "־"
                elif node.tag == f"{OSIS}note":
                    ok = False
                    break
            if ok and words:
                yield bi, int(ch), int(vs), words, shown


def segments(lemma: str, morph: str) -> list[tuple[str, str]]:
    """Pair the morph segments with their lemma parts (suffix segments have none)."""
    parts = morph[1:].split("/")
    lems = lemma.split("/")
    out, li = [], 0
    for p in parts:
        if p.startswith("S"):
            out.append((p, ""))
        else:
            out.append((p, lems[li].strip() if li < len(lems) else ""))
            li += 1
    return out


def weak_classes(root: str, form_is_lexical: bool, stem: str = "q") -> list[str]:
    """Weak-verb classes a form of `root` may show (none for the dictionary form). Resh counts as a guttural
    in the middle only where the stem doubles it (Piel, Pual, Hitpael)."""
    if form_is_lexical or len(root) != 3:
        return []
    r = root.translate(str.maketrans("ךםןףץ", "כמנפצ"))
    out = []
    if r[0] == "נ":
        out.append("pe-nun")
    if r[0] == "א" and root in PE_ALEPH:
        out.append("pe-aleph")
    elif r[0] in "אהחע":
        out.append("pe-guttural")
    if r[0] in "יו":
        out.append("pe-yod")
    if r[1] in "וי" and r[2] != "ה":
        out.append("hollow")
    elif r[1] in "אהחע" or (r[1] == "ר" and stem in "pPt"):
        out.append("ayin-guttural")
    if r[1] == r[2]:
        out.append("geminate")
    if r[2] == "ה":
        out.append("lamed-he")
    elif r[2] == "א":
        out.append("lamed-aleph")
    elif r[2] in "חע":
        out.append("lamed-guttural")
    return out


def analyse(lemma: str, morph: str) -> dict:
    """Lemma (Strong's number), proper-name flag and grammar features of one OSHB word."""
    feats: set[str] = set()
    strong = None
    name = False
    host = None
    segs = segments(lemma, morph)
    for seg, lem in segs:
        kind = seg[0]
        num = re.match(r"\d+", lem or "")
        if kind == "S":
            if seg.startswith("Sd"):
                feats.add("he-locale")
            elif seg.startswith("Sp"):
                feats |= {"N": {"suffix"}, "A": {"suffix"}, "R": {"prep-suffix"}, "V": {"verb-suffix"},
                          "T": {"object-marker", "prep-suffix"} if host == "To" else {"particle"} if host == "Tm"
                          else {"question"} if host in ("Tn", "Ti") else {"suffix"},
                          "D": {"suffix"}, "P": {"suffix"}, "C": {"suffix"}}.get((host or "N")[0], {"suffix"})
            continue
        host = seg[:2] if kind in "TP" else seg[0]
        if lem in PREFIX_LEMMAS and kind in "RCT":
            if kind == "R":
                feats.add("prefix-prep")
                if seg.startswith("Rd"):
                    feats.add("article")
            elif kind == "C" and lem == "c":
                feats.add("waw")
            elif seg == "Td":
                feats.add("article")
            elif seg == "Ti":
                feats.add("question")
            continue
        if num:
            strong = int(num.group())
            if strong in LEMMA_FEATURES:
                feats.add(LEMMA_FEATURES[strong])
        if kind == "R" and seg.startswith("Rd"):
            feats.add("article")
        if kind == "N":
            if seg.startswith("Np"):
                name = True
            if len(seg) >= 5 and seg[3] in "pd":
                feats.add("plural")
            if seg.endswith("c"):
                feats.add("construct")
        elif kind == "A":
            feats.add("numeral" if seg[:2] in ("Ac", "Ao") else "adjective")
            if seg.endswith("c"):
                feats.add("construct")
        elif kind == "P":
            feats.add({"Pd": "demonstrative", "Pi": "question-word", "Pr": "relative"}.get(seg[:2], "pronoun"))
        elif kind == "T":
            if seg.startswith("Ti") and strong in (4310, 4100):
                feats.add("question-word")
            else:
                feats |= {"Td": {"article"}, "Ti": {"question"}, "To": {"object-marker"}, "Tr": {"relative"}}.get(seg[:2], set())
        elif kind == "V":
            stem, conj, pgn = seg[1], seg[2], seg[3:]
            if stem in STEMS:
                feats.add(STEMS[stem])
            if conj == "p":
                if stem == "q" and pgn != "3ms":
                    feats.add("qatal")
            elif conj in CONJ:
                feats.add(CONJ[conj])
            lexical = stem == "q" and conj in "pq" and pgn == "3ms"
            if strong is not None and strong in strong_roots():
                feats |= set(weak_classes(strong_roots()[strong], lexical, stem))
    return {"strong": strong, "name": name, "features": sorted(feats)}


# ---------------------------------------------------------------- attestation index

@lru_cache(maxsize=1)
def oshb_forms() -> dict[str, Counter]:
    """Every Hebrew word form of the OSHB (Qere readings, not Ketiv) with its (lemma, morph) counts."""
    out: dict[str, Counter] = defaultdict(Counter)
    for book in BOOKS:
        path = OSHB / f"{book}.xml"
        if not path.is_file():
            continue
        for w in ET.parse(path).getroot().iter(f"{OSIS}w"):
            morph = w.get("morph", "")
            if morph.startswith("H") and w.get("type") != "x-ketiv" and (w.text or "").strip():
                out[norm(w.text)][(w.get("lemma", ""), morph)] += 1
    return out


@lru_cache(maxsize=1)
def davidson_forms() -> set[str]:
    out = set()
    for path in CURATED.glob("davidson-*.json"):
        for it in json.loads(path.read_text(encoding="utf-8"))["items"]:
            for field in ("prompt", "answer"):
                out |= set(words_of(it.get(field) or ""))
    return out


def vocab_analyses(word: str) -> list[dict]:
    out = []
    for r in vocab():
        forms = [r["scriptForm"], r["plural"]] + [f for f in (r.get("forms") or "").split(";") if f]
        if word in {norm(f) for f in forms if f}:
            nums = re.findall(r"\d+", r["strong"] or "")
            out.append({"strong": int(nums[0]) if nums else None, "vocab": r["id"], "name": False,
                        "features": ["plural"] if norm(r["plural"] or "") == word else []})
    return out


def analyses_for(word: str) -> dict:
    found = oshb_forms().get(word)
    entry: dict = {"attested": []}
    if found:
        entry["attested"].append("oshb")
        seen = []
        for (lemma, morph), _ in found.most_common():
            a = analyse(lemma, morph)
            a["morph"] = morph
            if not any(x["strong"] == a["strong"] and x["features"] == a["features"] for x in seen):
                seen.append(a)
        entry["analyses"] = seen
    else:
        entry["analyses"] = []
    if word in davidson_forms():
        entry["attested"].append("davidson")
    va = vocab_analyses(word)
    if va:
        entry["attested"].append("vocab")
        entry["analyses"] += [a for a in va if not any(x["strong"] == a["strong"] for x in entry["analyses"])]
    return entry


# ---------------------------------------------------------------- placement

def analysis_unit(a: dict, floor: int) -> int | None:
    units = strong_units()
    if a.get("vocab"):
        base = next(int(r["unit"]) for r in vocab() if r["id"] == a["vocab"])
    elif a["strong"] is None:
        base = floor
    elif a["strong"] in units:
        base = units[a["strong"]]
    elif a["name"]:
        base = floor
    else:
        return None
    return max([base, floor] + [feature_unit(f) for f in a["features"]])


def word_unit(entry: dict, floor: int, plain: bool = False) -> int | None:
    """Unit of a word's most frequent reading (OSHB analyses come most frequent first; names only when the
    form has no other reading)."""
    weak = {"pe-nun", "pe-guttural", "pe-aleph", "ayin-guttural", "lamed-guttural", "lamed-aleph", "pe-yod",
            "hollow", "geminate", "lamed-he"}
    analyses = entry["analyses"]
    if any(not a["name"] for a in analyses):
        analyses = [a for a in analyses if not a["name"]]
    for a in analyses:
        if plain:
            a = {**a, "features": [f for f in a["features"] if f not in weak]}
        u = analysis_unit(a, floor)
        if u is not None:
            return u
    return None


def sentence_unit(hebrew: str, forms: dict, tags: list[str], plain: list[str] | None = None) -> tuple[int | None, list[str]]:
    """First unit where every word and every tagged feature of a sentence is taught; problems listed."""
    floor = grammar()["floor"]
    plain_set = {norm(p) for p in (plain or [])}
    problems = []
    unit = max([floor] + [feature_unit(t) for t in tags])
    for w in words_of(hebrew):
        entry = forms.get(w)
        if not entry or not entry["attested"]:
            problems.append(f"{w}: not attested")
            continue
        u = word_unit(entry, floor, w in plain_set)
        if u is None:
            problems.append(f"{w}: lemma not in the course word list")
            continue
        unit = max(unit, u)
    return (None if problems else unit), problems


# ---------------------------------------------------------------- commands

def load_corpus() -> dict:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def corpus_words(corpus: dict) -> list[str]:
    out = set()
    for s in corpus["sentences"]:
        for h in s["hebrew"]:
            out |= set(words_of(h))
    return sorted(out)


def build_forms() -> dict:
    corpus = load_corpus()
    forms = {w: analyses_for(w) for w in corpus_words(corpus)}
    return {"note": "Analyses of every Hebrew word in corpus.json: where it is attested (OSHB = Open Scriptures "
                    "Hebrew Bible, CC BY 4.0 morphology; davidson = the grammar's own exercises; vocab = the course "
                    "word list), its lemma (Strong's number) and the grammar it shows. Written by "
                    "build/davidson_corpus.py forms.", "forms": forms}


def cmd_forms(check: bool) -> int:
    if not OSHB.is_dir():
        sys.exit("OSHB cache missing: python build/fetch_oer.py --source morphhb")
    data = build_forms()
    text = dump(data)
    bad = {w: e for w, e in data["forms"].items() if not e["attested"]}
    for w in bad:
        print(f"not attested: {w}")
    if check:
        if not FORMS.is_file() or FORMS.read_text(encoding="utf-8") != text:
            print(f"out of date: {FORMS.relative_to(ROOT)}")
            return 1
        print(f"up to date: {len(data['forms'])} words")
        return 0
    FORMS.write_text(text, encoding="utf-8")
    print(f"wrote {FORMS.relative_to(ROOT)}: {len(data['forms'])} words, {len(bad)} not attested")
    return 0


def web_verses() -> dict[tuple[int, int, int], str]:
    out = {}
    idx = {b: i for i, b in enumerate(WEB_BOOKS)}
    for line in WEB.read_text(encoding="utf-8").splitlines():
        m = re.match(r"(\w+) (\d+):(\d+) (.*)", line)
        if m and m.group(1) in idx:
            out[(idx[m.group(1)], int(m.group(2)), int(m.group(3)))] = m.group(4).strip()
    return out


def clean_english(text: str, has_yhwh: bool) -> str:
    t = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"(\s+[A-Z]{2,}(\s+(AND\s+)?[A-Z]{2,})*)$", "", t)
    if has_yhwh:
        t = re.sub(r"\bLORD\b", "Yahweh", t)
        t = re.sub(r"\bthe Yahweh\b", "Yahweh", t)
        t = re.sub(r"\bThe Yahweh\b", "Yahweh", t)
    return t


def gloss_overlap(words: list[tuple[str, str, str]], english: str) -> float:
    gl = {}
    for r in vocab():
        for s in re.findall(r"\d+", r["strong"] or ""):
            gl.setdefault(int(s), r["gloss"])
    low = english.lower()
    hits = total = 0
    for _, lemma, morph in words:
        a = analyse(lemma, morph)
        if a["strong"] in gl and morph[1:2] in ("N", "V", "A"):
            total += 1
            keys = [k for k in re.findall(r"[a-z]+", gl[a["strong"]].lower()) if k not in {"he", "the", "a", "of", "to"}]
            if any(k[:4] in low for k in keys):
                hits += 1
    return hits / total if total else 1.0


def select_bible(max_words: int = 14) -> dict:
    floor = grammar()["floor"]
    web = web_verses()
    heb_counts = Counter()
    for b, c, _, _, _ in oshb_verses():
        heb_counts[(b, c)] += 1
    web_counts = Counter((b, c) for b, c, _ in web)
    picked = []
    seen = set()
    for b, c, v, words, shown in oshb_verses():
        if len(words) > max_words or heb_counts[(b, c)] != web_counts[(b, c)] or (b, c, v) not in web:
            continue
        names = 0
        unit = floor
        ok = True
        for _, lemma, morph in words:
            a = analyse(lemma, morph)
            names += a["name"]
            u = analysis_unit(a, floor)
            if u is None:
                ok = False
                break
            unit = max(unit, u)
        if not ok or names > 2:
            continue
        hebrew = MARKS.sub("", unicodedata.normalize("NFD", shown.replace("/", "")))
        hebrew = unicodedata.normalize("NFC", hebrew.replace("ׇ", "ָ")).strip()
        if norm(hebrew) in seen:
            continue
        has_yhwh = any(re.match(r"3068|3069", lem.split("/")[-1]) for _, lem, _ in words)
        english = clean_english(web[(b, c, v)], has_yhwh)
        if ('"' in english or not english[:1].isupper() or english[-1] not in ".!?" or len(english.split()) > 40
                or gloss_overlap(words, english) < 0.5):
            continue
        seen.add(norm(hebrew))
        picked.append({"ref": f"{BOOKS[b]}.{c}.{v}", "cite": f"{BOOK_NAMES[b]} {c}:{v}", "unit": unit,
                       "hebrew": hebrew, "english": english})
    picked.sort(key=lambda x: (x["unit"], BOOKS.index(x["ref"].split(".")[0]), int(x["ref"].split(".")[1]),
                               int(x["ref"].split(".")[2])))
    return {"note": "Whole verses of the Hebrew Bible that use only course words, placed in the first unit whose "
                    "words and grammar they need (grammar read from the OSHB morphology). Hebrew: Westminster "
                    "Leningrad Codex via the Open Scriptures Hebrew Bible (text public domain, morphology CC BY 4.0), "
                    "cantillation removed. English: World English Bible (public domain), with LORD written Yahweh. "
                    "Only chapters with the same verse division in both are used. Written by "
                    "build/davidson_corpus.py bible.", "verses": picked}


def cmd_bible(check: bool) -> int:
    if not OSHB.is_dir() or not WEB.is_file():
        sys.exit("cache missing: python build/fetch_oer.py --source morphhb and --source web")
    data = select_bible()
    text = dump(data)
    by_unit = Counter(v["unit"] for v in data["verses"])
    if check:
        if not BIBLE.is_file() or BIBLE.read_text(encoding="utf-8") != text:
            print(f"out of date: {BIBLE.relative_to(ROOT)}")
            return 1
        print(f"up to date: {len(data['verses'])} verses")
        return 0
    BIBLE.write_text(text, encoding="utf-8")
    print(f"wrote {BIBLE.relative_to(ROOT)}: {len(data['verses'])} verses; per unit {dict(sorted(by_unit.items()))}")
    return 0


def cmd_report() -> int:
    corpus = load_corpus()
    forms = json.loads(FORMS.read_text(encoding="utf-8"))["forms"]
    per = Counter()
    bad = 0
    for s in corpus["sentences"]:
        unit, problems = sentence_unit(s["hebrew"][0], forms, s.get("tags", []), s.get("plain"))
        if problems or unit != s["unit"]:
            bad += 1
            print(f"{s['id']}: declared {s['unit']}, computed {unit}; {'; '.join(problems)}")
        per[s["unit"]] += 1
    print(f"{len(corpus['sentences'])} sentences, {bad} with problems; per unit {dict(sorted(per.items()))}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["forms", "bible", "report"])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.command == "forms":
        return cmd_forms(args.check)
    if args.command == "bible":
        return cmd_bible(args.check)
    return cmd_report()


if __name__ == "__main__":
    sys.exit(main())
