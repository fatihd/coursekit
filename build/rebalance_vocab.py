#!/usr/bin/env python3
"""build/rebalance_vocab.py — spread a course's vocabulary evenly over its units.

Rewrites the `unit` column of content/vocab.csv and the `## Vocabulary`, `## Teaches` and
`## Assumes` lists of content/chapters/NN.md, from a layout file (--layout):

  * `pinned` ids keep their unit (alphabet units, derived-stem verbs, lesson examples);
  * from unit `first` on, every unit gets about the same number of words;
  * a word used in a unit's authored exercises (the book's, not the corpus expansion's) is taught in that unit
    or earlier;
  * `topics` words (a verb class, the numerals) are taught from their topic unit on, the topic
    unit first, the overflow at most half of each following unit;
  * words with the same Strong's number and category move together (e.g. horse/mare);
  * frequent words come early, rare words late (`frequency`; --recount refills it from the OSHB
    Strong's-number counts, one-letter prefixes from OSHB's prefix codes);
  * ids never change, so saved progress stays valid.

Usage:
    python build/rebalance_vocab.py --course courses/biblical-hebrew-davidson \
        --layout build/_sources/davidson/vocab-layout.json [--recount build/_oer/morphhb/books] [--check]

Then run build/materialize.py and scripts/validate. See docs/CONTENT-GENERATION.md.
"""

import argparse
import csv
import io
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

FINALS = str.maketrans("ךםןףץ", "כמנפצ")
PREFIXES = "והלבכמש"


def consonants(text):
    return re.sub(r"[^א-ת]", "", unicodedata.normalize("NFD", text)).translate(FINALS)


def exercise_words(course):
    words = {}
    for path in sorted((course / "authored").glob("[0-9][0-9].json")):
        unit = int(path.stem)
        data = json.loads(path.read_text(encoding="utf-8"))
        book = [it for it in data["items"] if not it.get("extra")]
        text = json.dumps(book, ensure_ascii=False)
        words[unit] = {consonants(w) for w in re.findall(r"[֐-׿]+", text)}
    return words


def defective(key):
    return key[:-2] + "ת" if key.endswith("ות") and len(key) >= 4 else key


def row_keys(row):
    base = consonants(row["scriptForm"])
    keys = {base, consonants(row.get("plural") or "")} - {""}
    keys |= {defective(k) for k in keys - {base}}
    inflected = set()
    if row["category"] == "adjective" and len(base) >= 2:
        inflected = {base + "ה", base + "ימ", base + "ות", base + "ת"} - keys
    return keys, inflected


def row_first_use(row, words):
    keys, inflected = row_keys(row)
    uses = [first_use(k, words) for k in keys] + [first_use(k, words, prefixed=False) for k in inflected]
    uses = [u for u in uses if u is not None]
    return min(uses) if uses else None


def first_use(key, words, prefixed=True):
    if not key:
        return None
    if len(key) == 1:
        return min(words) if words else None
    for unit in sorted(words):
        found = words[unit]
        if key in found or (prefixed and len(key) >= 2 and any(p + key in found for p in PREFIXES)):
            return unit
    return None


def frequency(row):
    try:
        return int(row["frequency"])
    except (TypeError, ValueError):
        return 0


PREFIX_CODES = {"ו": "c", "ב": "b", "ל": "l", "כ": "k", "מ": "m", "ה": "i"}


def oshb_counts(books):
    counts = {}
    for path in sorted(Path(books).glob("*.xml")):
        for lemma in re.findall(r'lemma="([^"]*)"', path.read_text(encoding="utf-8")):
            for part in lemma.split("/"):
                match = re.match(r"\s*(\d+)", part)
                key = int(match.group(1)) if match else part.strip()
                counts[key] = counts.get(key, 0) + 1
    return counts


def recount(rows, counts):
    changed = 0
    for row in rows:
        key = None
        letters = consonants(row["scriptForm"])
        if len(letters) == 1 and letters in PREFIX_CODES:
            key = PREFIX_CODES[letters]
        elif match := re.match(r"\d+", row.get("strong") or ""):
            key = int(match.group())
        if key in counts and row["frequency"] != str(counts[key]):
            row["frequency"] = str(counts[key])
            changed += 1
    return changed


def needed(pending, unit, fixed_count):
    need = 0
    for deadline in sorted({g["deadline"] for g in pending}):
        due = sum(len(g["rows"]) for g in pending if g["deadline"] <= deadline)
        fixed = sum(n for u, n in fixed_count.items() if unit <= u <= deadline)
        need = max(need, math.ceil((due + fixed) / (deadline - unit + 1)))
    return need


def make_groups(rows, words, layout, last):
    first = layout["first"]
    topic_of = {i: int(u) for u, ids in layout.get("topics", {}).items() for i in ids}
    groups = {}
    for row in rows:
        if row["id"] in layout["pinned"]:
            continue
        key = (row.get("strong") or row["id"], row["category"], topic_of.get(row["id"]))
        groups.setdefault(key, []).append(row)
    pending = []
    for (_, _, topic), members in sorted(groups.items(), key=lambda kv: kv[1][0]["id"]):
        uses = [u for u in (row_first_use(r, words) for r in members) if u is not None]
        release = topic or first
        if uses and min(uses) < release:
            release = first
        pending.append({"rows": members, "topic": topic, "release": release,
                        "deadline": max(min(uses), release) if uses else last,
                        "freq": max(frequency(r) for r in members)})
    return pending


def tier(group, unit, slack):
    tie = (-group["freq"], group["rows"][0]["id"])
    if group["deadline"] == unit:
        return (0, 0, *tie)
    if group["topic"] == unit:
        return (1, 0, *tie)
    if group["topic"] and group["topic"] < unit:
        return (2, group["topic"], *tie)
    if group["deadline"] - unit <= slack:
        return (3, group["deadline"], *tie)
    return (4, 0, *tie)


def plan(rows, words, layout, last):
    first, slack = layout["first"], layout.get("slack", 1)
    assigned = {i: int(u) for i, u in layout["pinned"].items()}
    fixed_count = {}
    for unit in assigned.values():
        fixed_count[unit] = fixed_count.get(unit, 0) + 1
    pending = make_groups(rows, words, layout, last)
    total = sum(len(g["rows"]) for g in pending) + sum(n for u, n in fixed_count.items() if u >= first)
    target = math.ceil(total / (last - first + 1))
    for unit in range(first, last + 1):
        later = sum(len(g["rows"]) for g in pending) + sum(n for u, n in fixed_count.items() if u >= unit)
        share = max(round(later / (last - unit + 1)), needed(pending, unit, fixed_count))
        if any(g["topic"] == unit for g in pending):
            share = max(share, target)
        room = share - fixed_count.get(unit, 0)
        topic_room = room // 2
        candidates = [g for g in pending if g["release"] <= unit]
        for group in sorted(candidates, key=lambda g: tier(g, unit, slack)):
            size, level = len(group["rows"]), tier(group, unit, slack)[0]
            if level > 0 and unit < last and size > room:
                continue
            if level == 2:
                if size > topic_room:
                    continue
                topic_room -= size
            for row in group["rows"]:
                assigned[row["id"]] = unit
            room -= size
            pending.remove(group)
    return assigned, target


def ordered(rows, assigned):
    by_unit = {}
    for row in rows:
        by_unit.setdefault(assigned[row["id"]], []).append(row)
    for unit in by_unit:
        by_unit[unit].sort(key=lambda r: (-frequency(r), r["id"]))
    return by_unit


def render_csv(header, rows, assigned, by_unit):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for unit in sorted(by_unit):
        for row in by_unit[unit]:
            writer.writerow({**row, "unit": str(assigned[row["id"]])})
    return out.getvalue()


def replace_list(text, heading, ids):
    pattern = re.compile(rf"(^## {heading}\n)(.*?)(?=^## |\Z)", re.S | re.M)
    match = pattern.search(text)
    if not match:
        return text
    tail = "" if match.end(2) == len(text) else "\n"
    body = "\n" + "".join(f"- {i}\n" for i in ids) + tail if ids else "\n"
    return text[: match.start(2)] + body + text[match.end(2):]


def render_chapter(text, unit, by_unit):
    ids = [r["id"] for r in by_unit.get(unit, [])]
    prior = [r["id"] for r in by_unit.get(unit - 1, [])]
    text = replace_list(text, "Vocabulary", ids)
    text = replace_list(text, "Teaches", ids)
    return replace_list(text, "Assumes", prior)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--course", required=True)
    ap.add_argument("--layout", required=True, help="JSON with first unit, pinned ids and topic ids")
    ap.add_argument("--recount", metavar="BOOKS", help="refill `frequency` from OSHB books (build/_oer/morphhb/books)")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    course = Path(args.course)
    csv_path = course / "content" / "vocab.csv"
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)
    if args.recount:
        print(f"frequency recounted from OSHB: {recount(rows, oshb_counts(args.recount))} row(s) changed")
    last = len(json.loads((course / "units.json").read_text(encoding="utf-8"))["units"])
    words = exercise_words(course)
    layout = json.loads(Path(args.layout).read_text(encoding="utf-8"))
    first = layout["first"]
    words = {u: w for u, w in words.items() if u >= first}
    assigned, target = plan(rows, words, layout, last)
    by_unit = ordered(rows, assigned)
    outputs = {csv_path: render_csv(header, rows, assigned, by_unit)}
    for path in sorted((course / "content" / "chapters").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        outputs[path] = render_chapter(text, int(path.stem), by_unit)
    stale = [p for p, t in outputs.items() if p.read_text(encoding="utf-8") != t]
    late = [r["id"] for r in rows if r["id"] not in layout["pinned"]
            and (u := row_first_use(r, words)) is not None and assigned[r["id"]] > u]
    counts = {u: len(by_unit.get(u, [])) for u in range(first, last + 1)}
    print(f"target {target}/unit; units {first}-{last}: min {min(counts.values())}, "
          f"max {max(counts.values())}; taught after first use: {len(late)}")
    if args.check:
        if stale:
            print("out of date: " + ", ".join(str(p) for p in stale))
            return 1
        print("vocabulary layout up to date")
        return 0
    for path in stale:
        path.write_text(outputs[path], encoding="utf-8")
    print(f"wrote {len(stale)} file(s); run build/materialize.py --course {course}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
