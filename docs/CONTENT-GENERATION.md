# CONTENT-GENERATION

> Extraction pipeline + lesson generation + the **OER allowlist**. Author-side, offline.
> Produces validated JSON consumed by the engine. Per AGENTS.md §6: do NOT reproduce
> copyrighted text; lessons paraphrase/transform owned material and use only approved OER
> sources.

## 1. Pipeline overview

```
archive.org scans ─▶ scripts/fetch-sources ─▶ exwb/ (exercise review) + build/*davidson*.py
                                          │
                  build/generate-lessons.py + OER fetch
                                          ▼
                           course content JSON (units/, vocab, exercises, knowledge)
                                          │
                                scripts/validate (JSON Schema)
                                          ▼
                                    course ready
```


## 3. Lesson generation — `build/generate-lessons.py`

Second pass (P6-T2): reads the **canonical text** (`content/vocab.csv` +
`content/chapters/NN.md`) and the local OER cache (`build/_oer/`), and enriches the
text in place. It does **not** write JSON directly — the text stays the source of
truth; run `build/materialize.py` afterwards to regenerate the engine JSON.

Per unit, it adds:
- **`vocab.csv`**: OER columns `root`, `strong`, `pos`, `oer_source`, `oer_license`
  (per-row attribution — ADR-004). `root` comes from the Wiktionary `he-rootbox`;
  `strong`/`pos` from the OSHB/MorphHB lexicon (joined on a stripped, prefix-free
  base form — prefixed token forms like `וָ/יָֽפֶת` are normalized to the lexeme).
- **`chapters/NN.md`**:
  - a **Word roots (OER)** GFM table (`## Word roots (OER)`): Hebrew, transliteration,
    gloss, root, strong — emitted only when ≥1 unit item has root/strong data;
  - `## Teaches` — the unit's vocab item ids;
  - `## Assumes` — the *prior* unit's item ids (spiral recap; absent for unit 1);
  - `## Did You Know` — the unit's most-frequent token per OSHB counts, attributed to
    "OSHB/MorphHB (CC BY 4.0)".

`build/generate-lessons.py` now preserves the canonical `## Summary` in
`content/chapters/NN.md`; it does not read or copy `units/NN.summary.md`. It reconstructs
the OER table, vocabulary references, teaches/assumes lists, and frequency note.

Called as:
```bash
python build/generate-lessons.py --course courses/<course>
# then: python build/materialize.py --course … && scripts/validate …
```

Output is schema-validated (`scripts/validate`). Stubbed first in P2-T6 (30 placeholder
lesson stubs with prose + vocab blocks); OER enrichment landed in P6-T2 (2026-08-15).


**Public-domain course (2026-11-03, updated 2026-11-05):** `courses/biblical-hebrew-davidson`
(ADR-014, ADR-016, ADR-017) is a separate 79-unit course built on public-domain grammars; it reuses
no other course's data. Its vocabulary CSV adds a `parse` column (mapped to
`extra.parse` by `materialize.py`/`textify.py`), carrying each verb's grammatical description
for the `parse-verb`/`produce-form` exercise types (ADR-015). `oer_source`/`oer_license` there
record `BDB; OSHB` and `public domain; CC BY 4.0`.

**Davidson exercise recovery (2026-11-05, ADR-017).** `build/recover_davidson_exercises.py`
rebuilds the 1924 key's English→Hebrew `translate-phrase` exercises: English prompts are read
from the 22nd-edition grammar via Apple Vision OCR (`grammar-vision-en.json`), pointed Hebrew
answers from the key's DjVu export (`key-1924-djvu.xml`, which keeps Hebrew script), and each
item is matched to a unit via the chapter's `## Source` §. It emits `exercises/NN.json`
(scaffolds), `authored/NN.json` (engine items), and `build/_sources/davidson/exercise-inventory.json`
(provenance ledger). Key answers are segmented using the DjVu XML word-box x-coordinates and
printed item numbers (right-to-left); each record retains its own answer leaf, and mapping is
by printed item number so an unreadable label does not shift the rest of the list. Every item
carries `source.promptUrl`/`source.answerUrl` scan links, so OCR misreadings are a link-click
away from the original page rather than a dead end. The OCR tool
(`build/_sources/davidson/ocr_pdf.swift` → `ocr_pdf`) is a macOS Vision wrapper. Current
regeneration emits 85 key-paired records across 22 units, without a per-unit cap or
duplicate-stimulus suppression. This is an optional English→Hebrew drill subset, not the
whole-book inventory or a prerequisite for inclusion there.

**Complete grammar-only exercise inventory (2026-11-05, ADR-018).**
`build/inventory_davidson_exercises.py --write` inventories every OCR-detected exercise block
in the 22nd-edition grammar without consulting or matching the answer key. It writes
`build/_sources/davidson/grammar-exercise-inventory.json`, preserving each block's heading,
type guess, Vision OCR region, DjVu OCR region (Hebrew script), extracted items, and exact
prompt-page scan links. Current inventory: **48 blocks and 865 extracted items** (339 Hebrew, 526 English), no
caps — 29 translation, 7 parsing, 6 writing, 2 correction, 1 transliteration, 1 pointing,
1 pronunciation, 1 unspecified. A coordinate-based pass uses the DjVu word boxes (mapped to
the Vision coordinate space via the heading anchor) to drop the pointed-Hebrew rows that
Vision reads as Latin garble and to salvage the clean English runs of mixed lines; the
inventory now reports 0 unrecoverable fragments and 791 distinct items. "Recoverable"
still allows letter-level OCR errors — each block links its scan page as the arbiter.

**Answer-side inventory (2026-11-05, ADR-018).**
`build/inventory_davidson_answers.py --write` inventories the 1924 key the same way:
`build/_sources/davidson/key-answer-inventory.json` holds every OCR-detectable answer — part A
(English, via Vision, keyed by printed "N." markers) and parts B/C/D (pointed Hebrew, via the
DjVu coordinate segmentation) — each with its §, part, item number, script, exact key leaf, and
scan link. Current yield: 885 items (600 English, 285 Hebrew). No caps, no grammar matching;
the same OCR-variant handling applies.

**Pairing with sanity checks (2026-11-05).**
`build/pair_davidson_exercises.py --write` joins the two inventories on § + part + printed item
number and scores each prompt↔answer pair against the course vocabulary — gloss overlap for
translation pairs, consonant patterns for transliteration pairs — re-assigning pairs that score
as belonging to another item. Emitted drills are ok/weak pairs only: typed-Hebrew
`translate-phrase` (English→Hebrew), `mcq` (Hebrew→English, transliteration); suspect pairs stay
in `pair-inventory.json` with their score. Every item carries both scan links and its sanity
score. Current yield: 380 pairs (67 ok, 43 weak, 270 suspect); ok/weak pairs emit 176 item
placements across 32 units. The grammar's Hebrew prompts now use the same coordinate
segmentation as the key's answers.

**Course drills from exwb (2026-11-10, P9-T6) — current.** The OCR pairs above are no longer
emitted. `python build/exwb_to_authored.py --course courses/biblical-hebrew-davidson` turns the
hand-checked exwb transcriptions (`exwb/curated/`, 40 blocks / 1,138 items; held §1–5/7/9 skipped)
into `authored/` + `exercises/` for 34 units, placed by `build/_sources/davidson/exwb-units.json`
(a block goes to the unit teaching its topic, moved later when its sentences need later
grammar: §47–§49 land in units 50/55 though comparison, numerals and particles are taught in
units 14/19/20). Shapes: 427 English→Hebrew, 442 Hebrew→English (each now a five-rung ladder, below), 181 parse,
43 pointing corrections, 45 "give the form" choice; item format in `docs/DATA-MODEL.md` §4.
**One topic per unit (2026-11-11, P12-T6).** The Davidson course has 79 units, each on a single topic; Davidson
sections that had no unit (§4, §9, §24, §32) now have one. Unit numbers appear in `units.json`, `course.json`,
`content/chapters/NN.md`, `build/_sources/davidson/{grammar-units,exwb-units,vocab-layout}.json`; tests look units up by title.

**Per-sentence placement (2026-11-11, P12-T1).** Each translation sentence is tagged with the grammar it uses
(`build/_sources/davidson/sentence-grammar.json`, ids from `grammar-units.json`) and placed in the first unit that
teaches all of it (floor: unit 16). Phrases before the article (2026-11-12): `build/_sources/davidson/indefinite-phrases.json`
lists Davidson phrases with the article taken off (pointed by hand) and their English with a/an, nothing (mass
nouns), "(some)" (plurals) or "(two)" (duals); they become ladder items in units 14 (nouns, plurals, duals,
noun + adjective) and 15 (pronoun + noun), shape `phrase`, `source.adaptedFrom` naming the exercise, which keeps
its own place too. Vocabulary first use (`build/rebalance_vocab.py`) counts the plural column (also spelled ־ת for ־וֹת),
adjective endings (־ָה ־ִים ־וֹת ־ת, without a prefix letter) and ignores the script units' syllable/dagesh drills. Davidson
words missing from the frequency list are added to `content/vocab.csv` by hand (2026-11-12: wolf, palace, cow, side,
רָם "high"; frequency from `--recount`); common nouns are not pinned late, they are taught at first use. Parse, form and pointing items stay in their block's unit. A feature names one unit's
topic: when a unit is split, split its feature too and re-tag the sentences (2026-11-12: `volitive` → `imperative`/`jussive`/`infinitive`,
`particle` → `question`/`particle`).

**Noun phrase first and script-unit recognition (2026-11-12, P12-T8/T9).** Davidson units 18–26 teach the noun
phrase before demonstratives and clauses (construct 18, prefix prepositions 19, independent prepositions 20, waw 21,
noun suffixes 22, preposition suffixes 23, demonstratives 24, who/what/relative 25, object marker 26). To reorder units,
renumber together: `content/chapters/NN.md` (file and `# Unit N` heading), `units.json`, `course.json`,
`grammar-units.json`, `exwb-units.json`, `vocab-layout.json`, the `unit` column of `content/vocab.csv`; then run
`exwb_to_authored.py` → `rebalance_vocab.py` → `materialize.py` → `exwb_to_authored.py` and `scripts/validate --snapshot`.
Units without Davidson exercises (6, 9–12) get hand-written recognition questions from
`build/_sources/davidson/recognition.json`: each question is a true/false claim (rung 1), a choice (rung 2) and,
where it has `typed`, a typed answer (rung 3, `pointing` for pointed answers); shape `recognition`, linked to the
grammar page of its section (no Key link).

**Exercise ladder (2026-11-11, P12-T2/T3/T4).** `build/davidson_ladder.py` (called by `exwb_to_authored.py`)
turns each of the 869 sentences into five items (true/false, choose, fill in, translate, translate with vowel
points; 4,510 items with the parse/form/pointing questions). Wrong options and false statements are the Key's
English with one point changed (possessive, article, this/that, preposition group, "not", subject/object
pronoun — a changed subject takes the matching form of "to be": "I (am)" → "We (are)"; for a bare noun phrase
also number: "A good man" → "(Some) good men", "(Some) stars" → "A star" / "(Two) stars"); if fewer than three such changes exist, other sentences of the same Davidson section fill in. Typed
English is graded against variants of the Key's English: bracketed supplied words optional ("The light (is)
good"), grammar notes like "(fem.)" dropped, a one-word alternative in brackets may replace the word before it,
archaic forms modernized (thou hast → you have; -eth/-est verbs from the hand-checked table
`build/_sources/davidson/archaic-verbs.json`, so the build does not depend on a system word list). The pointed rung also
accepts the contextual form of a pausal last word when that form occurs mid-sentence elsewhere and differs only
in the lengthened vowel (qamets for patah/segol, never on the first letter). Unit files store each sentence's
source once (`sources`, items point by `src`); `authored/ladder.json` counts items per rung.

*(2026-11-11, ADR-022: Hebrew→English is now typed (rung 4), English→Hebrew is graded with pointing at rung 5,
and sessions climb the ladder instead of sampling 10; a later offline authoring pass expands the corpus.)*

**Vocabulary layout (2026-11-10, P9-T12).** `build/rebalance_vocab.py --course courses/biblical-hebrew-davidson
--layout build/_sources/davidson/vocab-layout.json` sets the unit of every word: units 9–56 get about the same
number (10–15); a word used in a unit's drills is taught there or earlier; pinned ids stay put; topic words (a verb
class, the numerals) start at their topic unit and overflow at most half of the following units; frequent words
first. `--recount build/_oer/morphhb/books` refills `frequency` from OSHB (Strong's-number counts; one-letter
prefixes from OSHB's prefix codes). Ids never change, so saved progress stays valid. Then run `materialize.py`.
The pairing and recovery scripts are report-only (`--write` retired).

Run commands: `python build/inventory_davidson_exercises.py` (grammar blocks),
`python build/inventory_davidson_answers.py` (key answers), and
`python build/pair_davidson_exercises.py` (pairing + authored emission); add `--write` to emit.
`build/recover_davidson_exercises.py` is superseded by the pairing pipeline for emission but
still supplies the key's coordinate segmentation.

## 4. OER allowlist (approved sources)

| Source | Lang | License | Use |
|---|---|---|---|
| Aaron Christianson, *An Open Introduction to Biblical Hebrew* | Hebrew | CC BY-SA 3.0 | Primary source of the `biblical-hebrew-oer` course and an open reference for lesson explanations; adapt and attribute, do not reproduce exercises or unlicensed assets |
| OpenScriptures Hebrew Bible (OSHB) / MorphHB | Hebrew | CC BY 4.0 | Morphology, roots, glosses, frequency |
| Wiktionary Hebrew | Hebrew | CC BY-SA | Glosses, usage notes, etymology |
| SBLGNT (SBL Greek New Testament) | Greek | CC BY-SA 4.0 | Greek text for gap-fill, examples |
| Wiktionary Greek | Greek | CC BY-SA | Glosses, morphology, etymology |
| Perseus (Greek/Latin) | Greek | open (varies) | Morphology, lexicon |
| Comprehensive Aramaic Lexicon (CAL) | Aramaic | scholarly open | Aramaic lexicon, morphology |
| A. B. Davidson, *An Introductory Hebrew Grammar* (22nd ed., 1923 — the course's source per ADR-021; 19th ed., 1914, historical) + McFadyen *Key* (1924; keyed to the 22nd ed.) | Hebrew | Public domain | Primary sequence for `biblical-hebrew-davidson`; the key is the answer source for recovered exercises, with every item linking its prompt/answer scans (best-effort OCR, ADR-017). Edition audit: `build/_sources/davidson/SOURCES.md` (ADR-014) |
| Gesenius–Kautzsch–Cowley, *Gesenius' Hebrew Grammar* (1910) | Hebrew | Public domain | Grammar/syntax reference |
| Kalisch, *A Hebrew Grammar, with Exercises* (1875) + *Key* (1881) | Hebrew | Public domain | Supplementary exercises |
| Harper, *Hebrew Vocabularies* (1890) | Hebrew | Public domain | Frequency cross-check |
| Brown–Driver–Briggs (1906), Strong's (1890) | Hebrew | Public domain | Glosses and Strong's references |
| World English Bible (eBible.org, `engwebp`) | English | Public domain | Translations of the Bible verses in the Davidson corpus (P12-T5); `fetch_oer.py --source web` |

- Each OER-sourced row must carry **attribution** + license in `extra.source`/`extra.license`
  (written into `vocab.json` or `units/NN.json` block metadata).
- Cache fetched OER data under `build/_oer/` (gitignored if large; keep a manifest).
- **Not on the allowlist**: any copyrighted textbook/grammar. The student's own course
  PDFs are transformed (paraphrased), not reproduced. 

### `build/fetch_oer.py` (P6-T1)

Fetches the two approved Hebrew sources into `build/_oer/`:

```
build/_oer/
  manifest.json              # attribution manifest (tracked; lists source+license per dataset)
  morphhb/
    books/*.xml              # WLC per-book XML (gitignored)
    wordlist.csv             # WlcWordList: strong <-> form mapping (gitignored)
    lexicon.json             # token index: scriptForm -> {strong, pos, morph, count} (gitignored)
  wiktionary/
    <word>.json              # per-word raw wikitext + attribution (gitignored)
    index.json               # word -> url/source/license/authorship (tracked)
```

- Usage: `python build/fetch_oer.py --source all --course courses/<course>`
  (`--source morphhb|wiktionary`, `--limit N` for wiktionary, `--course` for the vocab list).
- **Resumable**: per-book XML, `wordlist.csv`, and per-word pages are skipped once present.
- **Rate-limiting**: polite backoff on 429/5xx; Wiktionary pages fetched in batches of 50
  titles per API call via `action=query&prop=revisions&rvprop=content`.
- **Attribution**: every cached row carries `source`+`license` (+`authorship`); the tracked
  `manifest.json` lists each dataset (name, licence, homepage, rows file). Follows the
  ADR-004 guardrail: cache text is transformed/paraphrased before it reaches students.
- P6-T1 result (2026-08-15): 39 book XMLs + `lexicon.json` (109,135 token forms, Strong's
  + POS/morph per form) + 366 Wiktionary pages for the first course's vocab. ~37 vocab forms not
  fetchable — these are exactly the truncated/garbled rows already on the P6-T2 hand-fix
  list (e.g. `רֹא`, `מִשְנָט`, `הוּא11`), so nothing real is missing.

The original workbook summaries at `units/NN.summary.md` remain author-only provenance and
are no longer a generator input. `build/generate-lessons.py` now preserves the Summary section
from canonical `content/chapters/NN.md` instead of copying the workbook extraction back into
the student-facing chapter.


## 8. Lint / format (P2-T5)

- Python: `ruff` — config in `pyproject.toml` (to be added). `ruff check build/` clean.
- Vanilla JS: no eslint (no build step); instead a short style guide note here:
  - 2-space indent, semi-colons, ES modules, no comments unless asked.
  - Functions documented in design docs, not inline.

## 9. Python environment

- `pypdf` and `jsonschema` are the third-party deps. Project venv at the repo root:
  `python3 -m venv .venv && .venv/bin/pip install pypdf ruff jsonschema`.
- Do NOT commit the venv; `.gitignore` excludes it.
- Run lesson scaffold: `.venv/bin/python build/generate-lessons.py --course courses/<course>`.
- Run validator: `.venv/bin/python scripts/validate courses/<course>`.
- Schemas live in `build/schemas/` (course, vocab, units, unit-lesson,
  workbook-exercises, answer-key, progress, knowledge).
- Lint: `.venv/bin/ruff check build/ scripts/` (config in `pyproject.toml`).

### Test dependency (dev-only)

- Browser regression test `scripts/e2e.py` needs Playwright:
  `.venv/bin/pip install playwright && .venv/bin/python -m playwright install chromium`.
  Not required to run the course itself; see ROADMAP §Cross-cutting (regression gate).
