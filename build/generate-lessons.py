#!/usr/bin/env python3
"""build/generate-lessons.py — OER-enriched lesson generation pass (P6-T2).

Reads the canonical text (content/vocab.csv + content/chapters/NN.md) and the
local OER cache (build/_oer/), and rewrites the canonical text with enrichment:

  * vocab.csv — adds OER columns: `root`, `strong`, `pos`, `oer_source`,
    `oer_license` (attribution per row, per ADR-004 + CONTENT-GENERATION §4).
  * chapters/NN.md — adds, per unit: a "Word Roots" table block (scriptForm,
    transliteration, gloss, root, strong) from the OSHB/lexicon join; a
    `## Teaches` list (the unit's vocab items); `## Assumes` (prior unit's
    items, spiral recap); and a machine-generated `## Did You Know` fact from
    OSHB token counts (attributed).

The text stays the source of truth: run build/materialize.py afterwards to
regenerate the engine JSON, then scripts/validate.

Usage:
    python build/generate-lessons.py --course courses/biblical-hebrew-davidson

See docs/CONTENT-GENERATION.md §3, docs/CONTENT-PORTABILITY.md, docs/STATUS.md.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

OEROOT = Path(__file__).resolve().parent / "_oer"

NIOQ = {chr(cp) for cp in range(0x0591, 0x05C8)}

VOCAB_COLUMNS = [
    "id", "unit", "category", "scriptForm", "plural", "transliteration",
    "pronunciation", "gloss", "gender", "number", "frequency",
    "root", "strong", "pos", "binyan", "oer_source", "oer_license",
]

SOURCE_OSHB = "OSHB/MorphHB"
LICENSE_OSHB = "CC BY 4.0"
SOURCE_WIKT = "Wiktionary"
LICENSE_WIKT = "CC BY-SA 3.0 / GFDL"

HE_ROOTBOX_RE = re.compile(r"\{\{he-rootbox\|([^}|]+)")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def strip_niqqud(s):
    return "".join(ch for ch in s if ch not in NIOQ)


def load_oshb_lexicon():
    """Index OSHB/MorphHB lexicon by stripped *base* form (prefix-free)."""
    path = OEROOT / "morphhb" / "lexicon.json"
    if not path.exists():
        print("  [warn] no OER lexicon; re-run build/fetch_oer.py")
        return {}
    rows = load_json(path).get("rows", {})
    index = {}

    def add(surface, entry):
        prefixed = "/" in surface
        base = strip_niqqud(surface.split("/")[-1])
        idx = index.setdefault(base, {"strong": "", "pos": "", "count": 0})
        if idx["strong"] and idx["pos"]:
            pass
        elif not prefixed:
            idx["strong"] = idx["strong"] or (entry.get("strong") or "")
            idx["pos"] = idx["pos"] or (entry.get("pos") or "")
        else:
            strong = entry.get("strong") or ""
            idx["strong"] = idx["strong"] or (strong.split("/")[-1] if "/" in strong else strong)
            idx["pos"] = idx["pos"] or (entry.get("pos") or "")
        idx["count"] += entry.get("count", 0)

    for surface, entry in rows.items():
        if "/" not in surface:
            add(surface, entry)
    for surface, entry in rows.items():
        if "/" in surface:
            add(surface, entry)
    return index


def load_wiktionary_for(form):
    path = OEROOT / "wiktionary" / f"{strip_niqqud(form)}.json"
    if not path.exists():
        return None
    return load_json(path)


def oer_fields(script_form):
    """Return (root, strong, pos, source, license) for a vocab item."""
    plain = strip_niqqud(script_form)
    lex = lexicon.get(plain)
    wiki = load_wiktionary_for(script_form)

    root = ""
    strong = ""
    pos = ""
    if lex:
        strong = lex.get("strong") or ""
        pos = lex.get("pos") or ""

    if wiki:
        wt = wiki.get("wikitext") or ""
        m = HE_ROOTBOX_RE.search(wt)
        if m:
            root = m.group(1).replace("־", "").replace("-", "")

    sources = []
    licences = []
    if lex is not None:
        sources.append(SOURCE_OSHB)
        licences.append(LICENSE_OSHB)
    if wiki is not None:
        sources.append(SOURCE_WIKT)
        licences.append(LICENSE_WIKT)
    source = "; ".join(sources)
    license = "; ".join(licences)
    return root, strong, pos, source, license


def enrich_vocab(course_dir):
    csv_path = course_dir / "content" / "vocab.csv"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))
    rows.sort(key=lambda r: (int(r["unit"]), r["id"]))

    counts = {"root": 0, "strong": 0, "pos": 0}
    for row in rows:
        root, strong, pos, source, license = oer_fields(row["scriptForm"])
        row["root"], row["strong"], row["pos"] = root, strong, pos
        row["oer_source"], row["oer_license"] = source, license
        for key in counts:
            if row[key]:
                counts[key] += 1

    out = course_dir / "content" / "vocab.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=VOCAB_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in VOCAB_COLUMNS})
    return rows


def build_word_roots_table(unit_items, vocab_by_id):
    columns = ["Hebrew", "Transliteration", "Gloss", "Root", "Strong"]
    rows = []
    for it in unit_items:
        data = vocab_by_id[it]
        if data.get("root") or data.get("strong"):
            rows.append([
                data["scriptForm"],
                data.get("transliteration", ""),
                data.get("gloss", ""),
                data.get("root", ""),
                data.get("strong", ""),
            ])
    if not rows:
        return None
    return {"type": "table", "caption": "Word roots (OER)", "columns": columns, "rows": rows}


def did_you_know(unit_items, vocab_by_id, lexicon):
    best = None
    for it in unit_items:
        data = vocab_by_id[it]
        entry = lexicon.get(strip_niqqud(data["scriptForm"]))
        if not entry or not entry.get("count"):
            continue
        cnt = entry["count"]
        if best is None or cnt > best[1]:
            best = (it, cnt)
    if not best:
        return ""
    data = vocab_by_id[best[0]]
    return (f"According to {SOURCE_OSHB} ({LICENSE_OSHB}), the most frequent word in this "
            f"unit is {data['scriptForm']} ({data.get('transliteration', '')}), occurring "
            f"{best[1]} times in the Westminster Leningrad Codex.")


def build_chapter_text(unit, title, description, summary_text, custom_sections,
                       vocab_block, table_block, teaches, assumes, did_you_know):
    lines = [f"# Unit {unit} — {title}", "", description, ""]
    if summary_text:
        lines += ["## Summary", "", summary_text.strip(), ""]
    for heading, body in custom_sections:
        lines += [f"## {heading}", "", body.strip(), ""]
    if table_block:
        header = "| " + " | ".join(table_block["columns"]) + " |"
        sep = "| " + " | ".join("---" for _ in table_block["columns"]) + " |"
        lines += ["## " + table_block["caption"], "", header, sep]
        for row in table_block["rows"]:
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    if vocab_block:
        lines += ["## Vocabulary", ""]
        lines += [f"- {r}" for r in vocab_block["refs"]]
        lines.append("")
    if teaches:
        lines += ["## Teaches", ""]
        lines += [f"- {t}" for t in teaches]
        lines.append("")
    if assumes:
        lines += ["## Assumes", ""]
        lines += [f"- {a}" for a in assumes]
        lines.append("")
    if did_you_know:
        lines += ["## Did You Know", "", did_you_know, ""]
    return "\n".join(lines).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    args = ap.parse_args()

    course_dir = Path(args.course)
    content_dir = course_dir / "content"
    if not (content_dir / "vocab.csv").exists():
        sys.exit(f"content/vocab.csv missing in {course_dir}; run build/textify.py first")
    if not (content_dir / "chapters").exists():
        sys.exit(f"content/chapters missing in {course_dir}; run build/textify.py first")

    global lexicon
    lexicon = load_oshb_lexicon()

    count = {}
    rows = enrich_vocab(course_dir)
    for r in rows:
        for key, val in (("root", r["root"]), ("strong", r["strong"]), ("pos", r["pos"])):
            count[key] = count.get(key, 0) + (1 if val else 0)
    print(f"vocab enrichment: root {count.get('root', 0)}, strong {count.get('strong', 0)}, "
          f"pos {count.get('pos', 0)}")

    vocab_by_id = {r["id"]: r for r in rows}
    unit_vocab = {}
    for r in rows:
        unit_vocab.setdefault(int(r["unit"]), []).append(r["id"])

    units = load_json(course_dir / "units.json")["units"]
    for u in sorted(units, key=lambda u: u["n"]):
        n = u["n"]
        chapter = content_dir / "chapters" / f"{n:02d}.md"
        text = chapter.read_text(encoding="utf-8") if chapter.exists() else ""
        lines = text.splitlines()
        desc = ""
        if lines and lines[0].startswith("# Unit"):
            i = 1
            desc_lines = []
            while i < len(lines) and not lines[i].startswith("## "):
                desc_lines.append(lines[i])
                i += 1
            desc = "\n".join(desc_lines).strip()

        unit_items = unit_vocab.get(n, [])
        table_block = build_word_roots_table(unit_items, vocab_by_id)
        teaches = list(unit_items)
        assumes = list(unit_vocab.get(n - 1, [])) if n > 1 else []
        fact = did_you_know(unit_items, vocab_by_id, lexicon)

        sections = parse_sections(lines)
        summary_text = sections.pop("Summary", "")
        custom_sections = [
            (heading, body)
            for heading, body in sections.items()
            if heading not in {"Word roots (OER)", "Vocabulary", "Teaches", "Assumes", "Did You Know"}
        ]
        out_text = build_chapter_text(
            n, u["title"], desc or u["description"], summary_text, custom_sections,
            {"type": "vocab", "refs": unit_items}, table_block,
            teaches, assumes, fact,
        )
        chapter.write_text(out_text, encoding="utf-8")

    print(f"wrote enriched chapters for {len(units)} units to {content_dir}/chapters")
    print("run build/materialize.py then scripts/validate")


def parse_sections(lines):
    sections = {}
    i = 0
    while i < len(lines):
        if not lines[i].startswith("## "):
            i += 1
            continue
        heading = lines[i][3:].strip()
        i += 1
        body = []
        while i < len(lines) and not lines[i].startswith("## "):
            body.append(lines[i])
            i += 1
        sections[heading] = "\n".join(body).strip()
    return sections


lexicon = {}

if __name__ == "__main__":
    sys.exit(main())
