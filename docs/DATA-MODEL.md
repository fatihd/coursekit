# DATA-MODEL

> Generic, language-agnostic JSON schemas. Per-language variation is handled by
> **column maps** and an `extra` bag, not by forking the schema per course (ADR-006).
> Schemas will live as JSON Schema files under `build/schemas/` (P2-T4); this doc is the
> authoritative sketch until then. JSON: 2-space indent, UTF-8, trailing newline, with
> multi-script text inline (not `\u`-escaped).

## 1. `course.json` (manifest)

```jsonc
{
  "id": "biblical-hebrew-davidson",
  "title": "Biblical Hebrew — Davidson Course",
  "language": "he",                 // ISO 639-1; affects script config
  "level": "A",
  "script": {
    "direction": "rtl",
    "font": "EzraSIL",
    "fontFile": "fonts/EzraSIL-Regular.woff2",
    "keyboard": "he_IL",            // maps to engine/keyboards/he_IL
    "translitScheme": "he-sbl"       // maps to engine/translit/he-sbl
    // Greek courses add: "profile": "greek" (engine/script.js grading), "code": "grc" (input lang),
    // optional "grading": { "plain": "breathings", "full": "full", "movableNu": true, "elision": true, "clitics": true }
  },
   "units": [
    { "id": "u01", "n": 1, "title": "The Aleph-Bet", "slug": "the-aleph-bet",
      "part": 1, "textbookPage": 1 }   // slug: optional, used in URLs (#/the-aleph-bet); fallback "u1"
    // ...one entry per unit
  ],
  "parts": [
    { "n": 1, "title": "Foundations", "units": [1,9] },
    { "n": 2, "title": "Nouns",       "units": [10,19] },
    { "n": 3, "title": "Verbs",       "units": [20,30] }
  ],
  "prerequisites": [
    { "course": "biblical-hebrew-oer", "level": "A" }  // example; empty for a first course
  ],
  "knowledgeGraph": "prerequisites/knowledge.json",
  "features": {                       // optional, opt-in (ADR-015)
    "parsing": true,                  // mix parse-noun/parse-verb/produce-form into drills
    "diagnostics": true,              // record per-unit skills; show "Review Unit N" on errors
    "reviewWarmup": true,             // offer an optional warm-up from weak prior units
    "targetItems": 24,                // session size (default 14 when absent)
    "reviewItems": 5,                 // spiral/review items pulled to the front (default 2)
    "authoredPerSession": 10,         // random sample of authored items per session (default all)
    "wordLadder": true,               // per-unit Words track, four rungs per word (P12-T12)
    "wordsPerSession": 10,            // items per Words session (default 10; a match set is one item)
    "retries": true,                  // drill: one hinted retry, missed questions return at the end, first-try credit
    "tests": true                     // test mode: unit / part / mock final tests (ADR-024)
  }
}
```

`features` is optional; courses that omit it keep the default drill mix and progress shape
unchanged. `parsing` exercise types are additionally gated by unit range (noun parsing from
unit 9, verb parsing from unit 16) so they follow the grammar sequence.

`textbookPage` is optional author-side source metadata for courses tied to a print textbook.
OER-only courses may omit it. `scripts/release-course` removes it from the student
`course.json`; the hub's `units.json` is also omitted from the release.

## 2. `vocab.json` (generic lexicon)

Generic shape; per-language column differences ride in `extra`. A **column map** declares
which source columns map to which fields for a language (see §7).

```jsonc
{
  "id": "he-dav-01-001",            // stable id: <lang>-<course>-<unit>-<n>
  "unit": 1,
  "category": "noun",               // shared taxonomy: noun|verb|adjective|preposition|
                                     //   proper-noun|number|adverb|demonstrative|pronoun|particle
  "scriptForm": "אָח",
  "plural": "אַחִים",                // optional
  "transliteration": "ʼāḥ",
  "pronunciation": "ʼaḥ",
  "gloss": "brother",               // clean English translation (no gender/number suffix)
  "gender": "m",                    // m | f | c (common) | null  (parsed from "(m.s.)" etc.)
  "number": "s",                    // s | p | d (dual) | null
  "frequency": 629,                  // biblical frequency (optional; Davidson: OSHB count by Strong's number)
  "root": null,                     // optional (Hebrew 3-letter root)
  "extra": {                         // per-language extras; see §7 column maps
    // verbs with a stem: "binyan": "Qal"
    // Greek: declension info embedded in scriptForm by convention
    // OER enrichment (P6-T2; written by build/generate-lessons.py):
  }
}
```

`gender`/`number` are **stored separately from `gloss`** (not stuffed into it), so a
recall exercise can grade the translation (`gloss`) without penalising a missing
"(m.s.)" suffix; other parentheticals (clarifications) stay in `gloss`.

**OER enrichment (P6-T2).** `build/generate-lessons.py` fills in OER-sourced fields from
the local cache (`build/_oer/`, see `docs/CONTENT-GENERATION.md` §4):

- `root` — triliteral root (Wiktionary `he-rootbox`), or `null`.
- `extra.strong` — Strong's number(s) (OSHB/MorphHB), string or absent.
- `extra.pos` — OSHB part-of-speech label, or absent.
- `extra.source` / `extra.license` — attribution, `; `-joined when multiple sources, per
  ADR-004. Rows with no enrichment carry **none of these keys** (no false attribution).
- `extra.parse` — a verb's full grammatical description (e.g. `Qal Qatal 3ms`), used by
  `parse-verb` (the answer) and `produce-form` (the reverse-production stimulus, combined
  with `root`). Optional; only verb rows carry it.

### Shared category taxonomy

`noun | verb | adjective | preposition | proper-noun | number | adverb | demonstrative |
pronoun | particle | conjunction | interjection | article | other`

Course column maps MAY refine (e.g., Greek uses `noun (proper)`); the engine normalizes to
the taxonomy above, putting the raw source value in `extra.sourceCategory`.

## 3. Unit lesson — `units/NN.json`

A lesson is an ordered list of typed **blocks** rendered by the lesson view.

```jsonc
{
  "unit": 1,
  "title": "The Aleph-Bet",
  "description": "Welcome! ...",
  "teaches": ["he-dav-alpha-history", "he-dav-letter-aleph", /* … */],
  "assumes": [],
  "blocks": [
    { "type": "prose", "caption": "Summary", "html": "This unit explored the historical development..." },
    { "type": "table",
      "caption": "The Hebrew Vowels",
      "columns": ["Vowel", "Transliteration", "Name", "Examples"],
      "rows": [ ["a", "ă", "ḥataf pataḥ", "מַחֲלָצוֹת maḥălāṣôt"], /* … */ ] },
    { "type": "vocab", "refs": ["he-dav-01-001", "he-dav-01-002"] },
    { "type": "callout", "variant": "did-you-know",
      "html": "Yiqtol forms are the basis for numerous names..." },
    { "type": "paradigm",
      "caption": "Qatal paradigm (Qal)",
      "columns": ["Person", "Singular", "Plural"],
      "rows": [ ["1", "קָטַלְתִּי", "קָטַלְנוּ"], /* … */ ] }
  ],
  "exercises": {
    "authored": ["exercises/01.json#ex1", "exercises/01.json#ex2"],
    "generated": {
      "types": ["mcq", "match-by-line", "categorize"],
      "count": 12,
      "distractorDepth": "within-unit"   // | "recent" | "known"
    }
  },
  "didYouKnow": "..."     // optional; also reachable as a callout block
}
```

Block types: `prose | table | vocab | callout | paradigm`. Prose blocks may carry a
`caption` heading, preserved by `materialize`/`textify` and rendered above the prose body.
New block types require a DATA-MODEL update + a lesson-view renderer (mandatory doc update
per AGENTS.md §5).

Filled in by `build/generate-lessons.py` (P6-T2): `teaches` = the unit's vocab item ids;
`assumes` = the *prior* unit's ids (spiral recap); a `table` block "Word roots (OER)"
(columns Hebrew, Transliteration, Gloss, Root, Strong) when any item has root/strong
data; and `didYouKnow` = the unit's most-frequent OSHB token, attributed. Round-tripped
through the text via `docs/CONTENT-PORTABILITY.md` §3.

## 4. Authored exercises — `authored/NN.json`

Two distinct artifacts exist; only one is consumed by the engine at runtime:

- **`exercises/NN.json`** (schema `workbook-exercises-v1.json`) — author-side **raw
  scaffolds** parsed from the workbook (`typeGuess`, `confidence`, `prompt`,
  `body_raw`, `answer_raw`). These are provenance/coverage input, **not** rendered by
  the engine, and are excluded from student releases together with `answer-key/NN.json`.
- **`authored/NN.json`** (schema `authored-exercises-v1.json`) — engine-consumable
  items in the per-type plugin shape. `scripts/release-course` ships this directory;
  `engine/main.js` loads `authored/<unit>.json` when it exists and mixes the items into
  the drill session (see `docs/EXERCISE-TYPES.md` §4).

```jsonc
{
  "schema": "authored-exercises-v1.json",
  "unit": 20,
  "items": [
    { "type": "match-by-line", "prompt": "…", "left": ["בָרַח"], "right": ["he fled"],
      "answer": { "בָרַח": "he fled" }, "leftIsScript": true }
    // per-type item shapes are defined in docs/EXERCISE-TYPES.md §4
  ]
}
```

Authored items must be hand-written and human-reviewed; the raw `body_raw`/`answer_raw`
scaffolds are not mechanically promoted because their extracted text is unreliable.

**exwb-derived items (Davidson, P9-T6, current).** `build/exwb_to_authored.py --course
courses/biblical-hebrew-davidson` turns the hand-checked exwb transcriptions
(`exwb/curated/davidson-*.json`, held blocks skipped) into `authored/NN.json` and
`exercises/NN.json` (scaffolds, `confidence: 1.0`). Units come from
`build/_sources/davidson/exwb-units.json` (block → unit, with a reason per block). Each item
keeps the engine shape of its type and adds:

```jsonc
{ "type": "parse-form", "prompt": "Parse this form", "stimulus": "אֶשְׁמֹר", "stimulusIsScript": true,
  "fields": [ { "key": "stem", "label": "Stem", "options": ["Qal", "Niph'al", "…"] },
              { "key": "form", "label": "Form", "options": ["perfect", "imperfect", "…"] },
              { "key": "person", "label": "Person", "options": ["1", "2", "3"] },
              { "key": "number", "label": "Number", "options": ["sing.", "plur.", "dual"] },
              { "key": "root", "label": "Root", "options": ["שָׁמַר", "…"], "isScript": true } ],
  "readings": [ { "person": "1", "number": "sing.", "form": "imperfect", "stem": "Qal",
                  "root": "שָׁמַר" } ],  // all accepted parses (P9-T8)
  "shape": "parse",            // en-he | he-en | parse | correct-pointing | he-form
  "id": "s21-AL1.parse",       // optional, stable item id (shown in the drill, used in #/<unit>/item/<id>)
  "rung": 3, "rungLabel": "Parse", // optional, exercise ladder rung 1–5 (P12-T4)
  "block": "s21", "blockLabel": "Davidson §21",  // optional, the Davidson section the item comes from
  "src": "s21-AL1",            // optional, key into the file's "sources" map (scan links stored once)
  "hint": "…", "explain": "…", // optional (schema: any item type, P9-T7); hint = shown on request
                               // before answering, explain = shown with the feedback. Unpointed
                               // prompts get "hint": "With vowel points: <pointed form>"
  "data": { "parse": { "person": "1", "number": "sing.", "form": "imperfect", "stem": "Qal",
                       "root": "שָׁמַר" } },          // optional, from exwb (P9-T8)
  "source": { "citation": "Davidson … exercise §21 A L1; McFadyen, Key … (1924)",
              "promptUrl": "…/page/n98/mode/1up", "answerUrl": "…/page/n46/mode/1up",
              "promptImageUrl": "…", "answerImageUrl": "…",
              "exwb": "davidson-s21#AL1", "note": "Transcribed by hand from the scans …" } }
```

An article-less phrase (`build/_sources/davidson/indefinite-phrases.json`) has `"shape": "phrase"`, ids ending in
`i` (`s11-B9i.choice`) and `source.adaptedFrom` (the exwb ref of the exercise it was made from) instead of `exwb`.
A recognition question (`build/_sources/davidson/recognition.json`, units 6 and 9–12) has `"shape": "recognition"`,
ids `rNN-k.tf|choice|fill`, block `rNN` ("Recognition"), and a `source` with the citation and the grammar page
(`promptUrl`, `promptImageUrl`) only: there is no Key answer.

`parse` items are `parse-form` drills (P9-T8): `readings` = exwb `data.parse` (closed fields only),
with missing person/gender/number filled from the key's answer text ("2 or 3 plur. fem." → two
readings), plus the key's alternative (`data.parse.alt`, parsed; it inherits root and stem, and
gender/number/state when its form is the same). Fields shown = those any reading sets; root
options = the item's root + three other roots of the block. `explain` = "Key: <answer>".
`he-form` prompts ("זָכָר (male) → cstr. sing.") are split: the Hebrew word is the stimulus,
the instruction names the form ("Choose the construct singular of this word (male)"), and the
distractors are the word's other forms plus the word itself. `en-he` items are typed-Hebrew `translate-phrase` (`accepted` = the key's answer plus its
"(or …)" / "X or Y" / "(in pause …)" variants); every other shape except `parse` is an `mcq` whose
distractors are other answers of the same block and part (corrections also offer the
mispointed form). Scan leaves are the block note's printed page + 19 (grammar) / + 15 (key).
`--check` fails when the course files differ from what the generator would write.

**OCR-derived items (Davidson, ADR-017; superseded by the exwb set above, kept for history).** `build/recover_davidson_exercises.py` emits
Davidson-key `translate-phrase` items that are best-effort OCR, so each carries a `source`
block instead of a hand-review guarantee:

```jsonc
{ "type": "translate-phrase", "prompt": "…", "stimulus": "To-day", "stimulusIsScript": false,
  "accepted": ["הַיּוֹם", "היום"], "answerIsScript": true,
  "source": { "citation": "…§11; Key … §11 B",
              "promptUrl": "https://archive.org/details/…/page/n64/mode/1up",
              "answerUrl": "https://archive.org/details/…/page/n23/mode/1up",
              "promptImageUrl": "…", "answerImageUrl": "…",
              "note": "Read from the scans by OCR; open them if a reading looks wrong." } }
```

`source` is additive (`additionalProperties: true`) and is rendered by the drill as scan
links. The `exercises/NN.json` scaffolds and the `build/_sources/davidson/exercise-inventory.json`
ledger are the author-side provenance (not shipped to students). The inventory records both
`grammarLeaf` and item-level `keyLeaf`; answer lists are parsed by DjVu word-box coordinates
and printed number, so an unreadable label can omit that item without shifting later matches.

**Complete grammar exercise-block inventory (ADR-018).**
`build/_sources/davidson/grammar-exercise-inventory.json` is independent of `authored/` and the
answer key. It preserves every OCR-detected exercise block — heading, type guess, Vision and
DjVu OCR regions, extracted items (numbered and unnumbered, Hebrew and English), and
`promptUrl`/`promptImageUrl`. It currently contains 48 blocks and 865 extracted items with
no per-unit cap. A coordinate-based pass maps the DjVu word boxes to the Vision coordinate
space (anchored on the exercise heading) to drop the pointed-Hebrew rows Vision reads as
Latin garble and salvage the clean English runs of mixed lines; the inventory reports 0
unrecoverable fragments. The counts are OCR yields, not a verified printed total; the raw
page OCR and scan links are retained so the printed page remains the arbiter.

**Answer-side inventory (ADR-018).**
`build/_sources/davidson/key-answer-inventory.json` inventories the 1924 key the same way:
each OCR-detectable answer carries its §, part (A/B/C/D), printed item number, script, exact
key leaf, and scan URL. Part A (English) via Vision; parts B/C/D (pointed Hebrew) via the
DjVu coordinate segmentation. Current yield: 885 items (600 English, 285 Hebrew). No caps, no
grammar matching.

**Pairing ledger (ADR-018).**
`build/_sources/davidson/pair-inventory.json` holds every prompt↔answer pair with §, part,
number, direction, a lexical sanity score/tier (course-vocabulary gloss overlap for
translations, consonant patterns for transliterations), and both scan leaves. The pairing
script emits `authored/`/`exercises/` only for ok/weak pairs; suspect pairs remain in the
ledger.

### Exercise ladder items (Davidson, P12-T2/T3/T4)

Every Davidson translation sentence yields five items in its unit file, ids `<src>.<rung key>`:

```jsonc
{ "id": "s15-B1.tf", "rung": 1, "type": "true-false", "prompt": "Is this the right translation?",
  "stimulus": "אָמַרְתִּי לָאִישׁ", "stimulusIsScript": true,
  "statement": "I said to a man.", "answer": false, "expected": "I said to the man." }
{ "id": "s15-B1.choice", "rung": 2, "type": "mcq", "options": ["I said to the man.", "They said to the man.", "…"], … }
{ "id": "s15-B1.fill", "rung": 3, "type": "translate-phrase", "prompt": "Fill in the missing word: I said to the man.",
  "stimulus": "＿＿＿ לָאִישׁ", "accepted": ["אָמַרְתִּי"], "answerIsScript": true }
{ "id": "s15-B1.translate", "rung": 4, "type": "translate-phrase", … }   // he→en: "selfCheck": true, English accepted[]
{ "id": "s15-B1.pointed", "rung": 5, "type": "translate-phrase", "pointing": "required",
  "accepted": ["אָמַרְתִּי לָאִישׁ"], "answerIsScript": true }
```

The unit file carries `"sources": { "<src>": { citation, promptUrl, answerUrl, exwb, note } }` once per
sentence; the engine attaches `source` to each item by its `src`. `authored/ladder.json` lists the items per
rung per unit (`{"units": {"35": {"1": 15, "2": 15, …}}, "extra": {"35": {"1": 15, …}}}`: `units` counts the
book's exercises, `extra` the corpus items) for the roadmap's stars. Corpus items (new sentences `cNN-NN`, Bible verses
`b-<Book>-<ch>-<v>`; P12-T5) carry `"extra": true` and shape `corpus` / `bible`; their right answers are stored under
`progress.units[n].done["x<rung>"]`. `course.json` features:
`unlockRung` (the next unit unlocks when every item of rungs 1…unlockRung was answered right once; Davidson 3),
`ladderTarget` (right answers a rung needs: every book exercise, topped up from the extra items; Davidson 20; without
it every extra item is needed)
and `vocabPerSession` (generated vocabulary items in a ladder session, default 4).

## 5. Knowledge item — `prerequisites/knowledge.json`

A snapshot of items taught by earlier levels, so a later course stands alone for recap/spiral
review even if the student never ran those levels.

```jsonc
{
  "items": [
    { "id": "he-dav-01-001",
      "language": "he",
      "kind": "lexeme",                 // lexeme | morpheme | paradigm | grammar
      "level": "A", "unit": 1,
      "scriptForm": "אָח", "transliteration": "ʼāḥ",
      "gloss": "brother (m.s.)",
      "category": "noun",
      "props": { "gender": "m", "number": "s" }
    },
    { "id": "he-dav-paradigm-qatal",
      "language": "he", "kind": "paradigm",
      "level": "A", "unit": 20,
      "gloss": "Qatal suffix conjugation",
      "props": { "binyan": "Qal" }
    }
    // …
  ]
}
```

Item IDs are **globally unique** across levels (`<lang>-<level>-<n>` or a slug for
non-lexeme kinds). Units reference them in `teaches`/`assumes`.

## 6. Progress object (localStorage value and Export/Import file)

```jsonc
{
  "schema": "progress/progress-v1.json",
  "courseId": "biblical-hebrew-davidson",
  "student": { "name": "", "forkRemote": "" },        // forkRemote: legacy, unused
  "currentUnit": 3,
  "units": {
    "u01": { "state": "done",     "lessonRead": true,  "bestScore": 90, "lastPlayed": "2026-08-12T10:00Z" },
    "u02": { "state": "done",     "lessonRead": true,  "bestScore": 85, "lastPlayed": "2026-08-12T11:00Z" },
    "u03": { "state": "in-progress","lessonRead": true, "bestScore": 0,  "lastPlayed": "2026-08-12T12:00Z",
             "done": { "1": ["s20-B3.tf"], "2": ["s20-B3.choice"] },    // ids answered right, per ladder rung (P12-T4)
             "words": { "1": ["he-dav-02-001"], "2": [] } }             // vocab ids right, per word rung (P12-T12)
  },
  "sessions": {                                         // open drill per unit ("N") or block ("N:block")
    "35": { "seed": "k3f9q1", "block": null, "pos": 7, "total": 24, "correct": 5, "answered": 6, "detail": [],
            "requeue": ["s20-B3.choice"] }             // questions coming back at the end (retries)
  },
  "tests": [                                            // test-mode results (ADR-024), oldest first
    { "scope": "unit", "key": 16, "seed": "mooprt", "date": "2026-11-12T10:35:53Z", "correct": 16, "total": 16,
      "score": 100, "elapsed": "0:52" }                 // scope unit|part|final; key = unit or part number
  ],
  "knownSet": ["he-dav-01-001", "he-dav-01-002", /* … items from completed units */],
  "skills": { "20": { "correct": 12, "attempts": 14 } },   // optional, ADR-015
  "xp": 175,
  "lastAttemptBranch": null,                            // legacy, unused (ADR-019)
  "lastExportedAt": "2026-08-12T12:00:00Z",             // set by Export progress
  "updatedAt": "2026-08-12T12:00:00Z"
}
```

Schema-versioned (`schema` field; schema `build/schemas/progress.json`) for forward
migration. Stored in `localStorage` under `lang-research.progress.<courseId>`; exported as
`<courseId>-progress-<YYYY-MM-DD>.json`; imports are merged (ADR-019). Courses no longer
contain a `progress/` folder.


## 8. Versioning and migration

- Every top-level JSON file carries a `schema` field where applicable (course.json, vocab
  entries via the file's outer wrapper, progress.json).
- Breaking schema changes bump the version and ship a migration in `build/migrate/`.
- Migration policy: the engine reads the highest version it knows; older `progress.json`
  on a student's fork is auto-migrated on load (with a backup written alongside).
