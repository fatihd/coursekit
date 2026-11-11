"""Exercise ladder for the Davidson sentences (ROADMAP P12-T2/T3/T4, AGENTS.md §0).

Every Davidson translation sentence (a Hebrew text and its English) becomes five items of
increasing difficulty: 1 true/false, 2 choose the translation, 3 fill in the blank,
4 translate (typed; Hebrew→English or English→Hebrew without points), 5 translate into
Hebrew with full vowel points. Wrong options and false statements are the Key's English
with one thing changed (possessive, article, this/that, a preposition from another group,
"not", a subject or object pronoun), so the Hebrew must be read to tell them apart.
Typed English is graded against variants of the Key's English: supplied words in brackets
optional, grammar notes dropped, archaic forms modernized.
"""

from __future__ import annotations

import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

HEB = re.compile(r"[א-ת]")
POINTS = re.compile(r"[ְ-ׇּׁׂ]")
ACCENTS = re.compile(r"[֑-ֽֿ֯׀׃-׆]")
WORD = re.compile(r"[A-Za-z]+(?:'[a-z]+)?")
RUNG_KEYS = {1: "tf", 2: "choice", 3: "fill", 4: "translate", 5: "pointed"}
RUNG_NAMES = {1: "True or false", 2: "Choose", 3: "Fill in", 4: "Translate", 5: "Translate with vowel points"}

ARCHAIC = {
    "thou": "you", "thee": "you", "ye": "you", "thy": "your", "thine": "your", "thyself": "yourself",
    "art": "are", "hast": "have", "hath": "has", "doth": "does", "dost": "do", "shalt": "shall",
    "wilt": "will", "wast": "were", "canst": "can", "saith": "says", "spake": "spoke", "unto": "to",
}
POSS = {"my": ["thy", "his", "our"], "thy": ["my", "his", "your"], "his": ["her", "my", "their"],
        "her": ["his", "my", "their"], "our": ["my", "their", "your"], "your": ["our", "my", "their"],
        "their": ["his", "our", "your"], "thine": ["my", "his", "their"]}
DEMS = {"this": "that", "that": "this", "these": "those", "those": "these"}
PREP_GROUPS = [{"in", "on", "upon", "at"}, {"to", "unto", "toward", "towards"}, {"from"}]
SUBJ = {"i": ["we", "they"], "we": ["I", "they"], "they": ["we", "I"], "he": ["she"], "she": ["he"]}
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
    return bool(HEB.search(c)) or "." in c or c.lower() in {"m", "f", "sing", "pl", "du"} \
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
        elif low in SUBJ and (low in {"he", "she"} or (nxt_low and nxt_low not in AGREE
                                                          and not re.search(r"(est|eth)$", nxt_low))):
            if low in {"i", "we", "they"} and i and toks[i - 1][2].lower() in {"to", "from", "with", "for", "by"}:
                continue
            for r in SUBJ[low]:
                put(i, r, "subject")
        elif low in OBJ:
            for r in OBJ[low]:
                put(i, r, "object")
    seen, uniq = set(), []
    for kind, cand in out:
        cand = re.sub(r"\s+", " ", cand).strip()
        if cand.lower() not in seen and cand.lower() != text.lower():
            seen.add(cand.lower())
            uniq.append((kind, cand))
    return uniq


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


# ---------------------------------------------------------------- Hebrew helpers

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


# ---------------------------------------------------------------- the ladder

def ladder(base: str, hebrew: list[str], english: str, english_pool: list[str], direction: str,
           rng: random.Random, pausal: PausalForms, extra: dict, reading: str | None = None,
           hint: str | None = None) -> list[dict]:
    """Five items for one sentence. `hebrew` is the list of accepted Hebrew forms (first = display);
    `reading` is the Hebrew to translate at rung 4 when it differs (Davidson's unpointed prompts)."""
    shown = hebrew[0]
    items = []
    false_pool = pick_distractors(english, rng, english_pool, n=3)

    def item(rung: int, body: dict) -> dict:
        out = {"id": f"{base}.{RUNG_KEYS[rung]}", "rung": rung, "rungLabel": RUNG_NAMES[rung], **body, **extra}
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
    blank = blank_sentence(shown, rng)
    if blank:
        stimulus, word = blank
        items.append(item(3, {
            "type": "translate-phrase",
            "prompt": f"Fill in the missing word: {english}",
            "stimulus": stimulus, "stimulusIsScript": True,
            "accepted": [word], "answerIsScript": True,
        }))
    if direction == "he-en":
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
            "prompt": "Translate into Hebrew (vowel points not checked)",
            "stimulus": english, "stimulusIsScript": False,
            "accepted": hebrew, "answerIsScript": True,
        }))
    pointed = [h for h in hebrew if is_pointed(h)]
    if pointed:
        accepted = list(pointed)
        for h in pointed:
            ctx = pausal.contextual(h)
            if ctx and ctx not in accepted:
                accepted.append(ctx)
        items.append(item(5, {
            "type": "translate-phrase",
            "prompt": "Translate into Hebrew with full vowel points",
            "stimulus": english, "stimulusIsScript": False,
            "accepted": accepted, "answerIsScript": True, "pointing": "required",
        }))
    return items
