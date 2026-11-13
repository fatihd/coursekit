#!/usr/bin/env python3
"""Attestation check for the Greek course's sentences and answers (ROADMAP P11-T4, ADR-025).

Machen has no key, so the Greek answers are ours. Every Greek word in the curated Machen items
(`exwb/curated/machen-*.json`: the book's Greek prompts and our Greek answers, with any accepted alternatives)
must be attested — the same form, compared with `build/greek_text.py` at the `full` level, in

* the SBLGNT text as analysed by MorphGNT (`build/_sources/morphgnt/`, fetched with `scripts/fetch-sources morphgnt`),
* Machen's own Greek: the printed exercise sentences, or `build/_sources/machen/attested.json` (paradigm and
  vocabulary forms, each with its page), or
* the course word list (`courses/biblical-greek-machen/content/vocab.csv`, when it exists).

`forms` also writes `build/_sources/machen/greek-forms.json`: each form's MorphGNT analyses (lemma, parse code,
count), so the course can be built and checked without the MorphGNT download. That file is derived from MorphGNT
(CC BY-SA 3.0) and keeps its attribution.

    python build/greek_corpus.py check            # report; exit 1 if a Greek word is not attested
    python build/greek_corpus.py forms [--check]  # (re)write greek-forms.json, or verify it is current
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import greek_text as G

ROOT = Path(__file__).resolve().parent.parent
CURATED = ROOT / "exwb" / "curated"
MORPHGNT = ROOT / "build" / "_sources" / "morphgnt"
SRC = ROOT / "build" / "_sources" / "machen"
ATTESTED = SRC / "attested.json"
FORMS = SRC / "greek-forms.json"
VOCAB = ROOT / "courses" / "biblical-greek-machen" / "content" / "vocab.csv"
BOOKS = {"61": "Matt", "62": "Mark", "63": "Luke", "64": "John", "65": "Acts", "66": "Rom", "67": "1Cor", "68": "2Cor",
         "69": "Gal", "70": "Eph", "71": "Phil", "72": "Col", "73": "1Thess", "74": "2Thess", "75": "1Tim", "76": "2Tim",
         "77": "Titus", "78": "Phlm", "79": "Heb", "80": "Jas", "81": "1Pet", "82": "2Pet", "83": "1John", "84": "2John",
         "85": "3John", "86": "Jude", "87": "Rev"}


def curated_files() -> list[Path]:
    return sorted(CURATED.glob("machen-*.json"))


def greek_side(item: dict) -> tuple[str, list[str], str]:
    """(role, texts, origin): the Greek texts of an item and whether they are the book's or ours."""
    if item["part"] == "I":
        return "prompt", [item["prompt"]], "book"
    texts = [item.get("answer", "")] + [a for a in (item.get("data") or {}).get("accept", []) if G.greek_words(a)]
    return "answer", texts, "ours"


def morphgnt() -> dict[str, Counter]:
    files = sorted(MORPHGNT.glob("*-morphgnt.txt"))
    if not files:
        sys.exit("MorphGNT files missing: python scripts/fetch-sources morphgnt")
    out: dict[str, Counter] = defaultdict(Counter)
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            ref, pos, parse, _text, word, norm, lemma = line.split(" ")
            for w in {word, norm}:
                out[G.key(w)][(lemma, pos.strip("-") + ":" + parse)] += 1
    return out


def book_forms() -> set[str]:
    keys = set()
    for path in curated_files():
        for it in json.loads(path.read_text(encoding="utf-8"))["items"]:
            if it["part"] == "I":
                keys |= {G.key(w) for w in G.greek_words(it["prompt"])}
    if ATTESTED.exists():
        keys |= {G.key(e["form"]) for e in json.loads(ATTESTED.read_text(encoding="utf-8"))["forms"]}
    return keys


def vocab_forms() -> set[str]:
    if not VOCAB.exists():
        return set()
    with VOCAB.open(encoding="utf-8") as f:
        return {G.key(w) for row in csv.DictReader(f) for w in G.greek_words(row.get("scriptForm", ""))}


def used_words() -> list[tuple[str, str, str, str]]:
    out = []
    for path in curated_files():
        for it in json.loads(path.read_text(encoding="utf-8"))["items"]:
            _role, texts, origin = greek_side(it)
            for t in texts:
                for w in G.greek_words(t):
                    out.append((w, origin, path.name, f"{it['part']}.{it['num']}"))
    return out


def check(nt: dict | None = None) -> int:
    nt_keys = set(nt) if nt is not None else set(json.loads(FORMS.read_text(encoding="utf-8"))["forms"])
    book, vocab = book_forms(), vocab_forms()
    words = used_words()
    where = Counter()
    missing = []
    for w, origin, fname, ref in words:
        k = G.key(w)
        if k in nt_keys:
            where["SBLGNT/MorphGNT"] += 1
        elif k in book:
            where["Machen's text"] += 1
        elif k in vocab:
            where["course word list"] += 1
        else:
            missing.append((w, origin, fname, ref))
    print(f"{len(words)} Greek words in {len(curated_files())} curated Machen files; attested by: {dict(where)}")
    for w, origin, fname, ref in missing:
        print(f"  NOT ATTESTED: {w} ({origin}, {fname} {ref})")
    return 1 if missing else 0


def forms_json(nt: dict[str, Counter]) -> dict:
    used = sorted({G.key(w) for w, *_ in used_words()})
    out = {}
    for k in used:
        if k in nt:
            out[k] = [{"lemma": lem, "parse": parse, "count": c} for (lem, parse), c in nt[k].most_common()]
    return {"source": "MorphGNT SBLGNT edition (CC BY-SA 3.0; text CC BY 4.0, SBL), commit aaed91e5; "
                      "analyses of the Greek forms used in exwb/curated/machen-*.json",
            "forms": out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "forms"])
    ap.add_argument("--check", action="store_true", help="forms: verify greek-forms.json is current")
    args = ap.parse_args()
    if args.cmd == "check":
        return check(morphgnt() if list(MORPHGNT.glob("*-morphgnt.txt")) else None)
    data = forms_json(morphgnt())
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        ok = FORMS.exists() and FORMS.read_text(encoding="utf-8") == text
        print("greek-forms.json is current" if ok else "greek-forms.json is stale: python build/greek_corpus.py forms")
        return 0 if ok else 1
    FORMS.write_text(text, encoding="utf-8")
    print(f"wrote {FORMS.relative_to(ROOT)}: {len(data['forms'])} forms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
