#!/usr/bin/env python3
"""build/materialize.py — load canonical plaintext into the engine JSON (P5-T3).

Reads courses/<course>/content/ (vocab.csv + chapters/NN.md) and regenerates
vocab.json + units/NN.json. The text is the source of truth; the JSON is a derived
build artifact (see docs/CONTENT-PORTABILITY.md, ADR-009).

Usage:
    python build/materialize.py --course courses/biblical-hebrew-davidson
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

HEADING_RE = re.compile(r"^# Unit (\d+) — (.+)$")
SECTION_RE = re.compile(r"^## (.+)$")
GFM_SEP_RE = re.compile(r":?-{2,}:?")


def read_vocab(content_dir):
    with (content_dir / "vocab.csv").open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        items = []
        for row in reader:
            item = {}
            for c in VOCAB_COLUMNS:
                item[c] = (row.get(c) or "").strip()
            item["unit"] = int(item["unit"])
            item["frequency"] = int(item["frequency"]) if item["frequency"] else None
            item["gender"] = item["gender"] or None
            item["number"] = item["number"] or None
            item["root"] = item["root"] or None
            extra = {}
            for k, v in (("strong", item.pop("strong")), ("pos", item.pop("pos")),
                         ("binyan", item.pop("binyan")), ("parse", item.pop("parse"))):
                if v:
                    extra[k] = v
            forms = item.pop("forms")
            if forms:
                try:
                    extra["forms"] = json.loads(forms)
                except json.JSONDecodeError:
                    extra["forms"] = []
            src, lic = item.pop("oer_source"), item.pop("oer_license")
            if src:
                extra["source"] = src
            if lic:
                extra["license"] = lic
            if extra:
                item["extra"] = extra
            items.append(item)
    return items


def paragraphs_to_html(text):
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    escaped = [html.escape(p) for p in paras]
    return "".join(f"<p>{p}</p>" for p in escaped)


def parse_gfm_table(body):
    rows = [ln for ln in body if ln.strip()]
    if len(rows) < 2:
        return None, None
    split = [ln.strip().strip("|").split("|") for ln in rows]
    cells = [[c.strip() for c in row] for row in split]
    sep = cells[1]
    if not all(GFM_SEP_RE.fullmatch(s) for s in sep):
        return None, None
    return cells[0], cells[2:]


def read_chapter(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    m = HEADING_RE.match(lines[0].strip())
    if not m:
        raise ValueError(f"bad chapter heading in {path}: {lines[0]!r}")
    n = int(m.group(1))
    title = m.group(2).strip()

    description_lines = []
    i = 1
    while i < len(lines):
        if lines[i].startswith("## "):
            break
        description_lines.append(lines[i])
        i += 1
    description = "\n".join(description_lines).strip()

    blocks = []
    teaches = []
    assumes = []
    did_you_know = ""
    while i < len(lines):
        if lines[i].startswith("## "):
            section = lines[i][3:].strip()
            i += 1
            body = []
            while i < len(lines) and not lines[i].startswith("## "):
                body.append(lines[i])
                i += 1
            if section == "Summary":
                blocks.append({
                    "type": "prose",
                    "caption": section,
                    "html": paragraphs_to_html("\n".join(body)),
                })
            elif section == "Vocabulary":
                refs = [ln.strip().lstrip("- ").strip() for ln in body if ln.strip().startswith("-")]
                blocks.append({"type": "vocab", "refs": refs})
            elif section == "Teaches":
                teaches = [ln.strip().lstrip("- ").strip() for ln in body if ln.strip().startswith("-")]
            elif section == "Assumes":
                assumes = [ln.strip().lstrip("- ").strip() for ln in body if ln.strip().startswith("-")]
            elif section == "Did You Know":
                text = "\n".join(ln.strip() for ln in body if ln.strip()).strip()
                if text:
                    did_you_know = text
            else:
                caption = section
                columns, rows = parse_gfm_table(body)
                if columns is not None:
                    blocks.append({"type": "table", "caption": caption, "columns": columns, "rows": rows})
                else:
                    blocks.append({
                        "type": "prose",
                        "caption": caption,
                        "html": paragraphs_to_html("\n".join(body)),
                    })
        else:
            i += 1

    return {
        "schema": "unit-lesson-v1.json",
        "unit": n,
        "title": title,
        "description": description,
        "teaches": teaches,
        "assumes": assumes,
        "blocks": blocks,
        "didYouKnow": did_you_know,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    args = ap.parse_args()

    course_dir = Path(args.course)
    content_dir = course_dir / "content"
    if not (content_dir / "vocab.csv").exists():
        sys.exit(f"content/vocab.csv missing in {course_dir}; run build/textify.py first")

    items = read_vocab(content_dir)
    vocab_out = {"schema": "vocab-v1.json", "source": "content/vocab.csv", "items": items}
    (course_dir / "vocab.json").write_text(
        json.dumps(vocab_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )

    units = json.loads((course_dir / "units.json").read_text(encoding="utf-8"))["units"]
    for u in units:
        path = content_dir / "chapters" / f"{u['n']:02d}.md"
        if not path.exists():
            sys.exit(f"missing chapter {path}")
        lesson = read_chapter(path)
        (course_dir / f"units/{u['n']:02d}.json").write_text(
            json.dumps(lesson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )

    print(f"materialized {course_dir.name}: {len(items)} vocab items + {len(units)} lessons from {content_dir}")


if __name__ == "__main__":
    main()
