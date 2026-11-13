"""Greek profile of the exercise ladder (ROADMAP P11, ADR-025).

Plugs into `ladder_core.ladder`: rung 5 is "translate with full accents"; rung 4 typed Greek is graded by the
engine on letters + breathings + iota subscript (`engine/script.js`). Fill-in blanks one of the longer words.
Alternatives for rung 5 are the book's spellings when they differ from the SBLGNT forms (passed in by the builder).
"""

from __future__ import annotations

import random
import re

import greek_text as G
from ladder_core import ladder as core_ladder

TRAIL = re.compile(r"[.,;:·;!?]+$")


class GreekProfile:
    name = "Greek"
    marks = "accents"
    to_english = "gr-en"

    def __init__(self, alternatives: dict[str, list[str]] | None = None):
        self.alt = alternatives or {}

    def blank_sentence(self, text: str, rng: random.Random) -> tuple[str, str] | None:
        parts = re.split(r"(\s+)", text.strip())
        greek = [i for i, p in enumerate(parts) if G.GREEK_LETTER.search(p)]
        idxs = [i for i in greek if len(G.bare(TRAIL.sub("", parts[i]))) >= 3]
        if len(greek) < 2 or not idxs:
            return None
        idxs.sort(key=lambda i: -len(G.bare(parts[i])))
        i = rng.choice(idxs[:3])
        word = TRAIL.sub("", parts[i])
        parts[i] = parts[i].replace(word, "＿＿＿")
        return "".join(parts), word

    def is_marked(self, text: str) -> bool:
        return G.has_accents(text)

    def alternatives(self, text: str) -> list[str]:
        return list(self.alt.get(text, []))


def ladder(base: str, greek: list[str], english: str, english_pool: list[str], direction: str, rng: random.Random,
           extra: dict, reading: str | None = None, hint: str | None = None,
           alternatives: dict[str, list[str]] | None = None) -> list[dict]:
    return core_ladder(GreekProfile(alternatives), base, greek, english, english_pool, direction, rng, extra, reading, hint)
