"""Hebrew profile of the exercise ladder and the Davidson entry point (ROADMAP P12-T2/T3/T4, P11).

The ladder itself is `ladder_core.ladder`; this module supplies what is Hebrew about it: pointed
and unpointed forms, blanking a word, and pausal/contextual alternatives for a sentence-final
word. `ladder(...)` keeps the signature `build/exwb_to_authored.py` has always used.
"""

from __future__ import annotations

import random
import re
import unicodedata
from collections import Counter, defaultdict

from ladder_core import (  # noqa: F401
    RUNG_KEYS,
    RUNG_NAMES,
    archaic_verbs,
    clean_display,
    english_variants,
    modernize,
    mutations,
    phrase_mutations,
    pick_distractors,
    rung_names,
)
from ladder_core import ladder as core_ladder

HEB = re.compile(r"[א-ת]")
POINTS = re.compile(r"[ְ-ׇּׁׂ]")
ACCENTS = re.compile(r"[֑-ֽֿ֯׀׃-׆]")


def strip_accents(s: str) -> str:
    return ACCENTS.sub("", unicodedata.normalize("NFC", s))


def consonants(s: str) -> str:
    return re.sub(r"[^א-ת]", "", s).translate(str.maketrans("ךםןףץ", "כמנפצ"))


def is_pointed(s: str) -> bool:
    letters = len(HEB.findall(s))
    return letters > 0 and len(POINTS.findall(s)) >= max(1, letters // 3)


def hebrew_words(s: str) -> list[str]:
    return [w for w in re.split(r"[\s־]+", strip_accents(s)) if HEB.search(w)]


def clusters(word: str) -> list[tuple[str, frozenset]]:
    out: list[tuple[str, set]] = []
    for ch in unicodedata.normalize("NFD", word):
        if HEB.match(ch):
            out.append((ch, set()))
        elif out and "\u05b0" <= ch <= "\u05c7":
            out[-1][1].add(ch)
    return [(b, frozenset(m)) for b, m in out]


def pausal_pair(pausal: str, context: str) -> bool:
    """True if `context` is `pausal` with its one lengthened vowel (qamets) short again."""
    a, b = clusters(pausal), clusters(context)
    if len(a) != len(b) or any(x[0] != y[0] for x, y in zip(a, b)):
        return False
    diffs = [(i, x[1], y[1]) for i, (x, y) in enumerate(zip(a, b)) if x[1] != y[1]]
    if len(diffs) != 1 or diffs[0][0] == 0:
        return False
    _, pa, ca = diffs[0]
    return pa - ca == {"\u05b8"} and len(ca - pa) == 1 and (ca - pa) <= {"\u05b7", "\u05b6"}


class PausalForms:
    """Contextual form of a sentence-final word, from the same word met mid-sentence elsewhere."""

    def __init__(self, sentences: list[str]):
        mid: dict[str, Counter] = defaultdict(Counter)
        for s in sentences:
            words = hebrew_words(s)
            for w in words[:-1]:
                mid[consonants(w)][w] += 1
        self.mid = mid

    def contextual(self, sentence: str) -> str | None:
        words = re.split(r"(\s+|־)", strip_accents(sentence).strip())
        idx = max((i for i, w in enumerate(words) if HEB.search(w)), default=None)
        if idx is None:
            return None
        last = re.sub(r"[^א-תְ-ׇ]", "", words[idx])
        forms = self.mid.get(consonants(last))
        if not forms or last in forms:
            return None
        matches = [f for f, _ in forms.most_common() if pausal_pair(last, f)]
        if not matches:
            return None
        best = matches[0]
        words[idx] = words[idx].replace(last, best)
        return "".join(words)


def blank_sentence(hebrew: str, rng: random.Random) -> tuple[str, str] | None:
    parts = re.split(r"(\s+)", strip_accents(hebrew).strip())
    idxs = [i for i, p in enumerate(parts) if len(consonants(p)) >= 2]
    if len([p for p in parts if HEB.search(p)]) < 2 or not idxs:
        return None
    idxs.sort(key=lambda i: -len(consonants(parts[i])))
    i = rng.choice(idxs[:3])
    word = re.sub(r"[.,;:!?]+$", "", parts[i])
    parts[i] = parts[i].replace(word, "＿＿＿")
    return "".join(parts), word


class HebrewProfile:
    name = "Hebrew"
    marks = "vowel points"
    to_english = "he-en"

    def __init__(self, pausal: PausalForms):
        self.pausal = pausal

    def blank_sentence(self, text: str, rng: random.Random) -> tuple[str, str] | None:
        return blank_sentence(text, rng)

    def is_marked(self, text: str) -> bool:
        return is_pointed(text)

    def alternatives(self, text: str) -> list[str]:
        ctx = self.pausal.contextual(text)
        return [ctx] if ctx else []


def ladder(base: str, hebrew: list[str], english: str, english_pool: list[str], direction: str,
           rng: random.Random, pausal: PausalForms, extra: dict, reading: str | None = None,
           hint: str | None = None) -> list[dict]:
    return core_ladder(HebrewProfile(pausal), base, hebrew, english, english_pool, direction, rng, extra, reading, hint)
