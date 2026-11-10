"""Inventory every OCR-detectable Davidson exercise and its items (no key matching).

Reads the 22nd-edition grammar OCR (Apple Vision for the English columns, IA DjVu
for the Hebrew script) and extracts every exercise block plus its individual items:
numbered Hebrew forms/phrases, Hebrew word lists, numbered English sentences,
English sentence columns, and transliteration word lists. Nothing is dropped for
quantity reasons and no answer key is consulted. Every block and item carries the
grammar scan page it was read from.

    python build/inventory_davidson_exercises.py
    python build/inventory_davidson_exercises.py --write
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))

import recover_davidson_exercises as recover  # noqa: E402

SOURCES = ROOT / "build" / "_sources" / "davidson"
ITEM_ID = "introductoryhebr0000davi_w1b2"

HEB_CONSONANT_RE = re.compile(r"[\u05d0-\u05ea]")
LAT_RE = re.compile(r"[A-Za-z]")
INVISIBLE_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff\u00ad]")
EXERCISE_HEAD_RE = re.compile(r"^\s*[Xx*]?\s*EXERCISE\b", re.I)
# The OCR prints § as §, 8, S, $, or ₪, and digits with T/t for 1.
SECTION_BODY_RE = re.compile(r"[§8S$₪]\s*([0-9IlOo1Tt][0-9IlOo1Tt ]{0,3})[.,]?\s+[A-Z\"'][A-Z\"' ,.'&()\-]{4,}")
ANY_SECTION_RE = re.compile(r"[§8S$₪]\s*[0-9IlOo1Tt][0-9IlOo1Tt ]{0,3}[.,]?\s+[A-Z\"'][A-Z\"' ,.'&()\-]{4,}")
NUMBER_RE = re.compile(r"^\d{1,2}$")
NUMBERED_ENGLISH_RE = re.compile(r"(?<![\w§])(\d{1,2})\.\s+(?=[A-Z(\"\u201c])")
SENTENCE_BREAK_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"\u201c])")
DJVU_HEADING_RE = re.compile(r"^\s*[\\|™*'\"0-9Xx ]{0,8}EXERCISE", re.I)

MAX_NUMBER = 40


def scan_url(leaf: int) -> str:
    return f"https://archive.org/details/{ITEM_ID}/page/n{leaf}/mode/1up"


def image_url(leaf: int) -> str:
    return f"https://archive.org/download/{ITEM_ID}/page/n{leaf}.jpg"


def load_sources() -> tuple[list[dict], list[list[tuple[float, str]]], list[float], list[list[recover.DjvuLine]]]:
    vision = json.loads((SOURCES / "grammar-vision-en.json").read_text(encoding="utf-8"))["pages"]
    root = ElementTree.parse(SOURCES / "grammar-1923-22nd-djvu.xml").getroot()
    djvu_pages: list[list[tuple[float, str]]] = []
    djvu_heights: list[float] = []
    for obj in root.iter("OBJECT"):
        djvu_heights.append(float(obj.get("height", "0") or 0))
        lines: list[tuple[float, str]] = []
        for line in obj.iter("LINE"):
            words = list(line.findall("WORD"))
            if not words:
                continue
            ys = []
            for word in words:
                coords = [int(value) for value in word.get("coords", "0,0,0,0").split(",")]
                ys.append((coords[1] + coords[3]) / 2)
            text = " ".join((word.text or "") for word in words).strip()
            if text:
                lines.append((sum(ys) / len(ys), text))
        djvu_pages.append(lines)
    djvu_words = recover.load_djvu(SOURCES / "grammar-1923-22nd-djvu.xml")
    return vision, djvu_pages, djvu_heights, djvu_words
    return vision, djvu_pages, djvu_heights


def _ordered_lines(page: dict) -> list[dict]:
    return sorted(page["lines"], key=lambda line: (round(line["y"] / 12), line["x"]))


def _ascii(text: str) -> str:
    """Strip OCR diacritics so headings like 'DÄGHESH' match their plain form."""
    return "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )


def _norm_number(raw: str) -> int | None:
    number = re.sub(
        r"\s+",
        "",
        raw.replace("I", "1").replace("l", "1").replace("o", "0").replace("O", "0").replace("T", "1").replace("t", "1"),
    )
    return int(number) if number.isdigit() else None


def section_heading(text: str) -> int | None:
    match = SECTION_BODY_RE.search(_ascii(text))
    return _norm_number(match.group(1)) if match else None


def is_section_heading_line(text: str) -> bool:
    """Any §-style heading, including running heads like '46 § 13. TITLE'."""
    return ANY_SECTION_RE.search(_ascii(text)) is not None


def kind_guess(heading: str) -> str:
    text = heading.casefold()
    for key, kind in (
        ("transliter", "transliteration"),
        ("pronounc", "pronunciation"),
        ("correct", "correction"),
        ("parse", "parsing"),
        ("write", "writing"),
        ("dag.", "pointing"),
        ("translate", "translation"),
    ):
        if key in text:
            return kind
    return "unspecified"


def _is_exercise_heading(text: str) -> bool:
    return bool(EXERCISE_HEAD_RE.match(text)) and len(text) < 110


def _clean_token(token: str) -> str:
    return INVISIBLE_RE.sub("", token).strip(".,;:|\u00b7()[]'\"\u2018\u2019\u201c\u201d")


def _item_number(token: str) -> int | None:
    text = _clean_token(token)
    if NUMBER_RE.match(text):
        number = int(text)
        return number if 1 <= number <= MAX_NUMBER else None
    if text in {"ro", "io", "lo", "1o"}:
        return 10
    return None


def _djvu_heading_index(page_lines: list[tuple[float, str]]) -> int | None:
    for index, (_, text) in enumerate(page_lines):
        if DJVU_HEADING_RE.match(text) and len(text) < 110:
            return index
    return None


def _djvu_region(pages: list[list[tuple[float, str]]], leaf: int) -> list[tuple[float, str]]:
    region: list[tuple[float, str]] = []
    for current in (leaf, leaf + 1):
        if current >= len(pages):
            break
        lines = pages[current]
        start = _djvu_heading_index(lines) if current == leaf else 0
        if start is None:
            if current == leaf:
                # Some headings OCR'd without the word EXERCISE; fall back to
                # the lines after the last section heading on the leaf.
                start = max(
                    (index for index, (_, text) in enumerate(lines) if is_section_heading_line(text)),
                    default=0,
                )
            else:
                continue
        for y, text in lines[(start + 1) if current == leaf else 0 :]:
            if is_section_heading_line(text) or re.match(r"^Note\b", text):
                break
            region.append((y, text))
    return region


def _djvu_region_words(pages: list[list[recover.DjvuLine]], leaf: int) -> list[tuple[int, recover.DjvuLine]]:
    """The same region bounds as ``_djvu_region``, but with word boxes per line."""
    region: list[tuple[int, recover.DjvuLine]] = []
    for current in (leaf, leaf + 1):
        if current >= len(pages):
            break
        lines = pages[current]
        start = None
        for index, line in enumerate(lines):
            if DJVU_HEADING_RE.match(line.text) and len(line.text) < 110:
                start = index
                break
        if start is None:
            if current == leaf:
                start = max(
                    (index for index, line in enumerate(lines) if is_section_heading_line(line.text)),
                    default=0,
                )
            else:
                continue
        for line in lines[(start + 1) if current == leaf else 0 :]:
            if is_section_heading_line(line.text) or re.match(r"^Note\b", line.text):
                break
            region.append((current, line))
    return region


def coordinate_hebrew_items(region_words: list[tuple[int, recover.DjvuLine]]) -> list[dict]:
    """Numbered Hebrew prompts via the coordinate parser shared with the key side."""
    items: list[dict] = []
    for number, phrase, _leaf in recover._coordinate_answers(region_words):
        if phrase:
            items.append({"number": number, "script": "he", "text": phrase})
    return items


def _vision_region(pages: list[dict], leaf: int) -> list[tuple[float, str]]:
    by_leaf = {int(page["page"]) - 1: page for page in pages}
    region: list[tuple[float, str]] = []
    for current in (leaf, leaf + 1):
        page = by_leaf.get(current)
        if page is None:
            break
        lines = _ordered_lines(page)
        started = current != leaf
        for line in lines:
            text = line["t"].strip()
            if not text:
                continue
            if not started:
                if _is_exercise_heading(text):
                    started = True
                continue
            if is_section_heading_line(text):
                break
            region.append((line["y"], text))
    return region


def _hebrew_column_cutoff(
    region: list[tuple[float, str]], margin: float = 25.0
) -> float | None:
    """DjVu y below which the English column starts, or None.

    The pointed Hebrew column is stacked above the English column. The first
    line of the region that reads as a clean English sentence (several Latin
    words, sentence punctuation, at most one embedded Hebrew word) marks the top
    of the English column.
    """
    for y, text in region:
        hebrew_words = len(HEB_CONSONANT_RE.findall(text))
        latin_words = len(LAT_RE.findall(text))
        if latin_words >= 6 and hebrew_words <= 1 and re.search(r"[.!?]", text):
            return y - margin
    return None


def _drop_hebrew_column_lines(
    vision_region: list[tuple[float, str]],
    cutoff: float | None,
    scale: float,
) -> list[str]:
    """Drop Vision lines that sit above the English column (the Hebrew block).

    Vision reads the pointed Hebrew column as Latin garble glued to the English
    column; matching the two OCRs' y coordinates on the same page lets us drop
    those rows instead of salvaging their garble.
    """
    if cutoff is None:
        return [text for _, text in vision_region]
    out: list[str] = []
    for y, text in vision_region:
        if y * scale < cutoff:
            continue
        out.append(text)
    return out


# ----------------------------------------------------------------- item extraction


def _clean_hebrew_token(token: str) -> str:
    text = _clean_token(token)
    return text if len(HEB_CONSONANT_RE.findall(text)) >= 2 else ""


def extract_hebrew_items(djvu_lines: list[str]) -> list[dict]:
    """Numbered Hebrew forms/phrases plus Hebrew word-list entries, in OCR order."""
    items: list[dict] = []
    current_number: int | None = None
    current_words: list[str] = []
    for line in djvu_lines:
        for token in re.split(r"[\s,;]+", line):
            number = _item_number(token)
            if number is not None:
                if current_words:
                    items.append({"number": current_number, "script": "he", "text": " ".join(current_words)})
                current_number = number
                current_words = []
                continue
            word = _clean_hebrew_token(token)
            if word:
                if current_number is not None:
                    current_words.append(word)
                else:
                    items.append({"number": None, "script": "he", "text": word})
    if current_words:
        items.append({"number": current_number, "script": "he", "text": " ".join(current_words)})
    return _collapse_hebrew(items)


def _collapse_hebrew(items: list[dict]) -> list[dict]:
    """Merge a numbered phrase split across lines, and drop exact neighbours."""
    out: list[dict] = []
    for item in items:
        if item["number"] is not None:
            tokens = item["text"].split()
            if len(tokens) >= 4 and tokens[:2] == tokens[2:][::-1]:
                tokens = tokens[:2]
            item["text"] = " ".join(tokens)
            out.append(item)
            continue
        if out and out[-1]["number"] is None and out[-1]["text"] == item["text"]:
            continue
        out.append(item)
    return out


_INSTRUCTION_LINE_RE = re.compile(
    r"^\s*(?:Write|Translate|Express|Point|Pronounce|Correct|Parse|Supply|Give|Put|Divide|Note\b|"
    r"\d{1,2}\s+|[§8S$₪]|Cf\.|See\s|Masc\.)",
    re.I,
)


def _djvu_english_lines(region: list[tuple[float, str]], cutoff: float | None = None) -> list[str]:
    """The English column of a DjVu region: lines with real English and no Hebrew.

    The grammar stacks the pointed Hebrew column above the English column, and
    Tesseract keeps Hebrew script, so the English column is simply the region
    lines at or below the English-column cutoff that carry several Latin words
    and at most one embedded Hebrew word.
    """
    out: list[str] = []
    for y, line in region:
        if cutoff is not None and y < cutoff:
            continue
        hebrew_words = len(HEB_CONSONANT_RE.findall(line))
        latin_words = len(LAT_RE.findall(line))
        if latin_words >= 6 and hebrew_words <= 1:
            out.append(line)
    return out


def extract_english_items(vision_lines: list[str]) -> list[dict]:
    """Numbered English sentences, sentence columns, or transliteration word lists."""
    usable = [line for line in vision_lines if not _INSTRUCTION_LINE_RE.match(line.strip())]
    text = re.sub(r"\s+", " ", " ".join(usable))
    items: list[dict] = []
    if NUMBERED_ENGLISH_RE.search(text):
        matches = list(NUMBERED_ENGLISH_RE.finditer(text))
        for index, match in enumerate(matches):
            number = int(match.group(1))
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[match.end() : end].strip()
            sentence = re.split(r"(?<!\w)(\d{1,2})\.\s+", body)[0].strip()
            sentence = _clean_english_sentence(sentence)
            if sentence:
                items.append({"number": number, "script": "en", "text": sentence})
    else:
        breaks = len(SENTENCE_BREAK_RE.findall(text))
        commas = text.count(",")
        if breaks >= 2 or (breaks >= 1 and commas < 4):
            for sentence in SENTENCE_BREAK_RE.split(text):
                sentence = _clean_english_sentence(sentence)
                if sentence:
                    items.append({"number": None, "script": "en", "text": sentence})
        else:
            for token in re.split(r"[\s,;]+", text):
                clean = _clean_token(token)
                if len(LAT_RE.findall(clean)) >= 2 and len(clean) <= 24:
                    items.append({"number": None, "script": "en", "text": clean})
    # Salvage lines polluted by Hebrew-column garble: keep the clean English runs.
    salvaged: list[dict] = []
    for item in items:
        if recoverable_english(item["text"]):
            salvaged.append(item)
            continue
        for run in _salvage_english(item["text"]):
            salvaged.append({**item, "text": run})
    return salvaged


_INSTRUCTION_RE = re.compile(
    r"^(?:write|translate|express|point|pronounce|correct|parse|supply|give|put|divide)\b",
    re.I,
)


def _clean_english_sentence(sentence: str) -> str:
    text = re.sub(r"\s+", " ", sentence).strip(" .,;:\u2018\u2019'\u201c\u201d*")
    if len(LAT_RE.findall(text)) < 2:
        return ""
    latin = len(LAT_RE.findall(text))
    if latin / max(1, len(re.sub(r"\s", "", text))) < 0.45:
        return ""
    if _INSTRUCTION_RE.match(text) and len(text.split()) <= 8:
        return ""
    return text


# ------------------------------------------------------------------- discovery


def discover_blocks(
    vision: list[dict],
    djvu_pages: list[list[tuple[float, str]]],
    djvu_heights: list[float],
    djvu_words: list[list[recover.DjvuLine]] | None = None,
) -> list[dict]:
    vision_by_leaf = {int(page["page"]) - 1: page for page in vision}
    headings_by_page: dict[int, list[tuple[int, dict]]] = {}
    for page in vision:
        leaf = int(page["page"]) - 1
        for line_index, line in enumerate(_ordered_lines(page)):
            if _is_exercise_heading(line["t"].strip()):
                headings_by_page.setdefault(leaf, []).append((line_index, line))

    locations = sorted(
        (
            (leaf, line_index, line)
            for leaf, entries in headings_by_page.items()
            for line_index, line in entries
        ),
        key=lambda item: (item[0], item[2]["y"], item[2]["x"]),
    )
    blocks: list[dict] = []
    for leaf, _, heading_line in locations:
        page = vision_by_leaf[leaf]
        page_lines = _ordered_lines(page)
        heading_text = heading_line["t"].strip()
        section_heads = sorted(
            ((section_heading(line["t"]), line["y"]) for line in page_lines if section_heading(line["t"]) is not None),
            key=lambda item: item[1],
        )
        running_section = section_heads[0][0] if section_heads else None
        body_headings = [entry for entry in section_heads if entry[1] >= 160]
        body_y = body_headings[0][1] if body_headings else None
        if body_y is not None:
            section = running_section if heading_line["y"] >= body_y else (running_section - 1 if running_section else None)
        else:
            section = running_section

        djvu_heading = ""
        if leaf < len(djvu_pages):
            for _, text in djvu_pages[leaf]:
                if _is_exercise_heading(text):
                    djvu_heading = text
                    break
        best_heading = djvu_heading if len(djvu_heading) > len(heading_text) else heading_text

        djvu_region = _djvu_region(djvu_pages, leaf)
        vision_region = _vision_region(vision, leaf)
        hebrew_items = extract_hebrew_items([text for _, text in djvu_region])
        if djvu_words is not None:
            region_words = _djvu_region_words(djvu_words, leaf)
            coordinate_items = coordinate_hebrew_items(region_words)
            if coordinate_items:
                hebrew_items = coordinate_items
        vision_height = float(page.get("height", 0) or 0)
        djvu_height = djvu_heights[leaf] if leaf < len(djvu_heights) else 0.0
        scale = djvu_height / (2 * vision_height) if vision_height else 1.0
        # Anchor the two coordinate spaces on the exercise heading line itself,
        # where both OCRs read the same printed row, for a tighter scale.
        heading_index = _djvu_heading_index(djvu_pages[leaf])
        if heading_index is not None:
            djvu_heading_y = djvu_pages[leaf][heading_index][0]
            if djvu_heading_y > 0 and heading_line["y"] > 0:
                scale = djvu_heading_y / heading_line["y"]
        cutoff = _hebrew_column_cutoff(djvu_region)
        clean_vision_lines = _drop_hebrew_column_lines(vision_region, cutoff, scale)
        english_items = extract_english_items(clean_vision_lines)
        djvu_english = extract_english_items(_djvu_english_lines(djvu_region, cutoff))
        if len(djvu_english) >= len(english_items):
            english_items = djvu_english

        blocks.append(
            {
                "id": f"davidson-ex-{len(blocks) + 1:03d}",
                "section": section,
                "kindGuess": kind_guess(best_heading),
                "headingOCR": best_heading,
                "promptLeaf": leaf,
                "promptUrl": scan_url(leaf),
                "promptImageUrl": image_url(leaf),
                "djvuRegionLines": [text for _, text in djvu_region],
                "visionRegionLines": clean_vision_lines,
                "hebrewItems": hebrew_items,
                "englishItems": english_items,
                "itemCount": len(hebrew_items) + len(english_items),
            }
        )
    return blocks


# ------------------------------------------------------------------- quality


def _letters(text: str) -> list[str]:
    return [char for char in text if unicodedata.category(char).startswith("L")]


def recoverable_hebrew(text: str) -> bool:
    """A complete-looking Hebrew form/word, not an OCR fragment."""
    if not text:
        return False
    letters = _letters(text)
    hebrew = sum(1 for char in letters if "\u0590" <= char <= "\u05ff")
    return hebrew >= 2 and hebrew / len(letters) >= 0.6


def recoverable_english(text: str) -> bool:
    """A complete-looking English sentence or transliteration word."""
    if not text:
        return False
    letters = _letters(text)
    latin = sum(1 for char in letters if char.isascii() and char.isalpha())
    latin += sum(1 for char in letters if "\u00c0" <= char <= "\u024f")
    if latin < 2 or latin / len(letters) < 0.8 or len(text.split()) > 40:
        return False
    # Require most letter-bearing tokens to be Latin-dominant, so lines whose
    # garble outweighs the English tail are still flagged for salvage.
    latin_tokens = 0
    letter_tokens = 0
    for token in text.split():
        token_letters = _letters(token)
        if not token_letters:
            continue
        letter_tokens += 1
        token_latin = sum(1 for char in token_letters if char.isascii() and char.isalpha())
        token_latin += sum(1 for char in token_letters if "\u00c0" <= char <= "\u024f")
        if token_latin / len(token_letters) >= 0.6:
            latin_tokens += 1
    return letter_tokens == 0 or latin_tokens / letter_tokens >= 0.8


def _salvage_english(text: str) -> list[str]:
    """Recover the clean English runs of a line polluted by Hebrew-column garble.

    Vision reads the pointed Hebrew column as Latin-ish garble glued to the real
    English column. Splitting the line into runs of ASCII-Latin-dominant tokens
    and keeping the readable runs recovers the English prompts.
    """
    runs: list[list[str]] = []
    current: list[str] = []
    for token in text.split():
        letters = _letters(token)
        if not letters:
            continue
        latin = sum(1 for char in letters if char.isascii() and char.isalpha())
        latin += sum(1 for char in letters if "\u00c0" <= char <= "\u024f")
        if latin / len(letters) >= 0.7:
            current.append(token)
        else:
            if current:
                runs.append(current)
            current = []
    if current:
        runs.append(current)
    out: list[str] = []
    for run in runs:
        joined = re.sub(r"\s+", " ", " ".join(run)).strip(" .,;:\u2018\u2019'\u201c\u201d*")
        if not recoverable_english(joined):
            continue
        if len(LAT_RE.findall(joined)) < 4:
            continue
        if _INSTRUCTION_LINE_RE.match(joined):
            continue
        tokens = joined.split()
        if len(tokens) >= 2 and tokens[0][:1].islower():
            continue
        out.append(joined)
    return out


def quality(blocks: list[dict]) -> dict:
    hebrew_ok = hebrew_bad = english_ok = english_bad = 0
    for block in blocks:
        for item in block["hebrewItems"]:
            if recoverable_hebrew(item["text"]):
                hebrew_ok += 1
            else:
                hebrew_bad += 1
        for item in block["englishItems"]:
            if recoverable_english(item["text"]):
                english_ok += 1
            else:
                english_bad += 1
    ok = hebrew_ok + english_ok
    bad = hebrew_bad + english_bad
    return {
        "recoverableItems": ok,
        "unrecoverableItems": bad,
        "recoverableHebrewItems": hebrew_ok,
        "recoverableEnglishItems": english_ok,
        "distinctRecoverableItems": len(
            {
                item["text"]
                for block in blocks
                for item in block["hebrewItems"]
                if recoverable_hebrew(item["text"])
            }
        )
        + len(
            {
                item["text"]
                for block in blocks
                for item in block["englishItems"]
                if recoverable_english(item["text"])
            }
        ),
    }


def write_inventory(blocks: list[dict]) -> Path:
    kinds: dict[str, int] = {}
    for block in blocks:
        kinds[block["kindGuess"]] = kinds.get(block["kindGuess"], 0) + 1
    path = SOURCES / "grammar-exercise-inventory.json"
    path.write_text(
        json.dumps(
            {
                "schema": "davidson-grammar-exercise-inventory-v1.json",
                "source": {
                    "item": ITEM_ID,
                    "edition": "22nd (1923)",
                    "visionOCR": "grammar-vision-en.json",
                    "djvuOCR": "grammar-1923-22nd-djvu.xml",
                },
                "coverage": {
                    "exerciseBlocks": len(blocks),
                    "blocksByKindGuess": kinds,
                    "hebrewItems": sum(len(block["hebrewItems"]) for block in blocks),
                    "englishItems": sum(len(block["englishItems"]) for block in blocks),
                    "totalItems": sum(block["itemCount"] for block in blocks),
                    **quality(blocks),
                    "note": (
                        "No answer-key matching, no caps. Item text is OCR best-effort with the "
                        "prompt page linked. recoverable* counts items that OCR extracted as "
                        "complete-looking items (a recoverable item can still contain letter-level "
                        "OCR errors; the scan link is the arbiter). Unrecoverable items are "
                        "fragments, mixed-script garble, or footnote remnants."
                    ),
                },
                "blocks": blocks,
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
    parser.add_argument("--write", action="store_true", help="write the inventory JSON")
    args = parser.parse_args()
    vision, djvu, djvu_heights, djvu_words = load_sources()
    blocks = discover_blocks(vision, djvu, djvu_heights, djvu_words)
    counts: dict[str, int] = {}
    total = 0
    for block in blocks:
        counts[block["kindGuess"]] = counts.get(block["kindGuess"], 0) + 1
        total += block["itemCount"]
        print(
            f"  {block['id']} §{block['section'] or '?'} {block['kindGuess']:<16} "
            f"n{block['promptLeaf']:<3} heb={len(block['hebrewItems']):>3} "
            f"en={len(block['englishItems']):>3} | {block['headingOCR'][:58]}"
        )
    print(f"\nExercise blocks: {len(blocks)} ({counts})")
    print(
        f"Items found: {total} total = "
        f"{sum(len(b['hebrewItems']) for b in blocks)} Hebrew + "
        f"{sum(len(b['englishItems']) for b in blocks)} English"
    )
    stats = quality(blocks)
    print(
        f"Recoverable: {stats['recoverableItems']} of {total} "
        f"({stats['recoverableHebrewItems']} Hebrew, {stats['recoverableEnglishItems']} English); "
        f"{stats['unrecoverableItems']} garbled fragments; "
        f"{stats['distinctRecoverableItems']} distinct"
    )
    if args.write:
        print(f"Wrote {write_inventory(blocks)}")


if __name__ == "__main__":
    main()
