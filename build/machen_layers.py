#!/usr/bin/env python3
"""Frequency layers of the Machen Greek course vocabulary (ROADMAP P11-T5, ADR-025).

Machen's lesson vocabularies cover most, but not all, of the New Testament's common words. This module adds two
layers, decided by the user on 2026-11-13:

* **core** — every NT lemma that occurs 50 times or more (MorphGNT counts) and is not in Machen's vocabularies,
  placed in the first unit whose grammar it needs (or earlier, when Machen's sentences already use it);
* **reading** — the lemmas that occur 10–49 times, in an optional reading-vocabulary part after the last lesson
  (Words track only, ADR-023; nothing unlocks through it).

Glosses come from Jeffrey Dodson's public-domain Greek–English lexicon (`build/_sources/dodson/`, fetched with
`python scripts/fetch-sources dodson`), shortened to its first senses; `layers-overrides.json` holds the glosses,
headwords, categories and units decided by hand. The result is written to `frequency-layers.json`, so the course
builds without the downloads; `build/machen_course.py` reads it.

    python build/machen_layers.py [--check]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import greek_corpus as GC
import greek_text as G

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "build" / "_sources" / "machen"
MAP = SRC / "course-map.json"
OUT = SRC / "frequency-layers.json"
OVERRIDES = SRC / "layers-overrides.json"
DODSON = ROOT / "build" / "_sources" / "dodson" / "dodson.xml"
MORPHGNT = ROOT / "build" / "_sources" / "morphgnt"
CURATED = ROOT / "exwb" / "curated"
NS = "{http://www.crosswire.org/2008/TEIOSIS/namespace}"
CORE_MIN, READING_MIN = 50, 10
READING_PER_UNIT = 50
POS_CATEGORY = {"N-": "noun", "V-": "verb", "A-": "adjective", "D-": "adverb", "C-": "conjunction", "P-": "preposition",
                "X-": "particle", "I-": "particle", "RA": "article", "RD": "pronoun", "RI": "pronoun", "RP": "pronoun",
                "RR": "pronoun"}
NUMBERS = {"two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "twenty", "thirty",
           "forty", "fifty", "one hundred", "a thousand", "seventy", "ten thousand"}
UNIT = {"verb": 3, "deponent": 10, "contract": 23, "mi": 31, "second": 4, "first-f": 5, "first-m": 7, "third": 17,
        "third-late": 25, "adjective": 6, "adjective-3": 25, "numeral": 26, "pronoun": 8, "preposition": 7, "other": 4}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def morphgnt() -> tuple[Counter, dict[str, Counter]]:
    counts, pos = Counter(), defaultdict(Counter)
    for f in sorted(MORPHGNT.glob("*-morphgnt.txt")):
        for line in f.read_text(encoding="utf-8").splitlines():
            p = line.split(" ")
            counts[nfc(p[6])] += 1
            pos[nfc(p[6])][p[1]] += 1
    return counts, pos


def dodson() -> dict[str, list[tuple[str, str, str]]]:
    out: dict[str, list] = defaultdict(list)
    for e in ET.parse(DODSON).getroot().iter(NS + "entry"):
        head = nfc(e.get("n").split("|")[0].strip())
        orth = nfc(" ".join((e.find(NS + "orth").text or "").split()))
        brief = " ".join((e.find(NS + "def[@role='brief']").text or "").split())
        out[G.bare(head)].append((head, orth, brief))
    return out


def lookup(dod: dict, lemma: str) -> tuple[str, str, str] | None:
    entries = dod.get(G.bare(lemma), [])
    exact = [e for e in entries if e[0] == lemma]
    return (exact or entries or [None])[0]


def short_gloss(text: str, verb: bool) -> str:
    text = re.sub(r"\s*\(.*?\)", "", text).strip().rstrip(".;,")
    parts = [p.strip() for p in re.split(r"[;,]\s*", text) if p.strip()]
    gloss = ", ".join(dict.fromkeys(parts[:3]))
    if verb and gloss and not gloss.startswith("I "):
        gloss = "I " + gloss
    return gloss


def headword(lemma: str) -> str:
    return re.sub(r"\(.*?\)", "", lemma)


def gender(orth: str) -> str:
    m = re.search(r",\s*(ὁ|ἡ|τό)\s*$", orth)
    return {"ὁ": "m", "ἡ": "f", "τό": "n"}.get(m.group(1), "") if m else ""


def grammar_unit(lemma: str, category: str, orth: str) -> int:
    b = G.bare(lemma)
    if category == "verb":
        if b.endswith("μι") or b.endswith("αμαι"):
            return UNIT["mi"]
        if re.search(r"(αω|εω|οω|αομαι|εομαι|οομαι)$", b):
            return UNIT["contract"]
        return UNIT["deponent"] if b.endswith("ομαι") else UNIT["verb"]
    if category == "noun":
        gen = re.match(r"[^,]+,\s*([^,]+),", orth)
        g = G.bare(gen.group(1)) if gen else ""
        if not g:
            return UNIT["other"]
        if g.endswith("εωσ") or g.endswith("ουσ"):
            return UNIT["third-late"]
        if g in ("ου", "ουσ") or g.endswith("ου"):
            return UNIT["first-m"] if re.search(r"(ησ|ασ)$", b) else UNIT["second"]
        if g in ("ασ", "ησ") or g.endswith("ασ") and not g.endswith("ατοσ") or g.endswith("ησ"):
            return UNIT["first-f"]
        return UNIT["third"]
    if category == "adjective":
        if re.search(r"ησ$", b) and "ες" in orth:
            return UNIT["adjective-3"]
        return UNIT["adjective"]
    if category == "pronoun":
        return UNIT["pronoun"]
    if category == "preposition":
        return UNIT["preposition"]
    return UNIT["other"]


def first_use() -> dict[str, int]:
    forms = json.loads((SRC / "greek-forms.json").read_text(encoding="utf-8"))["forms"]
    out: dict[str, int] = {}
    for path in sorted(CURATED.glob("machen-l*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for it in data["items"]:
            text = it["prompt"] if it["part"] == "I" else it["answer"]
            for w in G.greek_words(text):
                for a in forms.get(GC.wkey(w), [])[:1]:
                    out[a["lemma"]] = min(out.get(a["lemma"], 99), data["lesson"])
    return out


def covered(cmap: dict, aliases: dict[str, str]) -> set[str]:
    out = set()
    for u in cmap["units"]:
        for w in u["vocab"]:
            out.add(G.bare(w[4] if len(w) > 4 and w[4] else w[0]))
    out |= {G.bare(k) for k, v in aliases.items() if v is None}
    return out


def entry(lemma: str, count: int, pos: Counter, dod: dict, over: dict, aliases: dict) -> dict:
    o = over.get(lemma, {})
    found = lookup(dod, aliases.get(lemma) or lemma)
    orth, brief = (found[1], found[2]) if found else ("", "")
    category = o.get("category") or POS_CATEGORY.get(pos.most_common(1)[0][0], "particle")
    if not o.get("category") and category == "adjective":
        if gender(orth):
            category = "noun"
        elif short_gloss(brief, False) in NUMBERS:
            category = "numeral"
    return {"lemma": lemma, "count": count, "headword": o.get("headword") or headword(lemma),
            "gloss": o.get("gloss") or short_gloss(brief, category == "verb"), "category": category,
            "gender": o.get("gender", gender(orth) if category == "noun" else ""), "dodson": orth}


def build() -> dict:
    cmap = json.loads(MAP.read_text(encoding="utf-8"))
    over = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    aliases, words = over["aliases"], over["words"]
    counts, pos = morphgnt()
    dod = dodson()
    have = covered(cmap, aliases)
    used = first_use()
    last = max(u["n"] for u in cmap["units"])
    core, reading = [], []
    for lemma, c in sorted(counts.items(), key=lambda kv: (-kv[1], G.bare(kv[0]))):
        o = words.get(lemma, {})
        if c < READING_MIN or o.get("skip") or G.bare(lemma) in have and not o.get("force"):
            continue
        e = entry(lemma, c, pos[lemma], dod, words, aliases)
        if c >= CORE_MIN:
            unit = words.get(lemma, {}).get("unit") or min(grammar_unit(lemma, e["category"], e["dodson"]),
                                                             used.get(lemma, 99))
            core.append({**e, "unit": unit})
        else:
            reading.append(e)
    missing = [e["lemma"] for e in core + reading if not e["gloss"]]
    if missing:
        sys.exit(f"no gloss for: {', '.join(missing)} (add them to {OVERRIDES.relative_to(ROOT)})")
    units = []
    chunks = [reading[i:i + READING_PER_UNIT] for i in range(0, len(reading), READING_PER_UNIT)]
    for i, chunk in enumerate(chunks, start=1):
        hi, lo = chunk[0]["count"], chunk[-1]["count"]
        span = f"{lo}" if hi == lo else f"{lo}–{hi}"
        units.append({"n": last + i, "title": f"Reading Vocabulary {i}", "slug": f"reading-vocabulary-{i}",
                      "description": f"Optional: New Testament words that occur {span} times.", "words": chunk})
    return {"note": "Frequency layers of courses/biblical-greek-machen (ADR-025), written by build/machen_layers.py "
                    "from MorphGNT lemma counts (CC BY-SA 3.0) and Dodson's Greek-English lexicon (public domain); "
                    "hand decisions in layers-overrides.json. core: NT lemmas occurring 50+ times that Machen's "
                    "vocabularies lack, with the unit they are taught in; reading: lemmas occurring 10-49 times, in "
                    "optional reading-vocabulary units after the last lesson.",
            "core": sorted(core, key=lambda e: (e["unit"], -e["count"])), "reading": {"units": units}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if frequency-layers.json is out of date")
    args = ap.parse_args()
    if not DODSON.exists() or not list(MORPHGNT.glob("*-morphgnt.txt")):
        sys.exit("needs python scripts/fetch-sources dodson and python scripts/fetch-sources morphgnt")
    text = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("frequency-layers.json is current" if ok else "frequency-layers.json is stale: python build/machen_layers.py")
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8")
    data = json.loads(text)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['core'])} core words, "
          f"{sum(len(u['words']) for u in data['reading']['units'])} reading words in {len(data['reading']['units'])} units")
    return 0


if __name__ == "__main__":
    sys.exit(main())
