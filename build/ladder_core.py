"""Language-neutral core of the exercise ladder (ROADMAP P12-T2/T3/T4, P11; AGENTS.md §0).

Every translation sentence (a text in the course script and its English) becomes five items of
increasing difficulty: 1 true/false, 2 choose the translation, 3 fill in the blank, 4 translate
(typed, marks not checked), 5 translate into the script with full marks (Hebrew vowel points,
Greek accents). Wrong options and false statements are the English with one thing changed
(possessive, article, this/that, a preposition from another group, "not", a subject or object
pronoun), so the original must be read to tell them apart. Typed English is graded against
variants of the English: supplied words in brackets optional, grammar notes dropped, archaic
forms modernized. Everything about the script itself comes from a profile
(`davidson_ladder.HebrewProfile`, `ladder_greek.GreekProfile`).
"""

from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

SCRIPT_LETTER = re.compile(r"[א-ת\u0370-\u03ff\u1f00-\u1fff]")
WORD = re.compile(r"[A-Za-z]+(?:'[a-z]+)?")
RUNG_KEYS = {1: "tf", 2: "choice", 3: "fill", 4: "translate", 5: "pointed"}
RUNG_NAMES = {1: "True or false", 2: "Choose", 3: "Fill in", 4: "Translate", 5: "Translate with vowel points"}


def rung_names(profile) -> dict:
    return {**RUNG_NAMES, 5: f"Translate with {profile.marks}"}

ARCHAIC = {
    "thou": "you", "thee": "you", "ye": "you", "thy": "your", "thine": "your", "thyself": "yourself",
    "art": "are", "hast": "have", "hath": "has", "doth": "does", "dost": "do", "shalt": "shall",
    "wilt": "will", "wast": "were", "canst": "can", "saith": "says", "spake": "spoke", "unto": "to",
}
POSS = {"my": ["your", "his", "our"], "thy": ["my", "his", "your"], "his": ["her", "my", "their"],
        "her": ["his", "my", "their"], "our": ["my", "their", "your"], "your": ["our", "my", "their"],
        "their": ["his", "our", "your"], "thine": ["my", "his", "their"]}
DEMS = {"this": "that", "that": "this", "these": "those", "those": "these"}
PREP_GROUPS = [{"in", "on", "upon", "at"}, {"to", "unto", "toward", "towards"}, {"from"}]
SUBJ = {"i": ["you", "he"], "we": ["they", "you"], "they": ["we", "you"], "he": ["she"], "she": ["he"],
        "thou": ["I", "she"]}
OBJ = {"me": ["him", "us"], "him": ["me", "them"], "us": ["them", "me"], "them": ["us", "him"],
       "thee": ["me", "him"]}
AGREE = {"am", "is", "are", "was", "were", "have", "has", "hast", "hath", "art", "do", "does", "doth", "dost"}
FUNCTION = {"and", "to", "in", "from", "with", "for", "that", "as", "by", "on", "upon", "not", "be", "is",
            "was", "were", "are", "of", "into", "unto", "out", "up", "down", "again", "there"}
DETERMINERS = {"the", "a", "an", "this", "that", "these", "those", "all", "every"} | set(POSS)
OBJ_AFTER_PREP = {"him", "her", "them", "me", "us", "thee", "you", "it", "God", "Yahweh"}


ARCHAIC_VERBS = Path(__file__).resolve().parent / "_sources" / "davidson" / "archaic-verbs.json"


@lru_cache(maxsize=1)
def archaic_verbs() -> dict:
    return json.loads(ARCHAIC_VERBS.read_text(encoding="utf-8"))["verbs"]


def keep_case(src: str, word: str) -> str:
    if src.isupper() and len(src) > 1:
        return word.upper()
    return word[0].upper() + word[1:] if src[0].isupper() else word


# ---------------------------------------------------------------- English variants (grading)

def is_annotation(content: str) -> bool:
    c = content.strip()
    return bool(SCRIPT_LETTER.search(c)) or "." in c or c.lower() in {"m", "f", "sing", "pl", "du"} \
        or c.lower().startswith(("lit", "i.e", "cf", "or "))


SUPPLIED = {"is", "are", "was", "were", "am", "be", "been", "it", "the", "a", "an", "there", "of", "that",
            "which", "who", "he", "she", "they", "him", "them", "his", "her", "its", "to", "and", "i", "we",
            "you", "ye", "thou", "art", "hast", "hath", "shall", "will", "do", "did", "me", "us", "my"}


def tidy(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"\s+([.,;:!?])", r"\1", s)


def paren_variants(text: str) -> list[str]:
    """Readings of a Key sentence: supplied words in brackets kept or dropped, notes removed."""
    t = re.sub(r"\s*\(([^()]*)\)", lambda m: "" if is_annotation(m.group(1)) and "=" not in m.group(1) else m.group(0), text)
    eq = re.compile(r"\(([^()]*?)\s*=\s*\)\s*([A-Za-z-]+)")
    keep_eq = eq.sub(lambda m: m.group(2), t)
    swap_eq = eq.sub(lambda m: m.group(1), t)

    def unwrap(x: str) -> str:
        return re.sub(r"\(([^()]*)\)", r"\1", x)

    def drop(x: str) -> str:
        return re.sub(r"\s*\(([^()]*)\)", lambda m: "" if m.group(1).strip().lower() in SUPPLIED or len(m.group(1).split()) > 1 else m.group(0), x)

    def replace(x: str) -> str:
        return re.sub(r"\b([A-Za-z-]+)\s*\(([A-Za-z-]+)\)",
                      lambda m: m.group(0) if m.group(2).lower() in SUPPLIED else m.group(2), x)

    out: list[str] = []
    for base in (keep_eq, swap_eq):
        for v in (unwrap(base), unwrap(drop(base)), unwrap(replace(base)), unwrap(drop(replace(base)))):
            v = tidy(v)
            if v and v not in out:
                out.append(v)
    return out


def modern_verb(word: str, after_thou: bool) -> str | None:
    low = word.lower()
    modern = archaic_verbs().get(low)
    if not modern or (low.endswith("est") and not after_thou):
        return None
    return keep_case(word, modern)


def modernize(text: str) -> str:
    out, last = [], 0
    thou = False
    for m in WORD.finditer(text):
        w = m.group(0)
        low = w.lower()
        new = keep_case(w, ARCHAIC[low]) if low in ARCHAIC else (modern_verb(w, thou) or w)
        out.append(text[last:m.start()] + new)
        last = m.end()
        if low == "thou":
            thou = True
        elif low in {"and", "but", "for", "that", "if", "when"} or text[m.end():m.end() + 1] in ".;:,":
            thou = False
    return "".join(out) + text[last:]


def english_variants(text: str) -> list[str]:
    out: list[str] = []
    for v in paren_variants(text):
        for w in (v, modernize(v)):
            for x in (w, re.sub(r"\bYahweh\b", "the Lord", w)):
                if x not in out:
                    out.append(x)
    return out[:12]


# ---------------------------------------------------------------- English mutations (distractors)

def tokens(text: str) -> list[tuple[int, int, str, bool]]:
    """Word tokens (start, end, word, in_parens)."""
    out = []
    depth_spans = [(m.start(), m.end()) for m in re.finditer(r"\([^()]*\)", text)]
    for m in WORD.finditer(text):
        inside = any(a <= m.start() < b for a, b in depth_spans)
        out.append((m.start(), m.end(), m.group(0), inside))
    return out


def sentence_start(text: str, pos: int) -> bool:
    before = text[:pos].rstrip()
    return not before or before[-1] in ".:;!?"


def mutations(text: str) -> list[tuple[str, str]]:
    toks = [t for t in tokens(text) if not t[3]]
    out: list[tuple[str, str]] = []

    def put(i: int, new: str, kind: str) -> None:
        a, b, w, _ = toks[i]
        if sentence_start(text, a) or (w[0].isupper() and w.lower() != "i"):
            new = new[0].upper() + new[1:]
        cand = text[:a] + new + text[b:]
        if cand.lower() != text.lower():
            out.append((kind, cand))

    for i, (a, b, w, _) in enumerate(toks):
        low = w.lower()
        nxt = toks[i + 1][2] if i + 1 < len(toks) else None
        nxt_low = nxt.lower() if nxt else None
        if low in POSS:
            if low == "her" and (not nxt or nxt_low in FUNCTION or nxt_low in DETERMINERS):
                continue
            for r in POSS[low]:
                put(i, r, "possessive")
        elif low == "the" and nxt and nxt_low not in DETERMINERS and nxt_low not in FUNCTION:
            if nxt[0].isupper() and not sentence_start(text, a):
                continue
            if nxt_low.endswith("s") and not nxt_low.endswith("ss"):
                word = nxt[0].upper() + nxt[1:] if sentence_start(text, a) else nxt
                out.append(("article", text[:a] + word + text[toks[i + 1][1]:]))
            else:
                put(i, "an" if nxt_low[0] in "aeiou" else "a", "article")
        elif low in {"a", "an"} and nxt and nxt_low not in FUNCTION:
            put(i, "the", "article")
        elif low in DEMS:
            if low == "that" and (not nxt or nxt_low in FUNCTION or nxt_low in {"he", "she", "they", "we", "i", "thou", "ye", "you", "it"}):
                continue
            put(i, DEMS[low], "demonstrative")
        elif any(low in g for g in PREP_GROUPS):
            if not nxt or not (nxt_low in DETERMINERS or nxt in OBJ_AFTER_PREP or nxt[0].isupper()):
                continue
            for g in PREP_GROUPS:
                if low in g:
                    continue
                put(i, next(h for h in ("in", "to", "from") if h in g), "preposition")
        elif low == "not":
            a2 = toks[i - 1][1] if i else a
            cand = text[:a2] + text[b:]
            if cand.lower() != text.lower():
                out.append(("negation", re.sub(r"\s+", " ", cand)))
        elif low in SUBJ and (be := following_be(text, b)):
            for r in SUBJ[low]:
                word = r[0].upper() + r[1:] if sentence_start(text, a) or r == "I" else r
                out.append(("subject", text[:a] + word + " " + be[3] + BE[r.lower()] + text[be[1]:]))
        elif low in SUBJ and (low in {"he", "she"} or (nxt_low and nxt_low not in AGREE
                                                          and not re.search(r"(est|eth)$", nxt_low))):
            if low in {"i", "we", "they"} and i and toks[i - 1][2].lower() in {"to", "from", "with", "for", "by"}:
                continue
            for r in SUBJ[low]:
                put(i, r, "subject")
        elif low in OBJ:
            for r in OBJ[low]:
                put(i, r, "object")
    out += phrase_mutations(text)
    seen, uniq = set(), []
    for kind, cand in out:
        cand = re.sub(r"\s+", " ", cand).strip()
        if cand.lower() not in seen and cand.lower() != text.lower():
            seen.add(cand.lower())
            uniq.append((kind, cand))
    return uniq


BE = {"i": "am", "we": "are", "they": "are", "you": "are", "he": "is", "she": "is", "it": "is", "thou": "art"}
IRREGULAR = {"man": "men", "woman": "women", "ox": "oxen", "foot": "feet", "tooth": "teeth", "child": "children",
             "wolf": "wolves", "calf": "calves", "loaf": "loaves", "leaf": "leaves", "knife": "knives", "half": "halves"}
PHRASE = re.compile(r"(?:(A|An|The)\s+|\((Some|Two)\)\s+)?((?:[A-Za-z-]+\s+){0,2}[A-Za-z-]+)")


def following_be(text: str, end: int) -> tuple[int, int, str, str] | None:
    """The form of "to be" right after a subject (optionally in brackets): (start, end, word)."""
    m = re.match(r"(\s*(?:\([a-z.]+\)\s*)?)(\(?)(am|is|are|art)\b", text[end:], re.I)
    if not m:
        return None
    return end + m.start(3), end + m.end(3), m.group(3), m.group(2)


def pluralize(word: str) -> str:
    low = word.lower()
    if low in IRREGULAR:
        return IRREGULAR[low]
    if re.search(r"[^aeiou]y$", low):
        return word[:-1] + "ies"
    if re.search(r"(s|x|ch|sh)$", low):
        return word + "es"
    return word + "s"


def singularize(word: str) -> str:
    low = word.lower()
    for one, many in IRREGULAR.items():
        if low == many:
            return one
    if low.endswith("ies"):
        return word[:-3] + "y"
    if re.search(r"(ss|x|ch|sh)es$", low):
        return word[:-2]
    if low.endswith("s") and not low.endswith("ss"):
        return word[:-1]
    return word


def a_or_an(word: str) -> str:
    return "An" if word[0].lower() in "aeiou" else "A"


def phrase_mutations(text: str) -> list[tuple[str, str]]:
    """Number and definiteness changes for a bare noun phrase ("A good man", "(Some) stars", "(Two) hands")."""
    m = PHRASE.fullmatch(text.strip())
    if not m or any(w.lower() in AGREE | FUNCTION | set(SUBJ) for w in m.group(3).split()):
        return []
    art, qty, words = m.group(1), m.group(2), m.group(3).split()
    head, rest = words[-1], words[:-1]
    out = []
    if art in ("A", "An"):
        many = rest + [pluralize(head)]
        out += [("number", "(Some) " + " ".join(w.lower() for w in many)), ("article", "The " + " ".join(w.lower() for w in words))]
    elif qty:
        one = rest + [singularize(head)]
        if one[-1] == head:
            return [("article", "The " + " ".join(w.lower() for w in words))]
        out.append(("number", a_or_an(one[0]) + " " + " ".join(w.lower() for w in one)))
        out.append(("number", ("(Two) " if qty == "Some" else "(Some) ") + " ".join(w.lower() for w in words)))
        out.append(("article", "The " + " ".join(w.lower() for w in words)))
    elif art is None:
        out.append(("article", "The " + " ".join(w.lower() for w in words)))
    return out


def pick_distractors(text: str, rng: random.Random, fallback: list[str], n: int = 3) -> list[str]:
    cands = mutations(text)
    rng.shuffle(cands)
    by_kind: dict[str, list[str]] = defaultdict(list)
    for kind, cand in cands:
        by_kind[kind].append(cand)
    picked: list[str] = []
    kinds = list(by_kind)
    while len(picked) < n and any(by_kind.values()):
        for k in kinds:
            if by_kind[k] and len(picked) < n:
                picked.append(by_kind[k].pop(0))
    pool = [f for f in dict.fromkeys(fallback) if f.lower() != text.lower() and f not in picked]
    rng.shuffle(pool)
    picked += pool[: max(0, n - len(picked))]
    return picked


def clean_display(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------- the ladder

def ladder(profile, base: str, forms: list[str], english: str, english_pool: list[str], direction: str,
           rng: random.Random, extra: dict, reading: str | None = None, hint: str | None = None) -> list[dict]:
    """Five items for one sentence. `forms` are the accepted forms in the script (first = display);
    `reading` is the text to translate at rung 4 when it differs (e.g. Davidson's unpointed prompts);
    `direction` equal to `profile.to_english` means the book's exercise was script → English."""
    shown = forms[0]
    names = rung_names(profile)
    items = []
    false_pool = pick_distractors(english, rng, english_pool, n=3)

    def item(rung: int, body: dict) -> dict:
        out = {"id": f"{base}.{RUNG_KEYS[rung]}", "rung": rung, "rungLabel": names[rung], **body, **extra}
        return out

    truth = rng.random() < 0.5 or not false_pool
    items.append(item(1, {
        "type": "true-false",
        "prompt": "Is this the right translation?",
        "stimulus": shown, "stimulusIsScript": True,
        "statement": english if truth else false_pool[0],
        "answer": truth,
        "expected": english,
    }))
    if len(false_pool) >= 1:
        options = [english] + false_pool[:3]
        rng.shuffle(options)
        items.append(item(2, {
            "type": "mcq",
            "prompt": "Choose the translation",
            "stimulus": shown, "stimulusIsScript": True,
            "options": options, "answer": english, "optionIsScript": False,
        }))
    blank = profile.blank_sentence(shown, rng)
    if blank:
        stimulus, word = blank
        items.append(item(3, {
            "type": "translate-phrase",
            "prompt": f"Fill in the missing word: {english}",
            "stimulus": stimulus, "stimulusIsScript": True,
            "accepted": [word], "answerIsScript": True,
        }))
    if direction == profile.to_english:
        body = {
            "type": "translate-phrase",
            "prompt": "Translate into English",
            "stimulus": reading or shown, "stimulusIsScript": True,
            "accepted": english_variants(english), "answerIsScript": False, "selfCheck": True,
        }
        if hint:
            body["hint"] = hint
        items.append(item(4, body))
    else:
        items.append(item(4, {
            "type": "translate-phrase",
            "prompt": f"Translate into {profile.name} ({profile.marks} not checked)",
            "stimulus": english, "stimulusIsScript": False,
            "accepted": forms, "answerIsScript": True,
        }))
    pointed = [h for h in forms if profile.is_marked(h)]
    if pointed:
        accepted = list(pointed)
        for h in pointed:
            for ctx in profile.alternatives(h):
                if ctx and ctx not in accepted:
                    accepted.append(ctx)
        items.append(item(5, {
            "type": "translate-phrase",
            "prompt": f"Translate into {profile.name} with full {profile.marks}",
            "stimulus": english, "stimulusIsScript": False,
            "accepted": accepted, "answerIsScript": True, "pointing": "required",
        }))
    return items
