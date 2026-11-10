#!/usr/bin/env python3
"""build/textify.py — emit canonical plaintext from the engine JSON (P5-T2).

Writes courses/<course>/content/ (vocab.csv + chapters/NN.md) from the current
vocab.json + units/NN.json. The text is the source of truth; JSON is a derived
artifact (see docs/CONTENT-PORTABILITY.md, ADR-009).

Usage:
    python build/textify.py --course courses/biblical-hebrew-davidson
"""

import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path

VOCAB_COLUMNS = [
    "id", "unit", "category", "scriptForm", "plural", "transliteration",
    "pronunciation", "gloss", "gender", "number", "frequency",
    "root", "strong", "pos", "binyan", "parse", "forms", "oer_source", "oer_license",
]


def write_vocab(course_dir, content_dir):
    items = json.loads((course_dir / "vocab.json").read_text(encoding="utf-8"))["items"]
    out = content_dir / "vocab.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=VOCAB_COLUMNS)
        w.writeheader()
        for it in items:
            extra = it.get("extra") or {}
            row = {c: it.get(c) for c in VOCAB_COLUMNS}
            row["root"] = it.get("root")
            row["strong"] = extra.get("strong", "")
            row["pos"] = extra.get("pos", "")
            row["binyan"] = extra.get("binyan", "")
            row["parse"] = extra.get("parse", "")
            row["forms"] = json.dumps(extra.get("forms", []), ensure_ascii=False) if extra.get("forms") else ""
            row["oer_source"] = extra.get("source", "")
            row["oer_license"] = extra.get("license", "")
            for k, v in row.items():
                if v is None:
                    row[k] = ""
            w.writerow(row)


def strip_p(html_text):
    text = re.sub(r"</?p>", "", html_text)
    return html.unescape(text).strip()


def table_to_md(section, block):
    lines = [f"## {section}", ""]
    header = "| " + " | ".join(block["columns"]) + " |"
    sep = "| " + " | ".join("---" for _ in block["columns"]) + " |"
    lines.append(header)
    lines.append(sep)
    for row in block.get("rows", []):
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return lines


def write_chapter(course_dir, content_dir, n):
    lesson = json.loads((course_dir / f"units/{n:02d}.json").read_text(encoding="utf-8"))
    lines = [f"# Unit {n} — {lesson['title']}", "", lesson["description"], ""]
    for block in lesson.get("blocks", []):
        if block["type"] == "prose":
            lines += [f"## {block.get('caption') or 'Summary'}", "", strip_p(block["html"]), ""]
        elif block["type"] == "vocab":
            lines += ["## Vocabulary", ""]
            lines += [f"- {r}" for r in block.get("refs", [])]
            lines.append("")
        elif block["type"] in ("table", "paradigm"):
            lines += table_to_md(block.get("caption") or block["type"], block)
    if lesson.get("teaches"):
        lines += ["## Teaches", ""]
        lines += [f"- {t}" for t in lesson["teaches"]]
        lines.append("")
    if lesson.get("assumes"):
        lines += ["## Assumes", ""]
        lines += [f"- {a}" for a in lesson["assumes"]]
        lines.append("")
    if lesson.get("didYouKnow"):
        lines += ["## Did You Know", "", lesson["didYouKnow"], ""]
    out = content_dir / "chapters" / f"{n:02d}.md"
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    args = ap.parse_args()

    course_dir = Path(args.course)
    if not (course_dir / "vocab.json").exists():
        sys.exit(f"vocab.json missing in {course_dir}")

    content_dir = course_dir / "content"
    (content_dir / "chapters").mkdir(parents=True, exist_ok=True)

    write_vocab(course_dir, content_dir)

    units = json.loads((course_dir / "units.json").read_text(encoding="utf-8"))["units"]
    for u in units:
        write_chapter(course_dir, content_dir, u["n"])

    n_chapters = len(list((content_dir / "chapters").glob("*.md")))
    print(f"textified {course_dir.name}: vocab.csv + {n_chapters} chapters -> {content_dir}")


if __name__ == "__main__":
    main()
