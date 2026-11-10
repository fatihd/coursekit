"""Rebuild the Davidson *Key to the Exercises* (1924) exercises.

English prompts are read from the 22nd-edition grammar (1923), whose English is
clean under Apple Vision OCR. Hebrew answers are read from the 1924 key's DjVu
text export (Tesseract), which keeps Hebrew script that Vision mangles. Every
item carries the scan pages of its prompt and its answer, so an OCR misreading
is a five-second detour through the original page rather than a dead end.

    python build/recover_davidson_exercises.py --report
    python build/recover_davidson_exercises.py --write

Layout facts this script relies on:

* The grammar prints, after a body heading, an ``EXERCISE. TRANSLATE.`` block
  with two columns: pointed Hebrew (part A, translate into English) and English
  (part B, translate into Hebrew). A page-top heading is a *running head* that
  does not change the section; the exercise belongs to the last body heading.
* The key answers part A in English and parts B/C/D in Hebrew. The running head
  ("§ 11. B-§ 12. A.") and bare markers ("§ 13.", "B.") locate each list. The
  Hebrew list is printed right-to-left and the OCR reads it right-to-left, so a
  linear join of a page's lines is already in reading order.
* IA scan leaf ``n`` = DjVu object index = Vision page index minus one (the PDF
  has a leading blank page).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "build" / "_sources" / "davidson"
COURSE = ROOT / "courses" / "biblical-hebrew-davidson"
CHAPTERS = COURSE / "content" / "chapters"

GRAMMAR_ITEM = "introductoryhebr0000davi_w1b2"
KEY_ITEM = "keytoexercisesin0000mcfa"

HEB_RE = re.compile(r"[\u0590-\u05FF]")
HEB_CONSONANT_RE = re.compile(r"[\u05D0-\u05EA]")
LAT_RE = re.compile(r"[A-Za-z]")
NIQQUD_RE = re.compile(r"[\u0591-\u05C7]")
# Invisible bidi/format characters the OCR leaves glued to tokens.
INVISIBLE_RE = re.compile(r"[\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff\u00ad]")
SECTION_RE = re.compile(r"[§8S]\s*([0-9IlOo1][0-9IlOo1 ]{0,3})")
TITLE_HEADING_RE = re.compile(
    r"[§8S]\s*([0-9IlOo1][0-9IlOo1 ]{0,3})[.,]?\s+([A-Z][A-Z ,.'&()\-]{4,})"
)
EXERCISE_RE = re.compile(r"\bEXERCISE\b", re.I)
NUMBER_RE = re.compile(r"(?<!\d)(\d{1,2})(?!\d)")

MAX_ANSWER_WORDS = 4
MIN_HEBREW_CONSONANTS = 2
RUNNING_HEAD_Y = 200  # Vision top-origin y below which a heading is a running head


# --------------------------------------------------------------------------- io


def scan_url(item_id: str, leaf: int) -> str:
    return f"https://archive.org/details/{item_id}/page/n{leaf}/mode/1up"


def load_vision(path: Path) -> list[list[dict]]:
    """Vision JSON -> per-page list of line dicts {t, x, y}, sorted top-down."""
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[list[dict]] = []
    for page in data["pages"]:
        lines = sorted(page["lines"], key=lambda ln: (round(ln["y"] / 12), ln["x"]))
        out.append(lines)
    return out


@dataclass
class DjvuWord:
    text: str
    x0: int
    x1: int
    y: float = 0.0


@dataclass
class DjvuLine:
    text: str
    words: list[DjvuWord]
    y: float = 0.0


def load_djvu(path: Path) -> list[list[DjvuLine]]:
    """DjVu XML -> line text plus word boxes, preserving the IA leaf index."""
    root = ElementTree.parse(path).getroot()
    pages: list[list[DjvuLine]] = []
    for obj in root.iter("OBJECT"):
        lines: list[DjvuLine] = []
        for line in obj.iter("LINE"):
            words: list[DjvuWord] = []
            for word in line.findall("WORD"):
                coords = [int(value) for value in word.get("coords", "0,0,0,0").split(",")]
                text = (word.text or "").strip()
                if text:
                    words.append(
                        DjvuWord(
                            text=text,
                            x0=coords[0],
                            x1=coords[2],
                            y=(coords[1] + coords[3]) / 2,
                        )
                    )
            if words:
                lines.append(
                    DjvuLine(
                        text=" ".join(word.text for word in words),
                        words=words,
                        y=sum(word.y for word in words) / len(words),
                    )
                )
        pages.append(lines)
    return pages


# --------------------------------------------------------------------- grammar


@dataclass
class GrammarExercise:
    section: int
    leaf: int  # IA scan leaf of the English column (Vision page - 1)
    english: list[str] = field(default_factory=list)


def _norm_number(raw: str) -> int | None:
    """Normalise an OCR'd section number ('I1' -> 11, '1o' -> 10)."""
    s = (
        raw.replace("I", "1")
        .replace("l", "1")
        .replace("o", "0")
        .replace("O", "0")
        .replace("T", "1")
        .replace("t", "1")
    )
    s = re.sub(r"\s+", "", s)
    if not s.isdigit():
        return None
    return int(s)


def heading_section(text: str) -> int | None:
    match = TITLE_HEADING_RE.search(text)
    if not match:
        return None
    return _norm_number(match.group(1))


def is_english_line(text: str) -> bool:
    words = re.findall(r"[A-Za-z]{2,}", text)
    if len(words) < 3:
        return False
    if len(HEB_CONSONANT_RE.findall(text)) >= 3:
        return False
    latin = len(LAT_RE.findall(text))
    total = len(re.sub(r"\s", "", text))
    return total > 0 and latin / total >= 0.55


def clean_prompt(text: str) -> str:
    text = text.strip()
    # Drop leading non-Latin OCR noise (Hebrew columns misread as Latin-ish).
    text = re.sub(r"^\s*[\d\s.,;:\-\u2014]+", "", text)
    text = text.strip()
    while text:
        first = text.split()[0]
        if len(LAT_RE.findall(first)) < 2 and len(first) >= 2:
            text = " ".join(text.split()[1:])
        else:
            break
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" .,;:\u2018\u2019'\u201c\u201d*")
    return text


_FOOTNOTE_RE = re.compile(
    r"cf\.|see\b|Note\b|Grammar,|p\.\s?\d|\bibid\b|Paradigm|Gloss|in apposition|pausal",
    re.I,
)


def _plausible_prompt(p: str) -> bool:
    if not p or len(LAT_RE.findall(p)) < 3 or len(p.split()) > 12:
        return False
    if HEB_CONSONANT_RE.search(p):
        return False
    return not _FOOTNOTE_RE.search(p)


def split_prompts(text: str) -> list[str]:
    """Split an English column into sentences at '. ' boundaries."""
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\u201c\"'(\[])|\s+$", text)
    out: list[str] = []
    for part in parts:
        p = clean_prompt(part)
        if _plausible_prompt(p):
            out.append(p)
    return out


def parse_grammar(vision: list[list[dict]]) -> list[GrammarExercise]:
    return _collect_exercises(vision)


def _collect_exercises(vision: list[list[dict]]) -> list[GrammarExercise]:
    """Collect each TRANSLATE exercise's English column and assign its section.

    The top § heading of a page is a running head; a § heading further down
    (y >= 160) is a body heading that opens a section. An exercise printed
    before the current page's body heading belongs to the *previous* section.
    When a page's running head names a section whose body starts on a later
    page, everything above that body still belongs to the previous section.
    """
    exercises: list[GrammarExercise] = []
    prev_running = 0

    for page_index, lines in enumerate(vision):
        leaf = page_index  # Vision page index == DjVu leaf == IA scan leaf n
        headings = sorted(
            (
                (heading_section(ln["t"]), ln["y"])
                for ln in lines
                if heading_section(ln["t"]) is not None
            ),
            key=lambda h: h[1],
        )
        running = headings[0][0] if headings else prev_running
        body = [h for h in headings if h[1] >= 160]
        body_y = body[0][1] if body else None

        block: list[str] | None = None
        block_leaf = 0
        block_section = 0

        for ln in lines:
            text = ln["t"].strip()
            if not text:
                continue
            if heading_section(text) is not None:
                continue
            if EXERCISE_RE.search(text) and len(text) < 90:
                if block is not None:
                    exercises.append(
                        _exercise_from_block(block_section, block_leaf, block)
                    )
                if "TRANSLATE" in text.upper():
                    block = []
                    block_leaf = leaf
                    if body_y is not None:
                        block_section = running if ln["y"] >= body_y else running - 1
                    else:
                        block_section = running if running == prev_running else running - 1
                else:
                    block = None
                continue
            if block is not None:
                if re.match(r"^(VOCABULARY|PARADIGM|INDEX|NOTE)\b", text, re.I):
                    exercises.append(
                        _exercise_from_block(block_section, block_leaf, block)
                    )
                    block = None
                    continue
                block.append(text)
        if block is not None:
            exercises.append(_exercise_from_block(block_section, block_leaf, block))
        prev_running = running

    return [e for e in exercises if e.section and e.english]


def _exercise_from_block(
    section: int | None, leaf: int | None, block: list[str]
) -> GrammarExercise:
    # The English column is the run of English lines after the pointed Hebrew
    # column.
    start = 0
    for i, line in enumerate(block):
        if len(HEB_CONSONANT_RE.findall(line)) >= 4:
            start = i + 1
    english_lines: list[str] = []
    for line in block[start:]:
        if is_english_line(line):
            english_lines.append(line)
        elif english_lines and len(english_lines) >= 3:
            break
    joined = " ".join(english_lines)
    prompts = split_prompts(joined)
    return GrammarExercise(section=section or 0, leaf=leaf or 0, english=prompts)


# ------------------------------------------------------------------------ key


@dataclass
class AnswerList:
    section: int
    part: str
    leaf: int = 0
    hebrew: list[str] = field(default_factory=list)
    leaves: list[int] = field(default_factory=list)
    numbers: list[int] = field(default_factory=list)


def _hebrew_phrase(text: str) -> str:
    """The leading pointed Hebrew run of a segment."""
    kept: list[str] = []
    for token in text.split():
        bare = INVISIBLE_RE.sub("", token).strip(".,;:|\u00b7()[]'\"\u2018\u2019\u201c\u201d")
        if not bare:
            continue
        if kept and NUMBER_RE.fullmatch(bare):
            break
        if HEB_CONSONANT_RE.search(bare):
            if kept and bare == kept[-1]:
                break
            kept.append(bare)
            if len(kept) >= MAX_ANSWER_WORDS:
                break
        elif kept:
            break
    # Drop a leading single-letter token: the garbled item number ('1' -> 'ז').
    while kept and len(kept[0]) == 1 and kept[0] != "\u05d5" and HEB_CONSONANT_RE.fullmatch(kept[0]):
        kept.pop(0)
    return " ".join(kept)


def _head_numbers(text: str) -> list[int]:
    """Section numbers named in a running head, in printed order."""
    out: list[int] = []
    for match in re.finditer(r"[§8S$₪]\s*[.,]?\s*([0-9IlOo1Tt][0-9IlOo1Tt ]{0,3})", text):
        number = _norm_number(match.group(1))
        if number is not None:
            out.append(number)
    return out


def djvu_page_heights(path: Path) -> list[float]:
    root = ElementTree.parse(path).getroot()
    return [float(obj.get("height", "0") or 0) for obj in root.iter("OBJECT")]


def merge_word_sources(
    track: list[list[DjvuLine]],
    text: list[list[DjvuLine]],
    track_heights: list[float] | None = None,
    text_heights: list[float] | None = None,
) -> list[list[DjvuLine]]:
    """Union of the two OCRs' word boxes per leaf.

    Tesseract reads most Hebrew better, but it silently drops some words that
    the DjVu export keeps (e.g. the first items of §11 B). Words from ``track``
    that have no ``text`` word nearby are appended, so no row loses words that
    either OCR saw.
    """
    merged: list[list[DjvuLine]] = []
    for leaf in range(max(len(track), len(text))):
        track_lines = track[leaf] if leaf < len(track) else []
        text_lines = text[leaf] if leaf < len(text) else []
        scale = 1.0
        if track_heights and text_heights and leaf < len(track_heights) and leaf < len(text_heights):
            track_h = track_heights[leaf] or 0.0
            text_h = text_heights[leaf] or 0.0
            if track_h and text_h:
                scale = text_h / track_h
        words: list[DjvuWord] = [word for line in text_lines for word in line.words]
        for line in track_lines:
            for word in line.words:
                if len(HEB_CONSONANT_RE.findall(word.text)) < 2:
                    continue
                wx = word.x0 * scale
                wy = word.y * scale
                covered = any(
                    abs((other.x0 + other.x1) / 2 - (wx + word.x1 * scale) / 2) < 30
                    and abs(other.y - wy) < 25
                    for other in words
                )
                if not covered:
                    words.append(
                        DjvuWord(
                            text=word.text,
                            x0=int(wx),
                            x1=int(word.x1 * scale),
                            y=wy,
                        )
                    )
        lines: list[DjvuLine] = []
        for y in sorted({round(word.y / 30) for word in words}):
            group = [word for word in words if round(word.y / 30) == y]
            lines.append(
                DjvuLine(
                    text=" ".join(word.text for word in group),
                    words=group,
                    y=sum(word.y for word in group) / len(group),
                )
            )
        merged.append(lines)
    return merged


def parse_key(
    track: list[list[DjvuLine]],
    text: list[list[DjvuLine]] | None = None,
    track_heights: list[float] | None = None,
    text_heights: list[float] | None = None,
) -> list[AnswerList]:
    """Return every numbered Hebrew answer list (parts B/C/D), in order.

    ``track`` supplies the §/part markers and running heads (the DjVu export
    reads those reliably); ``text`` supplies the Hebrew glyphs (the tesseract
    heb+eng pass reads those far better). Rows are matched between the two
    sources by their y coordinates, so only the answer rows of the right part
    feed the phrase extraction.
    """
    if text is None:
        text = track
    section = 1
    part = ""
    buffers: dict[tuple[int, str], list[int]] = {}
    leafs: dict[tuple[int, str], int] = {}
    order: list[tuple[int, str]] = []

    for leaf, lines in enumerate(track):
        if not lines:
            continue
        # The running head names the sections on the page ("§ 12. B-§ 13. A.").
        # Advance to the FIRST name that moves us forward; a bare "§ N." body
        # marker later on the page then advances again, so answers printed
        # before that marker keep the earlier section (e.g. §12 B before "§ 13.").
        head_numbers: list[int] = []
        for line in lines:
            numbers = _head_numbers(line.text)
            if numbers:
                head_numbers = numbers
                break
        has_body_marker = any(
            re.fullmatch(r"[§8S$₪]+\s*([0-9IlOo1Tt][0-9IlOo1Tt ]{0,2})\s*[.,]?\s*", line.text.strip())
            for line in lines
        )
        if not has_body_marker:
            for number in head_numbers:
                if section < number <= section + 3:
                    section = number
                    part = ""
                    break
        for line in lines:
            line_text = line.text.strip()
            if not line_text or line is lines[0]:
                continue
            # Bare section marker.
            bare = re.fullmatch(r"[§8S$₪]+\s*([0-9IlOo1Tt][0-9IlOo1Tt ]{0,2})\s*[.,]?\s*", line_text)
            if bare:
                number = _norm_number(bare.group(1))
                if number is not None and section <= number <= section + 5:
                    section = number
                    part = ""
                continue
            # Bare part letter: B/C/D rows sit below this marker; part-A rows
            # (English answers with Hebrew glosses) sit above it.
            letter = re.fullmatch(r"([A-D])\s*[.,]?\s*", line_text)
            if letter:
                part = letter.group(1)
                continue
            # English answers and footnotes carry no pointing; drop them.
            if len(HEB_CONSONANT_RE.findall(line_text)) < MIN_HEBREW_CONSONANTS:
                continue
            key = (section, part)
            if key not in buffers:
                buffers[key] = []
                leafs[key] = leaf
                order.append(key)
            if leaf not in buffers[key]:
                buffers[key].append(leaf)

    lists: list[AnswerList] = []
    for key in order:
        section, part = key
        if part in ("A", ""):  # only Hebrew answers (parts B/C/D)
            continue
        words: list[tuple[int, DjvuWord]] = []
        for leaf in buffers[key]:
            if leaf >= len(text):
                continue
            for line in text[leaf]:
                hebrew = sum(len(HEB_CONSONANT_RE.findall(w.text)) for w in line.words)
                latin = sum(len(LAT_RE.findall(w.text)) for w in line.words)
                if hebrew < 2 or hebrew / max(1, hebrew + latin) < 0.18:
                    continue
                words.extend((leaf, word) for word in line.words)
        items = _coordinate_answers_words(words)
        if len(items) >= 2:
            lists.append(
                AnswerList(
                    section=section,
                    part=part,
                    leaf=leafs[key],
                    hebrew=[phrase for _, phrase, _ in items],
                    leaves=[answer_leaf for _, _, answer_leaf in items],
                    numbers=[number for number, _, _ in items],
                )
            )
    return lists


def _coordinate_answers_words(
    words: list[tuple[int, DjvuWord]],
) -> list[tuple[int, str, int]]:
    """Segment the answer block's words (y-ordered, RTL per row) into items.

    The OCR reads each RTL row right-to-left: number, phrase, number, phrase.
    Walking the whole block in that order and splitting at the number boxes
    keeps neighbouring answers apart. Where the printed number itself is
    garbled (1 as a Hebrew letter, 10 as ``ro``), the sequence is gap-filled so
    every answer still gets its ordinal position; the printed list restarts at 1
    per part, so the fill starts there.
    """
    ordered = sorted(words, key=lambda item: (item[1].y, -item[1].x0))
    chunks: list[tuple[int | None, list[str], int]] = []
    current_number: int | None = None
    current_words: list[str] = []
    current_leaf = 0
    for leaf, word in ordered:
        marker = _answer_number(word)
        if marker == 0:
            marker = None
        if marker is not None:
            if current_words:
                chunks.append((current_number, current_words, current_leaf))
            current_number = marker
            current_words = []
            current_leaf = leaf
            continue
        if HEB_CONSONANT_RE.search(word.text):
            current_words.append(word.text)
            current_leaf = leaf
    if current_words:
        chunks.append((current_number, current_words, current_leaf))

    used: set[int] = set()
    expected = 1
    items: list[tuple[int, str, int]] = []
    for number, words_in_chunk, leaf in chunks:
        phrase = _clean_answer_words(words_in_chunk)
        if number is not None:
            expected = max(expected, number + 1)
        if not phrase:
            continue
        assigned = number if number is not None else expected
        if number is None:
            expected += 1
        if assigned > 40 or assigned in used:
            continue
        used.add(assigned)
        items.append((assigned, phrase, leaf))
    return sorted(items, key=lambda item: item[0])


def _answer_number(word: DjvuWord) -> int | None:
    """Recognize printed item-number tokens, including common 1/10 OCR glyphs."""
    text = INVISIBLE_RE.sub("", word.text).strip(".,;:|()[]'\"\u2018\u2019")
    if text.isdigit():
        number = int(text)
        return number if 1 <= number <= 40 else None
    if text.lower() in {"ro", "io", "lo", "1o"} and word.x1 - word.x0 <= 60:
        return 10
    # A few digits are OCR'd as narrow letters. Resolve their numeric value
    # against the labels already recovered from this list in _coordinate_answers.
    if word.x1 - word.x0 <= 55 and len(text) == 1 and text in {"ז", "ג", "י", "ו", "l", "I"}:
        return 0
    return None


def _clean_answer_words(words: list[str]) -> str:
    phrase = _hebrew_phrase(" ".join(words))
    tokens = phrase.split()
    if len(tokens) >= 4 and tokens[:2] == tokens[2:][::-1]:
        tokens = tokens[:2]
    return " ".join(tokens)


# ------------------------------------------------------------------- mapping


def unit_sections() -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for path in sorted(CHAPTERS.glob("*.md")):
        unit = int(path.stem)
        text = path.read_text(encoding="utf-8")
        source = re.search(r"^#+\s*Source\s*\n+((?:.+\n?)+?)(?=\n#|\Z)", text, re.M)
        out[unit] = (
            sorted({int(n) for n in re.findall(r"\u00a7+\s*(\d{1,2})", source.group(1))})
            if source
            else []
        )
    return out


@dataclass
class Record:
    unit: int
    section: int
    part: str
    prompt: str
    answer: str
    grammar_leaf: int
    key_leaf: int
    item: dict


def strip_niqqud(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if 0x0591 <= code <= 0x05C7 and code not in (0x05C1, 0x05C2):
            continue
        if ch not in "\u05be\u05f3\u05f4":
            out.append(ch)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def source_block(section: int, part: str, grammar_leaf: int, answer_leaf: int) -> dict:
    return {
        "citation": (
            f"Davidson, Introductory Hebrew Grammar (22nd ed.) exercise on "
            f"\u00a7{section}; Key to the Exercises (1924) \u00a7{section}"
            f"{(' ' + part) if part else ''}"
        ),
        "promptUrl": scan_url(GRAMMAR_ITEM, grammar_leaf),
        "promptImageUrl": f"https://archive.org/download/{GRAMMAR_ITEM}/page/n{grammar_leaf}.jpg",
        "answerUrl": scan_url(KEY_ITEM, answer_leaf),
        "answerImageUrl": f"https://archive.org/download/{KEY_ITEM}/page/n{answer_leaf}.jpg",
        "note": "Read from the scans by OCR; open them if a reading looks wrong.",
    }


def typed_item(english: str, hebrew: str, source: dict) -> dict:
    accepted = [hebrew]
    unpointed = strip_niqqud(hebrew)
    if unpointed and unpointed != hebrew:
        accepted.append(unpointed)
    return {
        "type": "translate-phrase",
        "prompt": "Translate this English sentence into Hebrew",
        "stimulus": english,
        "stimulusIsScript": False,
        "accepted": accepted,
        "answerIsScript": True,
        "source": source,
    }


def build_records() -> tuple[list[Record], dict]:
    vision_grammar = load_vision(SOURCES / "grammar-vision-en.json")
    djvu_key = load_djvu(SOURCES / "key-1924-djvu.xml")

    exercises = parse_grammar(vision_grammar)
    answer_lists = parse_key(djvu_key)

    units = unit_sections()
    sections_to_units: dict[int, list[int]] = defaultdict(list)
    for unit, sections in units.items():
        for section in sections:
            sections_to_units[section].append(unit)
    for section in sections_to_units:
        sections_to_units[section].sort()

    records: list[Record] = []
    for exercise in exercises:
        section = exercise.section
        if section == 0:
            continue
        targets = sections_to_units.get(section)
        if not targets:
            continue
        candidate = [a for a in answer_lists if a.section == section]
        if not candidate:
            continue
        # Closest count wins, then the first (B before C before D).
        answer = min(candidate, key=lambda a: abs(len(a.hebrew) - len(exercise.english)))
        answer_by_number = {
            number: (hebrew, answer.leaves[index] if index < len(answer.leaves) else answer.leaf)
            for index, (number, hebrew) in enumerate(zip(answer.numbers, answer.hebrew))
        }

        for index, prompt in enumerate(exercise.english):
            matched = answer_by_number.get(index + 1)
            if not matched:
                continue
            hebrew, answer_leaf = matched
            unit = targets[index % len(targets)]
            source = source_block(section, answer.part, exercise.leaf, answer_leaf)
            records.append(
                Record(
                    unit=unit,
                    section=section,
                    part=answer.part,
                    prompt=prompt,
                    answer=hebrew,
                    grammar_leaf=exercise.leaf,
                    key_leaf=answer_leaf,
                    item=typed_item(prompt, hebrew, source),
                )
            )

    grouped = group_by_unit(records)
    stats = {
        "grammarExercises": len(exercises),
        "answerLists": len(answer_lists),
        "candidateRecords": len(records),
        "records": sum(len(items) for items in grouped.values()),
        "unitsWithItems": len(grouped),
        "exercisesSections": sorted({e.section for e in exercises}),
        "answerSections": sorted({a.section for a in answer_lists}),
    }
    return records, stats


def group_by_unit(records: list[Record]) -> dict[int, list[Record]]:
    grouped: dict[int, list[Record]] = defaultdict(list)
    for record in records:
        grouped[record.unit].append(record)
    return dict(grouped)


# ------------------------------------------------------------------- writers


def write_outputs(records: list[Record], stats: dict) -> None:
    grouped = group_by_unit(records)
    exercises_dir = COURSE / "exercises"
    authored_dir = COURSE / "authored"
    exercises_dir.mkdir(exist_ok=True)
    authored_dir.mkdir(exist_ok=True)
    _remove_stale_generated_outputs(grouped, exercises_dir, authored_dir)

    for unit, recs in sorted(grouped.items()):
        name = f"{unit:02d}.json"
        scaffolds = {
            "schema": "workbook-exercises-v1.json",
            "unit": unit,
            "items": [
                {
                    "unit": unit,
                    "n": i,
                    "typeGuess": record.item["type"],
                    "confidence": 0.5,
                    "prompt": record.item["prompt"],
                    "body_raw": record.prompt,
                    "answer_raw": record.answer,
                }
                for i, record in enumerate(recs, start=1)
            ],
        }
        (exercises_dir / name).write_text(
            json.dumps(scaffolds, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (authored_dir / name).write_text(
            json.dumps(
                {
                    "schema": "authored-exercises-v1.json",
                    "unit": unit,
                    "items": [record.item for record in recs],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    inventory = {
        "schema": "davidson-exercise-inventory-v1.json",
        "generatedBy": "build/recover_davidson_exercises.py",
        "stats": stats,
        "units": [
            {
                "unit": unit,
                "items": [
                    {
                        "section": record.section,
                        "part": record.part,
                        "prompt": record.prompt,
                        "answer": record.answer,
                        "type": record.item["type"],
                        "grammarLeaf": record.grammar_leaf,
                        "keyLeaf": record.key_leaf,
                        "promptUrl": record.item["source"]["promptUrl"],
                        "answerUrl": record.item["source"]["answerUrl"],
                    }
                    for record in recs
                ],
            }
            for unit, recs in sorted(grouped.items())
        ],
    }
    (SOURCES / "exercise-inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    emitted = sum(len(items) for items in grouped.values())
    print(
        f"wrote inventory + {len(grouped)} unit files "
        f"({emitted} items; no per-unit cap)"
    )


def _remove_stale_generated_outputs(
    grouped: dict[int, list[Record]], exercises_dir: Path, authored_dir: Path
) -> None:
    """Remove only paired stale files that still exactly match our generated shape."""
    for authored_path in authored_dir.glob("[0-9][0-9].json"):
        unit = int(authored_path.stem)
        if unit in grouped:
            continue
        exercises_path = exercises_dir / authored_path.name
        if not exercises_path.is_file():
            continue
        try:
            authored = json.loads(authored_path.read_text(encoding="utf-8"))
            scaffolds = json.loads(exercises_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        items = authored.get("items", [])
        raw_items = scaffolds.get("items", [])
        if (
            authored.get("schema") != "authored-exercises-v1.json"
            or scaffolds.get("schema") != "workbook-exercises-v1.json"
            or authored.get("unit") != unit
            or scaffolds.get("unit") != unit
            or not items
            or len(items) != len(raw_items)
        ):
            continue
        is_ours = all(
            item.get("source", {}).get("note")
            == "Read from the scans by OCR; open them if a reading looks wrong."
            and raw.get("body_raw") == item.get("stimulus")
            and raw.get("answer_raw") == item.get("accepted", [None])[0]
            for item, raw in zip(items, raw_items)
        )
        if is_ours:
            authored_path.unlink()
            exercises_path.unlink()


def report(records: list[Record], stats: dict) -> None:
    print("== grammar exercises ==")
    vision = load_vision(SOURCES / "grammar-vision-en.json")
    for e in parse_grammar(vision):
        print(f"  \u00a7{e.section:<3} leaf{e.leaf:>4} en={len(e.english):>2} | {e.english[0][:55]}")

    print("\n== key answer lists (Hebrew parts) ==")
    for a in parse_key(load_djvu(SOURCES / "key-1924-djvu.xml")):
        print(f"  \u00a7{a.section:<3} {a.part} n={len(a.hebrew):>2} | {' | '.join(a.hebrew[:5])}")

    print("\n== stats ==")
    for name, value in stats.items():
        print(f"  {name}: {value}")

    grouped = group_by_unit(records)
    print(f"\n== units with items: {len(grouped)} ==")
    for unit in sorted(grouped):
        recs = grouped[unit]
        print(f"  u{unit:02d} n={len(recs):>2}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    records, stats = build_records()
    if args.report or not args.write:
        report(records, stats)
    if args.write:
        sys.exit("--write is retired: course drills now come from the curated exwb set "
                 "(python build/exwb_to_authored.py --course courses/biblical-hebrew-davidson, P9-T6)")


if __name__ == "__main__":
    main()
