"""Tesseract-TSV loaders and Hebrew list segmentation (replaces the DjVu side).

The 400-DPI tesseract ``heb+eng`` pass reads the key's small pointed Hebrew far
better than either Apple Vision or the Internet Archive DjVu export. This module
loads per-page TSV (word boxes + text) and re-implements the numbered-list
segmentation on top of it.
"""

from __future__ import annotations

import re
from pathlib import Path

HEB_CONSONANT_RE = re.compile(r"[\u05d0-\u05ea]")
LAT_RE = re.compile(r"[A-Za-z]")
INVISIBLE_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff\u00ad]")
NUMBER_RE = re.compile(r"^\d{1,2}$")


def load_tsv_page(path: Path) -> list[dict]:
    words: list[dict] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = raw.split("\t")
        if len(fields) < 12 or fields[0] != "5":
            continue
        text = fields[11].strip()
        if not text:
            continue
        try:
            left, top, width, height = (int(fields[6]), int(fields[7]), int(fields[8]), int(fields[9]))
            conf = float(fields[10])
        except ValueError:
            continue
        words.append(
            {
                "x": left,
                "y": top,
                "w": width,
                "h": height,
                "conf": conf,
                "text": text,
            }
        )
    return words


def lines_of(words: list[dict], y_tol: int = 18) -> list[list[dict]]:
    """Group word boxes into printed lines, top to bottom."""
    ordered = sorted(words, key=lambda word: (word["y"], word["x"]))
    lines: list[list[dict]] = []
    current: list[dict] = []
    current_y: float | None = None
    for word in ordered:
        if current_y is None or abs(word["y"] - current_y) <= y_tol:
            current.append(word)
            current_y = word["y"] if current_y is None else (current_y + word["y"]) / 2
        else:
            lines.append(current)
            current = [word]
            current_y = word["y"]
    if current:
        lines.append(current)
    return lines


def clean_token(token: str) -> str:
    return INVISIBLE_RE.sub("", token).strip(".,;:|()[]'\"\u2018\u2019\u201c\u201d")


def item_number(token: str) -> int | None:
    text = clean_token(token)
    if NUMBER_RE.match(text):
        number = int(text)
        return number if 1 <= number <= 40 else None
    return None


def hebrew_phrase(tokens: list[str]) -> str:
    kept: list[str] = []
    for token in tokens:
        bare = clean_token(token)
        if not bare:
            continue
        if kept and NUMBER_RE.match(bare):
            break
        if HEB_CONSONANT_RE.search(bare):
            if kept and bare == kept[-1]:
                break
            kept.append(bare)
            if len(kept) >= 4:
                break
        elif kept:
            break
    while kept and len(kept[0]) == 1 and kept[0] != "\u05d5" and HEB_CONSONANT_RE.fullmatch(kept[0]):
        kept.pop(0)
    return " ".join(kept)


def numbered_items(line: list[dict]) -> list[tuple[int | None, str]]:
    """Segment one printed line (RTL rows) into (number, Hebrew phrase) items.

    Tesseract emits the row's words in visual order; the printed list runs
    right-to-left, so walk the words from right to left. A number token starts
    an item; the Hebrew run that follows it (further left) is its phrase. The
    leading run before the first number belongs to the number before it (the
    key prints ``N phrase N+1 phrase``), so it is kept with its number.
    """
    words = sorted(line, key=lambda word: word["x"], reverse=True)
    chunks: list[tuple[int | None, list[str]]] = []
    current_number: int | None = None
    current_words: list[str] = []
    for word in words:
        marker = item_number(word["text"])
        if marker is not None:
            if current_words:
                chunks.append((current_number, current_words))
            current_number = marker
            current_words = []
            continue
        if HEB_CONSONANT_RE.search(word["text"]):
            current_words.append(word["text"])
    if current_words:
        chunks.append((current_number, current_words))

    items: list[tuple[int | None, str]] = []
    for index, (number, words_in_chunk) in enumerate(chunks):
        phrase = hebrew_phrase(words_in_chunk)
        if not phrase:
            continue
        if number is None and index == 0 and items:
            continue
        items.append((number, phrase))
    return items


def page_lines(words: list[dict]) -> list[list[dict]]:
    return lines_of(words)


def tesseract_pages(tess_dir: Path, page_count: int):
    """Load tesseract TSV pages in the shape recover.parse_key expects.

    Returns ``(pages, heights)`` where each DjvuLine carries the word tops as y
    and each DjvuWord its own top, in tesseract pixels.
    """
    import recover_davidson_exercises as recover

    pages: list[list[recover.DjvuLine]] = []
    heights: list[float] = []
    for leaf in range(page_count):
        path = tess_dir / f"n{leaf}.tsv"
        if not path.exists():
            pages.append([])
            heights.append(0.0)
            continue
        page_height = 0.0
        lines: list[recover.DjvuLine] = []
        for line in lines_of(load_tsv_page(path)):
            words = [
                recover.DjvuWord(
                    text=word["text"],
                    x0=word["x"],
                    x1=word["x"] + word["w"],
                    y=word["y"],
                )
                for word in line
            ]
            lines.append(
                recover.DjvuLine(
                    text=" ".join(word["text"] for word in line),
                    words=words,
                    y=sum(word.y for word in words) / len(words),
                )
            )
        pages.append(lines)
        heights.append(page_height)
    return pages, heights


def tsv_page_height(path: Path) -> float:
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = raw.split("\t")
        if len(fields) >= 12 and fields[0] == "1":
            try:
                return float(fields[8])
            except ValueError:
                return 0.0
    return 0.0
