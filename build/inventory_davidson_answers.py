"""Inventory the 1924 McFadyen key's answer lists, mirroring the grammar inventory.

For every § and part letter the key answers, extract the numbered items:

* part A answers (English) from Apple Vision OCR of the key PDF, keyed by the
  printed "N." markers;
* part B/C/D answers (pointed Hebrew) from the key's DjVu word boxes, keyed by
  the printed RTL item numbers (the same coordinate-aware segmentation the
  exercise recovery uses).

No caps, no matching against the grammar: this records everything the OCR can
see in the key, each item with its own scan leaf.

    python build/inventory_davidson_answers.py
    python build/inventory_davidson_answers.py --write
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))

import recover_davidson_exercises as recover  # noqa: E402

SOURCES = ROOT / "build" / "_sources" / "davidson"
KEY_ITEM = "keytoexercisesin0000mcfa"

HEB_CONSONANT_RE = re.compile(r"[\u05d0-\u05ea]")
LAT_RE = re.compile(r"[A-Za-z]")
INVISIBLE_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff\u00ad]")
SECTION_ANY_RE = re.compile(r"[§8S$₪]\s*([0-9IlOo1Tt][0-9IlOo1Tt ]{0,3})")
BARE_SECTION_RE = re.compile(
    r"^\s*[§8S$₪]+\s*([0-9IlOo1TtбБ][0-9IlOo1TtбБ ]{0,2})\s*[.,]?\s*$"
)
BARE_PART_RE = re.compile(r"^\s*([A-D])\s*[.,]?\s*$")
NUMBERED_ENGLISH_RE = re.compile(r"(?<![\w§$])(\d{1,2})\.\s+(?=[A-Z(\"\u201c])")
FOOTNOTE_RE = re.compile(r"^\s*\d{1,2}\s+[A-Za-z]")
ENGLISH_LINE_RE = re.compile(r"[A-Za-z]{2,}")
INSTRUCTION_LINE_RE = re.compile(
    r"^\s*(?:Write|Translate|Note\b|Read\b|See\s|Cf\.|Compare|Observe)\b",
    re.I,
)
STOPWORDS = {"or", "of", "and", "the", "a", "an", "to", "in", "with", "for", "is", "are", "was"}


def scan_url(leaf: int) -> str:
    return f"https://archive.org/details/{KEY_ITEM}/page/n{leaf}/mode/1up"


def image_url(leaf: int) -> str:
    return f"https://archive.org/download/{KEY_ITEM}/page/n{leaf}.jpg"


def _ascii(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )


def _norm_number(raw: str) -> int | None:
    number = re.sub(
        r"\s+",
        "",
        raw.replace("I", "1")
        .replace("l", "1")
        .replace("o", "0")
        .replace("O", "0")
        .replace("T", "1")
        .replace("t", "1")
        .replace("\u0431", "6")
        .replace("\u0411", "6"),
    )
    return int(number) if number.isdigit() else None


def load_vision(path: Path) -> list[list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[list[dict]] = []
    for page in data["pages"]:
        out.append(sorted(page["lines"], key=lambda line: (round(line["y"] / 12), line["x"])))
    return out


def _ordered_lines(page: list[dict]) -> list[dict]:
    return page


def english_answer_lists(vision: list[list[dict]]) -> list[dict]:
    """Part-A (English) answer lists, keyed by printed number and section/part."""
    section = 1
    part = ""
    buffers: dict[tuple[int, str], list[str]] = {}
    buffer_leafs: dict[tuple[int, str], int] = {}
    order: list[tuple[int, str]] = []
    for leaf, lines in enumerate(vision):
        if not lines:
            continue
        running_head = lines[0]["t"].strip()
        for raw in SECTION_ANY_RE.findall(_ascii(running_head)):
            number = _norm_number(raw)
            if number is not None and section < number <= section + 3:
                section = number
                part = ""
                break
        for line in lines:
            text = line["t"].strip()
            if not text or line is lines[0]:
                continue
            bare_section = BARE_SECTION_RE.match(_ascii(text))
            if bare_section:
                number = _norm_number(bare_section.group(1))
                if number is not None and section <= number <= section + 5:
                    section = number
                    part = ""
                continue
            bare_part = BARE_PART_RE.match(text)
            if bare_part:
                part = bare_part.group(1)
                continue
            if part != "A":
                continue
            # The footnotes close the printed answer list.
            if FOOTNOTE_RE.match(text) and not NUMBERED_ENGLISH_RE.search(text):
                part = ""
                continue
            if INSTRUCTION_LINE_RE.match(text):
                continue
            if not ENGLISH_LINE_RE.findall(text):
                continue
            key = (section, part)
            if key not in buffers:
                buffers[key] = []
                buffer_leafs[key] = leaf
                order.append(key)
            buffers[key].append(text)

    items: list[dict] = []
    for key in order:
        section, part = key
        leaf = buffer_leafs[key]
        joined = re.sub(r"\s+", " ", " ".join(buffers[key]))
        if NUMBERED_ENGLISH_RE.search(joined):
            matches = list(NUMBERED_ENGLISH_RE.finditer(joined))
            for index, match in enumerate(matches):
                number = int(match.group(1))
                end = matches[index + 1].start() if index + 1 < len(matches) else len(joined)
                body = joined[match.end() : end].strip()
                sentence = re.split(r"(?<!\w)(\d{1,2})\.\s+", body)[0].strip()
                sentence = re.sub(r"\s+", " ", sentence).strip(" .,;:\u2018\u2019'\u201c\u201d*")
                if sentence and len(LAT_RE.findall(sentence)) >= 3:
                    items.append(
                        {
                            "section": section,
                            "part": part,
                            "number": number,
                            "script": "en",
                            "text": sentence,
                            "leaf": leaf,
                            "scanUrl": scan_url(leaf),
                            "imageUrl": image_url(leaf),
                        }
                    )
        else:
            if section > 9:
                # Later sections' A answers are prose or tables; keep whole
                # sentences rather than exploding them into word tokens.
                for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", joined):
                    sentence = sentence.strip(" .,;:")
                    if len(LAT_RE.findall(sentence)) >= 3:
                        items.append(
                            {
                                "section": section,
                                "part": part,
                                "number": None,
                                "script": "en",
                                "text": sentence,
                                "leaf": leaf,
                                "scanUrl": scan_url(leaf),
                                "imageUrl": image_url(leaf),
                            }
                        )
            else:
                # Unnumbered transliteration word lists (sections 1-9).
                for token in re.split(r"[\s,;]+", joined):
                    clean = INVISIBLE_RE.sub("", token).strip(".,;:|\u00b7()[]'\"")
                    if (
                        len(LAT_RE.findall(clean)) >= 2
                        and len(clean) <= 24
                        and clean.casefold() not in STOPWORDS
                    ):
                        items.append(
                            {
                                "section": section,
                                "part": part,
                                "number": None,
                                "script": "en",
                                "text": clean,
                                "leaf": leaf,
                                "scanUrl": scan_url(leaf),
                                "imageUrl": image_url(leaf),
                            }
                        )
    return items


def hebrew_answer_lists() -> list[dict]:
    """Part-B/C/D (Hebrew) answers: DjVu tracking + tesseract Hebrew glyphs."""
    import tess

    djvu_pages = recover.load_djvu(SOURCES / "key-1924-djvu.xml")
    tess_pages, tess_heights = tess.tesseract_pages(SOURCES / "_tess" / "key", 168)
    for page in sorted((SOURCES / "_tess" / "key").glob("n*.tsv")):
        tess_heights[int(page.stem[1:])] = tess.tsv_page_height(page)
    djvu_heights = recover.djvu_page_heights(SOURCES / "key-1924-djvu.xml")
    merged = recover.merge_word_sources(djvu_pages, tess_pages, djvu_heights, tess_heights)
    lists: list[dict] = []
    for answer in recover.parse_key(djvu_pages, merged):
        for index, (number, text) in enumerate(zip(answer.numbers, answer.hebrew)):
            leaf = answer.leaves[index] if index < len(answer.leaves) else answer.leaf
            lists.append(
                {
                    "section": answer.section,
                    "part": answer.part,
                    "number": number,
                    "script": "he",
                    "text": text,
                    "leaf": leaf,
                    "scanUrl": scan_url(leaf),
                    "imageUrl": image_url(leaf),
                }
            )
    return lists


def unit_for_section() -> dict[int, list[int]]:
    return recover.unit_sections()


def write_inventory(english: list[dict], hebrew: list[dict]) -> Path:
    units = unit_for_section()
    all_items = english + hebrew
    by_section: dict[int, int] = {}
    by_script = {"en": 0, "he": 0}
    units_touched: set[int] = set()
    for item in all_items:
        by_section[item["section"]] = by_section.get(item["section"], 0) + 1
        by_script[item["script"]] = by_script.get(item["script"], 0) + 1
        for unit, sections in units.items():
            if item["section"] in sections:
                units_touched.add(unit)
    path = SOURCES / "key-answer-inventory.json"
    path.write_text(
        json.dumps(
            {
                "schema": "davidson-key-answer-inventory-v1.json",
                "source": {
                    "item": KEY_ITEM,
                    "edition": "1924",
                    "visionOCR": "key-vision-en.json",
                    "djvuOCR": "key-1924-djvu.xml",
                },
                "coverage": {
                    "totalItems": len(all_items),
                    "englishPartAItems": len(english),
                    "hebrewPartsBCItems": len(hebrew),
                    "sections": sorted(by_section),
                    "itemsBySection": by_section,
                    "courseUnitsTouched": sorted(units_touched),
                    "note": (
                        "No caps, no grammar matching. Item text is OCR best-effort with the "
                        "exact key scan leaf per item; the leaf link is the arbiter."
                    ),
                },
                "items": sorted(all_items, key=lambda item: (item["section"], item["part"], item["number"])),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the answer inventory JSON")
    args = parser.parse_args()
    vision = load_vision(SOURCES / "key-vision-en.json")
    english = english_answer_lists(vision)
    hebrew = hebrew_answer_lists()
    print(f"Part-A English answers: {len(english)} items")
    print(f"Part-B/C/D Hebrew answers: {len(hebrew)} items")
    print(f"Total: {len(english) + len(hebrew)} items")
    sections: dict[int, dict[str, int]] = {}
    for item in english + hebrew:
        entry = sections.setdefault(item["section"], {"en": 0, "he": 0})
        entry[item["script"]] += 1
    print("By section:", {f"\u00a7{n}": counts for n, counts in sorted(sections.items())})
    if args.write:
        print(f"Wrote {write_inventory(english, hebrew)}")


if __name__ == "__main__":
    main()
