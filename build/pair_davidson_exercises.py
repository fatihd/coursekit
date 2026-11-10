"""Pair the grammar exercise prompts with the 1924 key answers and emit drills.

Joins the two inventories on § + part + item number, scores every
prompt-answer pair with a lexical sanity check (course vocabulary glosses for
translation pairs, consonant patterns for transliteration pairs), re-assigns
pairs that score as mis-paired, and emits engine-consumable authored items per
course unit with scan links on both sides.

    python build/pair_davidson_exercises.py            # report only

Report only: the course drills now come from the hand-checked exwb set
(build/exwb_to_authored.py, ROADMAP P9-T6); --write is retired.

Mappings:
  * translation B (English prompt -> key Hebrew answer): translate-phrase,
    typed Hebrew, niqqud-insensitive.
  * translation A (grammar Hebrew prompt -> key English answer): mcq over the
    section's English answers (identity grading), translate-phrase fallback.
  * transliteration lists (grammar Hebrew word -> key transliteration): mcq.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))

import recover_davidson_exercises as recover  # noqa: E402

SOURCES = ROOT / "build" / "_sources" / "davidson"
COURSE = ROOT / "courses" / "biblical-hebrew-davidson"

NIQQUD_RE = re.compile(r"[\u0591-\u05c7]")
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "to", "for", "with", "is", "are",
    "was", "were", "be", "am", "art", "i", "we", "ye", "thou", "thee", "he", "she",
    "it", "they", "them", "his", "her", "my", "thy", "your", "our", "their", "all",
    "this", "that", "these", "those", "not", "no", "so", "as", "by", "from", "upon",
}
TRANSLIT_HEB = {
    "א": "'", "ב": "b", "ג": "g", "ד": "d", "ה": "h", "ו": "w", "ז": "z",
    "ח": "h", "ט": "t", "י": "y", "כ": "k", "ל": "l", "מ": "m", "נ": "n",
    "ס": "s", "ע": "'", "פ": "p", "צ": "c", "ק": "q", "ר": "r", "ש": "sS",
    "ת": "t",
}
VOWELS = set("aeiou")
# Davidson's glosses and the course vocabulary differ in wording; these classes
# collapse the frequent equivalents so a correct pair is not scored as wrong.
SYNONYM_CLASSES: list[set[str]] = [
    {"firmament", "expanse"},
    {"water", "waters"},
    {"earth", "land", "ground"},
    {"heaven", "heavens", "sky"},
    {"ass", "donkey"},
    {"cattle", "kine"},
    {"high", "lofty"},
    {"word", "words"},
    {"people", "folk"},
    {"man", "men"},
    {"woman", "women"},
    {"city", "town"},
    {"soul", "life"},
    {"sea", "seas"},
    {"mountain", "mountains", "hill", "hills"},
    {"great", "big"},
]
_WORD_CLASS: dict[str, str] = {}
for _class in SYNONYM_CLASSES:
    for _word in _class:
        _WORD_CLASS[_word] = min(_class)


def class_word(word: str) -> str:
    return _WORD_CLASS.get(word, word)


def unpoint(text: str) -> str:
    return "".join(char for char in text if not NIQQUD_RE.match(char)).replace("\u05be", " ")


def strip_niqqud(text: str) -> str:
    return recover.strip_niqqud(text)


def _letters(text: str) -> list[str]:
    return [char for char in unicodedata.normalize("NFKD", text) if char.isalpha()]


def english_content_words(text: str) -> list[str]:
    words: list[str] = []
    for token in re.split(r"[^A-Za-z']+", text.lower()):
        if token and token not in STOPWORDS:
            words.append(class_word(token))
    return words


def build_lexicon(vocab_items: list[dict]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """unpointed scriptForm -> gloss words; 3-consonant stem -> gloss words."""
    exact: dict[str, set[str]] = {}
    stems: dict[str, set[str]] = {}
    for item in vocab_items:
        key = unpoint(item["scriptForm"]).strip().translate(FINAL_FORMS)
        gloss_words = {
            class_word(word) for word in re.split(r"[\s,;]+", item["gloss"].lower()) if word
        }
        if not key:
            continue
        exact.setdefault(key, set()).update(gloss_words)
        consonants = [char for char in key if "\u05d0" <= char <= "\u05ea"]
        stem = "".join(consonants[:3]) if len(consonants) >= 3 else "".join(consonants)
        if stem:
            stems.setdefault(stem, set()).update(gloss_words)
    return exact, stems


FINAL_FORMS = str.maketrans({"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"})
PREFIXES = "הובלמכש"


def gloss_of_hebrew(word: str, exact: dict, stems: dict) -> set[str]:
    key = unpoint(word).strip(" .,;:()[]'\"\u2018\u2019").translate(FINAL_FORMS)
    candidates = [key]
    stripped = key
    while len(stripped) > 2 and stripped[0] in PREFIXES:
        stripped = stripped[1:]
        candidates.append(stripped)
    for candidate in candidates:
        if candidate in exact:
            return exact[candidate]
    for candidate in candidates:
        consonants = [char for char in candidate if "\u05d0" <= char <= "\u05ea"]
        stem = "".join(consonants[:3]) if len(consonants) >= 3 else "".join(consonants)
        if stem and stem in stems:
            return stems[stem]
    return set()


def translation_score(english: str, hebrew: str, lexicon) -> float:
    exact, stems = lexicon
    words = english_content_words(english)
    if not words:
        return 0.0
    covered: set[str] = set()
    for token in hebrew.split():
        gloss = gloss_of_hebrew(token, exact, stems)
        for word in words:
            if word in gloss or (len(word) > 3 and any(word.startswith(g) for g in gloss if len(g) >= 4)):
                covered.add(word)
    return len(covered) / len(words)


def transliteration_score(hebrew: str, translit: str) -> float:
    heb_consonants = [char for char in unpoint(hebrew) if "\u05d0" <= char <= "\u05ea"]
    latin = [
        char
        for char in _letters(translit.replace("sh", "S"))
        if char.casefold() not in VOWELS and char not in "'’"
    ]
    if not heb_consonants or not latin:
        return 0.0
    matched = 0
    used: list[bool] = [False] * len(latin)
    for char in heb_consonants:
        for index, letter in enumerate(latin):
            if not used[index] and letter in TRANSLIT_HEB.get(char, char):
                used[index] = True
                matched += 1
                break
    return matched / len(heb_consonants)


def tier(score: float) -> str:
    if score >= 0.34:
        return "ok"
    if score >= 0.15:
        return "weak"
    return "suspect"


def assign_pairs(
    prompts: list[dict],
    answers: list[dict],
    score_fn,
    base: dict[int, int],
    fallback_unmatched: bool = True,
) -> list[tuple[int, int, float]]:
    """Greedy assignment that keeps numbered pairs when they score decently.

    With ``fallback_unmatched`` disabled, a prompt whose printed number has no
    answer is left unpaired rather than grabbing a wrong answer.
    """
    matrix = {
        (i, j): score_fn(prompts[i], answers[j])
        for i in range(len(prompts))
        for j in range(len(answers))
    }
    used: set[int] = set()
    result: list[tuple[int, int, float]] = []
    order = sorted(
        range(len(prompts)),
        key=lambda i: -(matrix.get((i, base.get(i, -1)), -1.0)),
    )
    for i in order:
        base_j = base.get(i)
        if base_j is None and not fallback_unmatched:
            continue
        if base_j is not None and base_j not in used and matrix.get((i, base_j), -1.0) >= 0.15:
            chosen = base_j
        elif base_j is None:
            candidates = [j for j in range(len(answers)) if j not in used]
            chosen = max(candidates, key=lambda j: matrix.get((i, j), -1.0)) if candidates else None
        else:
            candidates = [j for j in range(len(answers)) if j not in used]
            chosen = max(candidates, key=lambda j: matrix.get((i, j), -1.0)) if candidates else None
        if chosen is None:
            continue
        used.add(chosen)
        result.append((i, chosen, matrix.get((i, chosen), 0.0)))
    return sorted(result, key=lambda pair: pair[0])


def load_inventories() -> tuple[list[dict], list[dict], list[dict]]:
    grammar = json.loads((SOURCES / "grammar-exercise-inventory.json").read_text(encoding="utf-8"))
    answers = json.loads((SOURCES / "key-answer-inventory.json").read_text(encoding="utf-8"))
    vocab = json.loads((COURSE / "vocab.json").read_text(encoding="utf-8"))
    return grammar["blocks"], answers["items"], vocab["items"]


def key_answers_by_section(answers: list[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    for item in answers:
        grouped[item["section"]].append(item)
    return {section: sorted(items, key=lambda i: (i["part"], i["number"] or 0)) for section, items in grouped.items()}


def pair_side(
    section: int,
    prompts: list[dict],
    answers: list[dict],
    score_fn,
    numbered: bool,
) -> list[tuple[dict, dict, float]]:
    if not prompts or not answers:
        return []
    base: dict[int, int] = {}
    if numbered:
        answer_by_number = {item["number"]: index for index, item in enumerate(answers) if item["number"]}
        for i, prompt in enumerate(prompts):
            if prompt.get("number") in answer_by_number:
                base[i] = answer_by_number[prompt["number"]]
        pairs = assign_pairs(prompts, answers, score_fn, base, fallback_unmatched=True)
    else:
        base = {i: i for i in range(min(len(prompts), len(answers)))}
        pairs = assign_pairs(prompts, answers, score_fn, base)
    return [
        (prompts[i], answers[j], score)
        for i, j, score in pairs
        if answers[j]["text"].strip()
    ]


def source_block(section: int, prompt_leaf: int, answer_leaf: int, score: float) -> dict:
    return {
        "citation": (
            f"Davidson, Introductory Hebrew Grammar (22nd ed.) exercise on \u00a7{section}; "
            f"Key to the Exercises (1924) \u00a7{section}"
        ),
        "promptUrl": f"https://archive.org/details/introductoryhebr0000davi_w1b2/page/n{prompt_leaf}/mode/1up",
        "promptImageUrl": f"https://archive.org/download/introductoryhebr0000davi_w1b2/page/n{prompt_leaf}.jpg",
        "answerUrl": f"https://archive.org/details/keytoexercisesin0000mcfa/page/n{answer_leaf}/mode/1up",
        "answerImageUrl": f"https://archive.org/download/keytoexercisesin0000mcfa/page/n{answer_leaf}.jpg",
        "sanityScore": round(score, 2),
        "sanity": tier(score),
        "note": "Read from the scans by OCR; open them if a reading looks wrong.",
    }


def build_pairs() -> tuple[list[dict], dict]:
    blocks, answers, vocab_items = load_inventories()
    lexicon = build_lexicon(vocab_items)
    by_section = key_answers_by_section(answers)
    units = recover.unit_sections()
    sections_to_units: dict[int, list[int]] = defaultdict(list)
    for unit, sections in units.items():
        for section in sections:
            sections_to_units[section].append(unit)

    pairs: list[dict] = []
    for block in blocks:
        section = block["section"]
        if not section:
            continue
        prompt_leaf = block["promptLeaf"]
        key_items = by_section.get(section, [])
        english_answers = [item for item in key_items if item["script"] == "en"]
        hebrew_answers = [item for item in key_items if item["script"] == "he"]
        kind = block["kindGuess"]

        # Translation B: English prompt -> key Hebrew answer (typed Hebrew).
        # Pair by the printed item number, not by list position: a list that
        # lost its leading items must not shift every later prompt onto the
        # wrong answer.
        if kind == "translation" and hebrew_answers:
            english_prompts = [
                {"number": index + 1, "text": item["text"]}
                for index, item in enumerate(block["englishItems"])
            ]
            for prompt, answer, score in pair_side(
                section,
                english_prompts,
                hebrew_answers,
                lambda p, a: translation_score(p["text"], a["text"], lexicon),
                numbered=True,
            ):
                pairs.append(
                    {
                        "direction": "en->he",
                        "section": section,
                        "part": answer["part"],
                        "number": answer["number"],
                        "prompt": prompt["text"],
                        "answer": answer["text"],
                        "promptLeaf": prompt_leaf,
                        "answerLeaf": answer["leaf"],
                        "score": score,
                        "sanity": tier(score),
                    }
                )

        # Translation A: grammar Hebrew prompt -> key English answer (mcq).
        if english_answers and block["hebrewItems"] and kind in ("translation", "parsing"):
            hebrew_prompts = [
                {"number": item.get("number"), "text": item["text"]}
                for item in block["hebrewItems"]
                if item.get("number") is not None
            ]
            if not hebrew_prompts:
                hebrew_prompts = [
                    {"number": None, "text": item["text"]}
                    for item in block["hebrewItems"][: len(english_answers)]
                ]
            for prompt, answer, score in pair_side(
                section,
                hebrew_prompts,
                english_answers,
                lambda p, a: translation_score(a["text"], p["text"], lexicon),
                numbered=True,
            ):
                pairs.append(
                    {
                        "direction": "he->en",
                        "section": section,
                        "part": answer["part"],
                        "number": answer["number"],
                        "prompt": prompt["text"],
                        "answer": answer["text"],
                        "promptLeaf": prompt_leaf,
                        "answerLeaf": answer["leaf"],
                        "score": score,
                        "sanity": tier(score),
                    }
                )

        # Transliteration lists: grammar Hebrew word -> key transliteration (mcq).
        if (
            kind in ("writing", "transliteration", "pronunciation")
            and english_answers
            and block["hebrewItems"]
        ):
            hebrew_prompts = [
                {"number": None, "text": item["text"]}
                for item in block["hebrewItems"]
                if len(unpoint(item["text"])) >= 2
            ]
            for prompt, answer, score in pair_side(
                section,
                hebrew_prompts,
                english_answers,
                lambda p, a: transliteration_score(p["text"], a["text"]),
                numbered=False,
            ):
                if score >= 0.4:
                    pairs.append(
                        {
                            "direction": "translit",
                            "section": section,
                            "part": answer["part"],
                            "number": None,
                            "prompt": prompt["text"],
                            "answer": answer["text"],
                            "promptLeaf": prompt_leaf,
                            "answerLeaf": answer["leaf"],
                            "score": score,
                            "sanity": tier(score),
                        }
                    )

    stats = {
        "pairs": len(pairs),
        "byTier": {
            label: sum(1 for pair in pairs if tier(pair["score"]) == label)
            for label in ("ok", "weak", "suspect")
        },
        "byDirection": {
            direction: sum(1 for pair in pairs if pair["direction"] == direction)
            for direction in ("en->he", "he->en", "translit")
        },
    }
    return pairs, stats


def item_for(pair: dict, all_english: dict[int, list[str]]) -> dict:
    source = source_block(pair["section"], pair["promptLeaf"], pair["answerLeaf"], pair["score"])
    if pair["direction"] == "en->he":
        accepted = [pair["answer"]]
        unpointed = strip_niqqud(pair["answer"])
        if unpointed and unpointed != pair["answer"]:
            accepted.append(unpointed)
        return {
            "type": "translate-phrase",
            "prompt": "Translate this English sentence into Hebrew",
            "stimulus": pair["prompt"],
            "stimulusIsScript": False,
            "accepted": accepted,
            "answerIsScript": True,
            "source": source,
        }
    if pair["direction"] == "he->en":
        options = [pair["answer"]]
        for other in all_english.get(pair["section"], []):
            if other != pair["answer"] and other not in options:
                options.append(other)
            if len(options) >= 4:
                break
        if len(options) >= 2:
            return {
                "type": "mcq",
                "prompt": "Translate this Hebrew sentence into English",
                "stimulus": pair["prompt"],
                "stimulusIsScript": True,
                "options": options,
                "answer": pair["answer"],
                "optionIsScript": False,
                "source": source,
            }
        return {
            "type": "translate-phrase",
            "prompt": "Translate this Hebrew sentence into English",
            "stimulus": pair["prompt"],
            "stimulusIsScript": True,
            "accepted": [pair["answer"]],
            "answerIsScript": False,
            "source": source,
        }
    options = [pair["answer"]]
    for other in all_english.get(pair["section"], []):
        if other != pair["answer"] and other not in options:
            options.append(other)
        if len(options) >= 4:
            break
    if len(options) >= 2:
        return {
            "type": "mcq",
            "prompt": "Which transliteration matches this Hebrew word?",
            "stimulus": pair["prompt"],
            "stimulusIsScript": True,
            "options": options,
            "answer": pair["answer"],
            "optionIsScript": False,
            "source": source,
        }
    return {
        "type": "translit-normalize",
        "direction": "script->translit",
        "prompt": "Transliterate this Hebrew word into Latin script",
        "stimulus": pair["prompt"],
        "stimulusIsScript": True,
        "answer": pair["answer"],
        "answerIsScript": False,
        "source": source,
    }


def write_outputs(pairs: list[dict], stats: dict) -> None:
    _, answers, _ = load_inventories()
    all_english: dict[int, list[str]] = defaultdict(list)
    for item in answers:
        if item["script"] == "en":
            all_english[item["section"]].append(item["text"])

    units = recover.unit_sections()
    sections_to_units: dict[int, list[int]] = defaultdict(list)
    for unit, sections in units.items():
        for section in sections:
            sections_to_units[section].append(unit)

    per_unit: dict[int, list[tuple[dict, dict]]] = defaultdict(list)
    for pair in pairs:
        if tier(pair["score"]) == "suspect":
            # Recorded in the ledger, but not emitted as a graded drill.
            continue
        item = item_for(pair, all_english)
        targets = sections_to_units.get(pair["section"])
        if not targets:
            continue
        for unit in targets:
            per_unit[unit].append((pair, item))

    authored_dir = COURSE / "authored"
    exercises_dir = COURSE / "exercises"
    authored_dir.mkdir(exist_ok=True)
    exercises_dir.mkdir(exist_ok=True)
    _remove_stale_outputs(per_unit, authored_dir, exercises_dir)

    emitted = 0
    for unit, records in sorted(per_unit.items()):
        name = f"{unit:02d}.json"
        (authored_dir / name).write_text(
            json.dumps(
                {
                    "schema": "authored-exercises-v1.json",
                    "unit": unit,
                    "items": [item for _, item in records],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (exercises_dir / name).write_text(
            json.dumps(
                {
                    "schema": "workbook-exercises-v1.json",
                    "unit": unit,
                    "items": [
                        {
                            "unit": unit,
                            "n": index,
                            "typeGuess": item["type"],
                            "confidence": 0.5,
                            "prompt": item.get("prompt", ""),
                            "body_raw": pair["prompt"],
                            "answer_raw": pair["answer"],
                        }
                        for index, (pair, item) in enumerate(records, start=1)
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        emitted += len(records)

    (SOURCES / "pair-inventory.json").write_text(
        json.dumps(
            {
                "schema": "davidson-pair-inventory-v1.json",
                "generatedBy": "build/pair_davidson_exercises.py",
                "stats": stats,
                "pairs": sorted(
                    pairs,
                    key=lambda pair: (pair["section"], pair["direction"], pair["number"] or 0),
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote pair inventory + authored/exercises for {len(per_unit)} units "
        f"({emitted} items across all units; pairs can appear in several units)"
    )


def _remove_stale_outputs(
    per_unit: dict[int, list], authored_dir: Path, exercises_dir: Path
) -> None:
    """Remove only stale files that still match our generated shape."""
    for authored_path in authored_dir.glob("[0-9][0-9].json"):
        unit = int(authored_path.stem)
        if unit in per_unit:
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
            and raw.get("answer_raw") == (
                item.get("accepted", [None])[0] if "accepted" in item else item.get("answer")
            )
            for item, raw in zip(items, raw_items)
        )
        if is_ours:
            authored_path.unlink()
            exercises_path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="emit authored items and ledger")
    args = parser.parse_args()
    pairs, stats = build_pairs()
    print(f"Pairs: {stats['pairs']}")
    print(f"  by tier: {stats['byTier']}")
    print(f"  by direction: {stats['byDirection']}")
    for label in ("ok", "weak", "suspect"):
        samples = [p for p in pairs if tier(p["score"]) == label][:6]
        print(f"\n  {label} samples:")
        for pair in samples:
            print(f"    \u00a7{pair['section']} {pair['direction']} "
                  f"'{pair['prompt'][:40]}' -> '{pair['answer'][:34]}' ({pair['score']:.2f})")
    if args.write:
        sys.exit("--write is retired: course drills now come from the curated exwb set "
                 "(python build/exwb_to_authored.py --course courses/biblical-hebrew-davidson, P9-T6)")


if __name__ == "__main__":
    main()
