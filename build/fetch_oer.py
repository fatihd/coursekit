#!/usr/bin/env python3
"""build/fetch_oer.py — fetch approved OER Hebrew sources into build/_oer/ (P6-T1).

Populates the local OER cache used by the lesson-generation pass
(build/generate-lessons.py, P6-T2). Sources are restricted to the OER
allowlist in docs/CONTENT-GENERATION.md §4:

  * OpenScriptures Hebrew Bible / MorphHB — CC BY 4.0
    (morphology, roots, glosses, frequency)
  * Wiktionary Hebrew — CC BY-SA 3.0 / GFDL
    (glosses, usage notes, etymology)

Output (all under build/_oer/):
  manifest.json             attribution manifest (every row carries source+license)
  morphhb/books/*.xml        WLC per-book XML (raw, kept for re-processing)
  morphhb/lexicon.json       token index: scriptForm -> {strong, root, pos, gloss, count}
  wiktionary/<word>.json     per-word Wiktionary pages (raw title/authored summary)
  wiktionary/summary.json    index of fetched Wiktionary words

Usage:
    python build/fetch_oer.py --source all
    python build/fetch_oer.py --source morphhb
    python build/fetch_oer.py --source wiktionary --course courses/biblical-hebrew-davidson

See docs/CONTENT-GENERATION.md, docs/STATUS.md P6-T1.
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

OEROOT = Path(__file__).resolve().parent / "_oer"

OSHB_BASE = "https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc"

OSHB_BOOKS = [
    "Gen", "Exod", "Lev", "Num", "Deut", "Josh", "Judg", "Ruth", "1Sam", "2Sam",
    "1Kgs", "2Kgs", "1Chr", "2Chr", "Ezra", "Neh", "Esth", "Job", "Ps", "Prov",
    "Eccl", "Song", "Isa", "Jer", "Lam", "Ezek", "Dan", "Hos", "Joel", "Amos",
    "Obad", "Jonah", "Mic", "Nah", "Hab", "Zeph", "Hag", "Zech", "Mal",
]

WLC_WORDLIST = (
    "https://raw.githubusercontent.com/openscriptures/morphhb/master/WlcWordList/Words.csv"
)

WIKTIONARY_API = "https://en.wiktionary.org/w/api.php"

OSIS_NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"

MORPH_HEB = {
    "A": "adjective", "C": "conjunction", "D": "adverb", "N": "noun",
    "P": "pronoun", "R": "preposition", "S": "suffix", "T": "particle",
    "V": "verb",
}

NIOQ = {chr(cp) for cp in range(0x0591, 0x05C8)}

ROOT_STRONG = re.compile(r"^([A-Za-z])?/?(?:(\d{1,5})|(?:H\d{1,5}))")


def iso_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def strip_niqqud(s):
    return "".join(ch for ch in s if ch not in NIOQ)


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": WIKTIONARY_UA})
    last_err = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt + 1)
                continue
            raise
    raise last_err


WIKTIONARY_UA = (
    "lang-research-fetch/0.1 (Hebrew OER cache builder; "
    "contact: course author) requests-with-backoff"
)


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)


def load_json(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# MorphHB
# ---------------------------------------------------------------------------

def fetch_morphhb():
    out_books = OEROOT / "morphhb" / "books"
    ensure_dir(out_books)

    fetched = []
    for book in OSHB_BOOKS:
        dest = out_books / f"{book}.xml"
        if dest.exists():
            continue
        url = f"{OSHB_BASE}/{book}.xml"
        try:
            dest.write_bytes(get(url, timeout=60))
            fetched.append(book)
        except Exception as e:
            print(f"  [warn] {book}: {e}")
    if fetched:
        print(f"morphhb: fetched {len(fetched)} books: {', '.join(fetched[:6])}...")

    lexicon = build_lexicon(out_books)

    wordlist = OEROOT / "morphhb" / "wordlist.csv"
    if not wordlist.exists():
        try:
            wordlist.write_bytes(get(WLC_WORDLIST))
        except Exception as e:
            print(f"  [warn] wordlist: {e}")

    enrich_lexicon_from_wordlist(lexicon, wordlist)

    out_lex = OEROOT / "morphhb" / "lexicon.json"
    out_lex.write_text(
        json.dumps(
            {
                "schema": "oer-morphhb-lexicon-v1.json",
                "source": "OpenScriptures Hebrew Bible / MorphHB (WLC)",
                "homepage": "https://github.com/openscriptures/morphhb",
                "license": "CC BY 4.0",
                "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
                "authorship": "Open Scriptures Hebrew Bible Project; base text Westminster "
                "Leningrad Codex (public domain)",
                "lastFetched": iso_now(),
                "rowLicense": "CC BY 4.0",
                "rowSource": "OSHB/MorphHB",
                "count": len(lexicon),
                "rows": lexicon,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"morphhb: lexicon with {len(lexicon)} unique forms -> "
          f"build/_oer/morphhb/lexicon.json")


def parse_morph(morph):
    pos_letter = morph[1] if len(morph) > 1 and morph[0] == "H" else ""
    pos = MORPH_HEB.get(pos_letter, "unknown")
    return {"pos": pos, "code": morph}


def build_lexicon(books_dir):
    lexicon = {}
    for book_xml in sorted(books_dir.iterdir()):
        if book_xml.suffix != ".xml":
            continue
        try:
            tree = ET.parse(book_xml)
        except ET.ParseError as e:
            print(f"  [warn] parse {book_xml.name}: {e}")
            continue
        root = tree.getroot()
        for w in root.iter(f"{OSIS_NS}w"):
            form = (w.text or "").strip()
            if not form:
                continue
            morph = w.get("morph", "")
            if not morph.startswith("H"):
                continue
            strong = w.get("lemma", "")
            entry = lexicon.setdefault(
                form,
                {
                    "scriptForm": form,
                    "plainForm": strip_niqqud(form),
                    "strong": strong,
                    "pos": parse_morph(morph)["pos"],
                    "morph": morph,
                    "count": 0,
                },
            )
            entry["count"] += 1
    return lexicon


def enrich_lexicon_from_wordlist(lexicon, wordlist_path):
    if not wordlist_path.exists():
        return
    rows = wordlist_path.read_text(encoding="utf-8").splitlines()
    strong_to_gloss_rows = {}
    for ln in rows:
        parts = ln.strip().strip('"').split('","')
        if len(parts) < 2:
            continue
        strong, form = parts[0], parts[1]
        strong_to_gloss_rows.setdefault(form, strong)
    for entry in lexicon.values():
        strong = strong_to_gloss_rows.get(entry["plainForm"]) or strong_to_gloss_rows.get(
            entry["scriptForm"]
        )
        if strong:
            entry["strong"] = strong


# ---------------------------------------------------------------------------
# Wiktionary
# ---------------------------------------------------------------------------

def vocab_forms(course_dir):
    """Yield unique vocabulary scriptForms (pointed) from a course's vocab.csv."""
    csv_path = course_dir / "content" / "vocab.csv"
    if not csv_path.exists():
        csv_path = course_dir / "vocab.json"
        if csv_path.exists():
            data = load_json(csv_path)
            forms = [it["scriptForm"] for it in data["items"]]
        else:
            return []
    else:
        import csv

        with csv_path.open(newline="", encoding="utf-8") as f:
            forms = [row["scriptForm"] for row in csv.DictReader(f)]
    return list(dict.fromkeys(f for f in forms if f))


def fetch_wiktionary(course_dir, limit=None):
    forms = vocab_forms(course_dir)
    out_dir = OEROOT / "wiktionary"
    ensure_dir(out_dir)

    if limit:
        forms = forms[:limit]

    pending = []
    for form in forms:
        dest = out_dir / f"{strip_niqqud(form)}.json"
        if dest.exists():
            continue
        pending.append(form)

    fetched = 0
    errors = 0
    missing = 0
    idx = 0
    while idx < len(pending):
        batch = pending[idx : idx + 50]
        idx += len(batch)
        titles = [strip_niqqud(f) for f in batch]
        qs = urllib.parse.urlencode(
            {
                "action": "query",
                "titles": "|".join(titles),
                "format": "json",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "formatversion": "2",
            }
        )
        url = f"{WIKTIONARY_API}?{qs}"
        try:
            raw = get(url, timeout=60)
            data = json.loads(raw)
            pages = data.get("query", {}).get("pages", [])
        except Exception:
            errors += len(batch)
            time.sleep(1.0)
            continue
        for page in pages:
            title = page.get("title", "")
            revs = page.get("revisions")
            text = revs[0]["slots"]["main"]["content"] if revs else ""
            form = next((f for f in batch if strip_niqqud(f) == title), title)
            dest = out_dir / f"{strip_niqqud(form)}.json"
            if not text:
                missing += 1
                continue
            dest.write_text(
                json.dumps(
                    {
                        "word": strip_niqqud(form),
                        "pointed": form,
                        "url": f"https://en.wiktionary.org/wiki/{urllib.parse.quote(strip_niqqud(form))}",
                        "source": "Wiktionary",
                        "license": "CC BY-SA 3.0 / GFDL",
                        "authorship": "Wiktionary contributors",
                        "lastFetched": iso_now(),
                        "wikitext": text,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            fetched += 1
        time.sleep(0.5)

    write_wiktionary_index(out_dir)
    print(
        f"wiktionary: fetched {fetched}, missing {missing}, errors {errors} "
        f"({len(pending)} pending target forms)"
    )


def write_wiktionary_index(out_dir):
    index = []
    for f in sorted(out_dir.glob("*.json")):
        if f.name == "index.json":
            continue
        data = load_json(f)
        if data:
            index.append(
                {
                    "word": data["word"],
                    "pointed": data["pointed"],
                    "url": data["url"],
                    "source": data["source"],
                    "license": data["license"],
                    "authorship": data["authorship"],
                }
            )
    (out_dir / "index.json").write_text(
        json.dumps(
            {
                "schema": "oer-wiktionary-index-v1.json",
                "count": len(index),
                "rows": index,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def write_manifest():
    manifest = {
        "schema": "oer-manifest-v1.json",
        "purpose": "Local cache of approved OER sources for lesson enrichment (P6).",
        "lastFetched": iso_now(),
        "disclaimer": "Cached text is license-marked per row. Engine/course output must "
        "paraphrase/attribute; never reproduce wholesale (see ADR-004).",
        "sources": [
            {
                "id": "morphhb",
                "name": "OpenScriptures Hebrew Bible / MorphHB",
                "license": "CC BY 4.0",
                "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
                "homepage": "https://github.com/openscriptures/morphhb",
                "rows": "build/_oer/morphhb/lexicon.json",
            },
            {
                "id": "wiktionary",
                "name": "Wiktionary (English) Hebrew",
                "license": "CC BY-SA 3.0 / GFDL",
                "licenseUrl": "https://creativecommons.org/licenses/by-sa/3.0/",
                "homepage": "https://en.wiktionary.org",
                "rows": "build/_oer/wiktionary/index.json",
            },
        ],
    }
    (OEROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("manifest: build/_oer/manifest.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["all", "morphhb", "wiktionary"], default="all")
    ap.add_argument("--course", required=True)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if args.source in ("all", "morphhb"):
        fetch_morphhb()
    if args.source in ("all", "wiktionary"):
        fetch_wiktionary(Path(args.course), args.limit)
    write_manifest()
    return 0


if __name__ == "__main__":
    sys.exit(main())