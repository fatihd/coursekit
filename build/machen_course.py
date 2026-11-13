#!/usr/bin/env python3
"""Build the Machen Greek course data (ROADMAP P11-T5, ADR-025).

Reads `build/_sources/machen/course-map.json` (units and Machen's lesson vocabularies), `recognition.json`
(questions for the letter and accent units) and the curated exercises `exwb/curated/machen-lNN.json` (Machen's
sentences with the answers written for this course), and writes into `courses/biblical-greek-machen`:

* `content/vocab.csv` — the lesson vocabularies, with NT frequencies from MorphGNT (`build/_sources/morphgnt/`,
  or the counts kept in `build/_sources/machen/lemma-counts.json` when MorphGNT is not downloaded);
* `authored/NN.json`, `exercises/NN.json`, `authored/ladder.json` — five ladder rungs per sentence made by the Greek
  profile of the ladder (`build/ladder_greek.py` on `build/ladder_core.py`), recognition questions for units 1-2.

Then run `python build/materialize.py --course courses/biblical-greek-machen` and
`python scripts/validate courses/biblical-greek-machen --snapshot`.

    python build/machen_course.py --course courses/biblical-greek-machen [--check]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import greek_text as G
from ladder_core import RUNG_KEYS, clean_display, english_variants, rung_names
from ladder_greek import GreekProfile
from ladder_greek import ladder as greek_ladder

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "build" / "_sources" / "machen"
MAP = SRC / "course-map.json"
RECOGNITION = SRC / "recognition.json"
COUNTS = SRC / "lemma-counts.json"
MORPHGNT = ROOT / "build" / "_sources" / "morphgnt"
CURATED = ROOT / "exwb" / "curated"
BOOK_ID = "newtestamentgree00mach_0"
PAGE_TO_LEAF = 17
VOCAB_COLUMNS = ["id", "unit", "category", "scriptForm", "plural", "transliteration", "pronunciation", "gloss", "gender",
                 "number", "frequency", "root", "strong", "pos", "binyan", "parse", "forms", "oer_source", "oer_license"]
CITATION = "Machen, New Testament Greek for Beginners (1923)"


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def page_links(page: int) -> dict:
    n = page + PAGE_TO_LEAF
    return {"promptUrl": f"https://archive.org/details/{BOOK_ID}/page/n{n}/mode/1up",
            "promptImageUrl": f"https://archive.org/download/{BOOK_ID}/page/n{n}.jpg"}


def lemma_counts(lemmas: list[str]) -> dict[str, int]:
    files = sorted(MORPHGNT.glob("*-morphgnt.txt"))
    if files:
        counts: Counter = Counter()
        for f in files:
            for line in f.read_text(encoding="utf-8").splitlines():
                counts[unicodedata.normalize("NFC", line.split(" ")[6])] += 1
        by_bare = defaultdict(list)
        for lem in counts:
            by_bare[G.bare(lem)].append(lem)
        out = {}
        for lem in lemmas:
            hit = lem if lem in counts else max(by_bare.get(G.bare(lem), [""]), key=lambda x: counts.get(x, 0))
            out[lem] = counts.get(hit, 0)
        COUNTS.write_text(dump({"note": "NT occurrences of the course lemmas (MorphGNT SBLGNT edition, CC BY-SA 3.0); "
                                        "written by build/machen_course.py so the course builds without MorphGNT.",
                                "counts": out}), encoding="utf-8")
        return out
    return json.loads(COUNTS.read_text(encoding="utf-8"))["counts"]


def vocab_rows(cmap: dict) -> list[dict]:
    words = [(u["n"], w) for u in cmap["units"] for w in u["vocab"]]
    counts = lemma_counts([w[0] for _, w in words])
    rows, seq = [], Counter()
    for unit, w in words:
        seq[unit] += 1
        word, gloss, category = w[0], w[1], w[2]
        rows.append({
            "id": f"gr-mac-{unit:02d}-{seq[unit]:03d}", "unit": str(unit), "category": category, "scriptForm": word,
            "plural": "", "transliteration": "", "pronunciation": "", "gloss": gloss,
            "gender": w[3] if len(w) > 3 else "", "number": "", "frequency": str(counts.get(word, 0)),
            "root": "", "strong": "", "pos": category, "binyan": "", "parse": "", "forms": "",
            "oer_source": "Machen (1923); MorphGNT", "oer_license": "public domain; CC BY-SA 3.0",
        })
    return rows


def vocab_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=VOCAB_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def accepted_english(it: dict) -> list[str]:
    out = []
    for text in [it["answer"]] + (it.get("data") or {}).get("accept", []):
        for v in english_variants(text):
            if v not in out:
                out.append(v)
    return out


def sentence_items(unit: int, stem: str, data: dict) -> list[dict]:
    items = data["items"]
    lesson, section = data["lesson"], data["section"]
    pool = defaultdict(list)
    for it in items:
        pool[it["part"]].append(clean_display(it["answer"] if it["part"] == "I" else it["prompt"]))
    out = []
    for it in items:
        base = f"m{lesson:02d}-{it['part']}{it['num']}"
        page = data["pages"][0] if it["part"] == "I" or len(data["pages"]) == 1 else data["pages"][-1]
        source = {"citation": f"{CITATION}, Lesson {lesson}, §{section}, exercise {it['part']}.{it['num']}; "
                              "answer written for this course", **page_links(page), "exwb": f"{stem}#{it['part']}{it['num']}"}
        common = {"block": f"m{lesson:02d}", "blockLabel": f"Machen §{section}",
                  "shape": "gr-en" if it["part"] == "I" else "en-gr", "src": base}
        rng = random.Random(base)
        english_pool = pool[it["part"]] + [e for p, es in pool.items() if p != it["part"] for e in es]
        if it["part"] == "I":
            made = greek_ladder(base, [it["prompt"]], clean_display(it["answer"]), english_pool, "gr-en", rng, common)
            for m in made:
                if m["rung"] == 4:
                    m["accepted"] = accepted_english(it)
        else:
            greek = [it["answer"]] + [a for a in (it.get("data") or {}).get("accept", []) if G.greek_words(a)]
            made = greek_ladder(base, greek, clean_display(it["prompt"]), english_pool, "en-gr", rng, common)
        out.append({"base": base, "source": source, "items": made,
                    "raw": {"typeGuess": made[0]["type"], "confidence": 1.0, "prompt": made[0]["prompt"],
                            "body_raw": it["prompt"], "answer_raw": it["answer"]}})
    return out


def recognition_items(unit: int, spec: dict) -> list[dict]:
    names = rung_names(GreekProfile())
    out = []
    for n, q in enumerate(spec["questions"], start=1):
        base = f"r{unit:02d}-{n}"
        rng = random.Random(base)
        common = {"block": f"r{unit:02d}", "blockLabel": "Recognition", "shape": "recognition", "src": base}

        def rung(r: int, body: dict, base: str = base, common: dict = common) -> dict:
            return {"id": f"{base}.{RUNG_KEYS[r]}", "rung": r, "rungLabel": names[r], **body, **common}

        truth = rng.random() < 0.5
        options = [q["answer"]] + q["wrong"]
        rng.shuffle(options)
        items = [
            rung(1, {"type": "true-false", "prompt": "True or false?", "stimulus": q["stimulus"], "stimulusIsScript": True,
                     "statement": q["claim"].format(x=q["answer"] if truth else q["wrong"][0]), "answer": truth,
                     "expected": q["claim"].format(x=q["answer"])}),
            rung(2, {"type": "mcq", "prompt": q["prompt"], "stimulus": q["stimulus"], "stimulusIsScript": True,
                     "options": options, "answer": q["answer"], "optionIsScript": False}),
            rung(3, {"type": "translate-phrase", "prompt": q["typed"]["prompt"], "stimulus": q["stimulus"],
                     "stimulusIsScript": True, "accepted": q["typed"]["accepted"], "answerIsScript": True}),
        ]
        source = {"citation": f"Written for this course on {CITATION}, Lesson {spec['lesson']}", **page_links(spec["page"])}
        out.append({"base": base, "source": source, "items": items,
                    "raw": {"typeGuess": "mcq", "confidence": 1.0, "prompt": q["prompt"], "body_raw": q["stimulus"],
                            "answer_raw": q["answer"]}})
    return out


def build(cmap: dict) -> dict[int, list[dict]]:
    units: dict[int, list[dict]] = defaultdict(list)
    rec = json.loads(RECOGNITION.read_text(encoding="utf-8"))["units"]
    for key, spec in rec.items():
        units[int(key)] += recognition_items(int(key), spec)
    for u in cmap["units"]:
        stem = u.get("exercise")
        if stem:
            data = json.loads((CURATED / f"{stem}.json").read_text(encoding="utf-8"))
            units[u["n"]] += sentence_items(u["n"], stem, data)
    return units


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--course", required=True)
    ap.add_argument("--check", action="store_true", help="fail if the course files are out of date")
    args = ap.parse_args()
    course = Path(args.course)
    cmap = json.loads(MAP.read_text(encoding="utf-8"))
    wanted: dict[Path, str] = {course / "content" / "vocab.csv": vocab_csv(vocab_rows(cmap))}
    ladder_index = {}
    for unit, entries in sorted(build(cmap).items()):
        items = [it for e in entries for it in e["items"]]
        sources = {e["base"]: e["source"] for e in entries}
        raw = [{"unit": unit, "n": i, **e["raw"]} for i, e in enumerate(entries, start=1)]
        wanted[course / "authored" / f"{unit:02d}.json"] = dump(
            {"schema": "authored-exercises-v1.json", "unit": unit, "sources": sources, "items": items})
        wanted[course / "exercises" / f"{unit:02d}.json"] = dump(
            {"schema": "workbook-exercises-v1.json", "unit": unit, "items": raw})
        ladder_index[str(unit)] = dict(sorted(Counter(str(it["rung"]) for it in items).items()))
    wanted[course / "authored" / "ladder.json"] = dump(
        {"note": "Items per ladder rung per unit (rung 1 true/false … 5 translate with accents); written by "
                 "build/machen_course.py.", "units": ladder_index, "extra": {}})
    existing = {p for d in ("authored", "exercises") for p in (course / d).glob("[0-9][0-9].json")}
    stale = sorted(existing - set(wanted))
    changed = sorted(p for p, text in wanted.items() if not p.is_file() or p.read_text(encoding="utf-8") != text)
    total = sum(n for u in ladder_index.values() for n in u.values())
    summary = f"{total} ladder items in {len(ladder_index)} units; rungs per unit: {ladder_index}"
    if args.check:
        for p in changed + stale:
            print(f"out of date: {p.relative_to(course)}")
        if changed or stale:
            return 1
        print(f"up to date: {summary}")
        return 0
    for p in stale:
        p.unlink()
    for p in changed:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(wanted[p], encoding="utf-8")
    print(f"wrote {len(changed)} file(s), removed {len(stale)}: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
