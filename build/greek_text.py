"""Greek text keys for the build side — the Python twin of `engine/greek.js` (ROADMAP P11, ADR-025).

`compose` puts marks in canonical order (diaeresis, breathing, accent, iota subscript), NFC-composes and fixes final
sigma. `key(s, level)` is the grading key: `letters` (all marks dropped), `breathings` (breathings and iota subscript
kept), `full` (accents too; grave = acute; enclitic/proclitic accent variants, movable nu and elision tolerated).
`tests/test_greek_text.py` checks that it agrees with the engine on the cases of `scripts/e2e-greek.py`.
"""

from __future__ import annotations

import re
import unicodedata

MARK_RANK = {"\u0308": 0, "\u0313": 1, "\u0314": 1, "\u0301": 2, "\u0300": 2, "\u0342": 2, "\u0345": 3}
ACCENTS = re.compile("[\u0300\u0301\u0342]")
GREEK_LETTER = re.compile("[\u0370-\u03ff\u1f00-\u1fff]")
ELISION = re.compile("[\u1fbd\u1fbf\u2019\u02bc']")
PUNCT = re.compile("[.,;:!?\"()\\[\\]\u00b7\u0387\u037e\u2014\u2013\u2018\u201c\u201d-]")
ELIDED = {
    "δι’": "διά", "ἀπ’": "ἀπό", "ἀφ’": "ἀπό", "ἀλλ’": "ἀλλά", "κατ’": "κατά", "καθ’": "κατά",
    "μετ’": "μετά", "μεθ’": "μετά", "παρ’": "παρά", "ἐπ’": "ἐπί", "ἐφ’": "ἐπί", "ὑπ’": "ὑπό",
    "ὑφ’": "ὑπό", "ἀντ’": "ἀντί", "ἀνθ’": "ἀντί", "δ’": "δέ", "οὐδ’": "οὐδέ", "μηδ’": "μηδέ",
    "ἵν’": "ἵνα", "τοῦτ’": "τοῦτο",
}
ENCLITIC = set(("μου μοι με σου σοι σε τις τι τινος τινι τινα τινες τινων τισι τισιν τινας εστι εστιν εισι εισιν "
                "εσμεν εστε ειμι φημι φησι φησιν φαμεν φασι φασιν γε τε τοι περ που ποτε πω πως ποθεν")
               .replace("ς", "σ").split())
PROCLITIC = set("ει εν εις εκ εξ ως ου ουκ ουχ".replace("ς", "σ").split())
NU_KEEP = {"ουδεν", "μηδεν"}


def _is_mark(ch: str) -> bool:
    return unicodedata.category(ch).startswith("M")


def _strip(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if not _is_mark(c))


def bare(w: str) -> str:
    return _strip(w).lower().replace("ς", "σ")


def compose(s: str) -> str:
    out: list[list] = []
    for ch in unicodedata.normalize("NFD", s or ""):
        if _is_mark(ch) and out:
            out[-1][1].append(ch)
        else:
            out.append([ch, []])
    text = "".join(b + "".join(sorted(dict.fromkeys(m), key=lambda x: MARK_RANK.get(x, 9))) for b, m in out)
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"ς(?=[^\W\d_])", "σ", text)
    return re.sub(r"σ(?![^\W\d_])", "ς", text)


def _spacing_breathings(s: str) -> str:
    s = re.sub("[\u1fbf\u1fbd]([^\\W\\d_])", "\\1\u0313", s)
    return re.sub("\u1ffe([^\\W\\d_])", "\\1\u0314", s)


def _drop_movable_nu(w: str) -> str:
    b = bare(w)
    if len(b) <= 3 or b in NU_KEEP:
        return w
    if b == "εστιν" or re.search(r"(σι|ε)ν$", b):
        return re.sub("ν$", "", w)
    return w


def _clitics(words: list[str]) -> list[str]:
    out = []
    for i, w in enumerate(words):
        b = bare(w)
        if b in ENCLITIC or b in PROCLITIC:
            out.append(ACCENTS.sub("", w))
            continue
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt is not None and bare(nxt) in ENCLITIC and len(re.findall("[\u0301\u0342]", w)) > 1:
            at = w.rfind("\u0301")
            w = w[:at] + w[at + 1:]
        out.append(w)
    return out


def words(s: str) -> list[str]:
    t = compose(_spacing_breathings(s or "")).lower()
    t = PUNCT.sub(" ", ELISION.sub("’", t))
    return [w for w in t.split() if w]


def key(s: str, level: str = "full", movable_nu: bool = True, elision: bool = True, clitics: bool = True) -> str:
    ws = words(s)
    if elision:
        ws = [ELIDED.get(w, w) for w in ws]
    ws = [unicodedata.normalize("NFD", w) for w in ws]
    if level == "full":
        ws = [w.replace("\u0300", "\u0301") for w in ws]
    elif level == "breathings":
        ws = [ACCENTS.sub("", w).replace("\u0308", "") for w in ws]
    else:
        ws = ["".join(c for c in w if not _is_mark(c)) for w in ws]
    ws = [w.replace("ς", "σ") for w in ws]
    if level == "full" and clitics:
        ws = _clitics(ws)
    if movable_nu:
        ws = [_drop_movable_nu(w) for w in ws]
    return unicodedata.normalize("NFC", " ".join(ws))


def greek_words(s: str) -> list[str]:
    return [w for w in words(s) if GREEK_LETTER.search(w)]


def has_accents(s: str) -> bool:
    return bool(ACCENTS.search(unicodedata.normalize("NFD", s or "")))
