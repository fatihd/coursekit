# EXERCISE-TYPES

> Plugin contract + the type catalog. Authored workbook instances and generated drills
> share the **same renderers**, so an `mcq` is an `mcq` whether its data came from
> `exercises/01.json` or from a generator. New types go here AND in
> `engine/exercise-types/` (mandatory doc update per AGENTS.md §5).

## 1. Plugin contract

Every type is an ES module in `engine/exercise-types/<type>.js` registering:

```js
export default {
  id: "mcq",
  generate(params, pool)      // → item instance (for generated drills)
  render(item, ctx)            // → DOM node (or HTML string) for one item
  grade(item, answer)          // → { correct: bool, expected: any, feedback?: string }
}
```

- `params`: generator configuration from a unit's `exercises.generated` block
  (e.g., `{ direction: "script→gloss", count: 6, distractorDepth: "recent" }`).
- `pool`: the student's **known set** (items they've completed units for), filtered by the
  generator. This is the distractor source (and the non-SRS "remind" mechanism — older
  vocab resurfaces as wrong answers / recap as you advance).
- `ctx`: rendering context — script config (font, direction), keyboard handle, i18n.
- `answer`: whatever the renderer collects (chosen option index, typed string, ordered
  list, mapping object). The grader is type-specific.

Difficulty = **lookback depth**: how far back the `pool` reaches for distractors.
*(Distractor setting only. Course difficulty is the exercise ladder of ADR-022: true/false → multiple choice →
fill in the blank → translate without points → translate with points.)*
- `within-unit` — distractors only from the current unit (early units).
- `recent` — last ≤3 completed units.
- `known` — the full known set (later units → old vocab resurfaces naturally).

## 2. Catalog

### Workbook-mirroring types (shapes common in printed workbooks)

| id | Form | Description |
|---|---|---|
| `mcq` | MCQ | Pick the correct script/transliteration/gloss from N options. Directions: script→gloss, gloss→script, transliteration→script, script→transliteration. |
| `match-by-line` | Match | Pair N left items with N right items by drawing lines (or selecting pairs). Used for Hebrew↔English matching. |
| `categorize` | Sort into columns | Sort words into labeled columns by gender / root (`shoresh`) / dagesh type / part of speech / binyan. |
| `translate-phrase` | Translate + analyze | Translate a phrase (Hebrew→English or EN→HE) AND identify a property (PNG=person/number/gender, nominal-sentence yes/no, definiteness). |
| `fill-blank-verse` | Fill blank in a verse | A Bible verse with a blank; choose the word (often a pronominal-suffix form) that fits. |
| `transform` | Transform | Apply a transformation: add definite article + preposition, convert Yiqtol→Wayyiqtol, make a phrase definite. |
| `paradigm-tag` | Classify | Given a verb form, tag person/gender/number (e.g., 3ms, 2fp) using the abbreviations (1cs, 2mp…). |
| `paradigm-fill` | Fill conjugation table | Complete a paradigm table (Qatal/Yiqtol/Wayyiqtol/Weqatal) for given roots/persons. |
| `multi-translation` | Multiple readings | Produce N possible translations of a Qatal/Yiqtol form (past perfect, simple past, present perfect, future perfect). |
| `scan-text` | Scan a verse | Given a verse, find instances of a feature (matres lectionis, moving shewa, construct chains) and select/mark them. |
| `synonym-antonym` | Pair matching | Match word pairs that are synonyms or antonyms, then translate. |

Generated `match-by-line` items contain at most one row per script form. If the pool has
multiple lexicon entries with identical spelling, the generator keeps the last entry for
that spelling so each displayed left item has one unambiguous gloss.

### Ideated / extended types

| id | Form | Description |
|---|---|---|
| `root-pattern-compose` | Compose | Build a word from a given root (`shoresh`) + pattern (`mishqal`) — choose the correct resulting form. |
| `spot-error` | Error splice | A phrase contains one error (wrong vowel, wrong agreement, wrong binyan); locate and correct it. |
| `dictation` | Type pointed script | Hear/see the gloss, type the fully-pointed Hebrew/Aramaic word (uses on-screen keyboard + niqqud). |
| `translit-normalize` | Transliteration | Given a transliteration, produce the pointed script form (or vice versa); compares under NFC. |
| `gap-fill-verse` | Gap-fill a verse | A Bible verse with multiple gaps drawn from the unit's vocab; fill all. |
| `flash-timed` | Timed translate | Quick translation prompts under a per-item timer; form is MCQ but time-bounded. |
| `identify-binyan` | Classify | Given a verb, identify its binyan (Qal, Niphal, Piel…). (Courses that teach the stems.) |
| `build-construct-chain` | Compose | Build a construct chain that translates a given English phrase (e.g., "the king of the land"). |
| `parse-noun` | Classify | Choose a noun's gender and number from its pointed form (built from `gender`/`number`). |
| `parse-verb` | Classify | Choose a verb's stem, conjugation, person, gender, and number from its form (built from `extra.parse`). |
| `parse-form` | Classify (field by field) | Authored only (P9-T8): one dropdown per parse field (stem, form, person, gender, number, state, root); graded field by field against one or more accepted readings. |
| `produce-form` | Compose | Reverse production: choose the plural of a noun, or the Hebrew form matching a `root + features` description (built from `extra.parse` + `root`). |

## 3. Type → plugin map (initial)

- Implemented first (P3-T3/T4): `mcq`, `match-by-line`, `categorize`,
  `translate-phrase`, `fill-blank-verse`, `transform`, `paradigm-tag`, `paradigm-fill`,
  `multi-translation`, `scan-text`, `synonym-antonym` — **all 11 registered**, each
  with `render`/`collect`/`grade`. `mcq`/`match-by-line`/`categorize`/
  `translate-phrase` generate from the vocab pool and are mixed into unit sessions
  (`engine/session.js`); `transform`/`paradigm-tag`/`paradigm-fill`/
  `multi-translation`/`fill-blank-verse`/`scan-text`/`synonym-antonym` are
  authored-only for now (demo `generate` returns a single sample), to be wired to
  authored instances promoted from `exercises/NN.json` in P6.
- P6-T3 (2026-08-16): the ideated set is now **implemented + registered** (18 types
  total): `root-pattern-compose`, `spot-error`, `translit-normalize`, `gap-fill-verse`,
  `flash-timed`, `identify-binyan`, `build-construct-chain`. (`dictation` already
  existed from P3-T6.) `root-pattern-compose`/`spot-error`/`translit-normalize`/
  `flash-timed` generate from the vocab pool (shares `mcq.js` render/collect/grade or
  `util.js` normalizers); `gap-fill-verse`/`identify-binyan`/`build-construct-chain`
  are demo `generate` (rich demo items, real data wiring deferred to QA). Each
  render→collect→grade path is asserted by `scripts/e2e.py --exercise-types`.
- P9 (2026-11-03): three more types registered (21 total) — `parse-noun`, `parse-verb`,
  `produce-form`. They generate from the vocab pool (noun gender/number; verb
  `extra.parse` + `extra.binyan`; noun plural / verb root+features) and are mixed into a
  session only when `course.json.features.parsing` is true (ADR-015). They are gated by
  unit range (`parse-noun`/noun-produce from unit 9, `parse-verb`/verb-produce from unit
  16) so parsing follows the grammar sequence. Exercised by `scripts/e2e.py
  courses/biblical-hebrew-davidson --units 30`.

- P9-T8 (2026-11-10): `parse-form` registered (22 total) — authored-only parse drill
  (`generate` returns nothing). It also introduced the optional `annotate` hook below.

**Plugin contract note (P3-T4):** the contract now includes an optional
`collect(node, item) -> answer` step so non-MCQ types can gather a structured answer
(selections, text) before grading. `render` returns the input DOM; the drill view calls
`collect` on "Check", then `grade`. Optional `annotate(node, item, answer, result)` (P9-T8) is
called right after `grade` to mark the answer in place (`parse-form` outlines each select green
or red from `result.fields`). Answer grading normalizes text via `util.js`
(`normalize`). Types that generate from the vocab pool (`mcq`, `match-by-line`,
`translate-phrase`) are mixed into unit drill sessions by `engine/session.js`; the
paradigm/verb-centric types are authored-only until P6 (instances promoted from
`exercises/NN.json`). `categorize` is no longer part of the generated session mix — its
`generate` returns nothing when a pool has fewer than two parts of speech (single-category
units), so it was removed from `buildSession` to avoid trivial one-column sorts.

## 4. Authoring vs generation

- **Authored** items live in `courses/<course>/authored/NN.json` (schema
  `authored-exercises-v1.json`). They are passed directly to `render`; `generate` is not
  called for them. Each item carries its type and the per-type fields the renderer/grader
  need (see the shapes below).
- **Generated** drills: the engine calls `generate(params, pool)` with the unit's generator
  config + the student's known set. Output instance shape matches the authored shape, so
  the same `render`/`grade` applies.
- **Session composition** (`engine/session.js` `buildSession`): spiral review items first,
  then **authored items** (all of them, or a fresh random sample of
  `features.authoredPerSession` when the course sets it), then generated fill up to the
  session target. `engine/main.js` fetches `authored/NN.json` and passes `options.authored`;
  units without an authored file keep generated-only behavior.
- The raw workbook scaffolds in `exercises/NN.json` (`typeGuess`/`body_raw`/`answer_raw`)
  are author-side coverage input, not runtime items. OCR-extracted scaffolds are promoted to
  `authored/NN.json` **by hand**, not mechanically, because their extracted text is
  unreliable. The exception is Davidson: its exercises were transcribed and checked by hand in
  exwb, so `build/exwb_to_authored.py` generates both files from that set (P9-T6; shapes in
  `docs/DATA-MODEL.md` §4).
- `mcq` (and the types that reuse its renderer) shows an item's optional `prompt` as an
  instruction line above the stimulus.
- **Hints and explanations (P9-T7).** Any authored item may carry `hint` and `explain`
  (non-empty strings, in every item schema). `engine/views/drill.js` adds a "Show hint" button
  under the exercise when `hint` is set (the text replaces the button; the button is disabled
  once the answer is checked) and shows `explain` under the exercise together with the
  right/wrong feedback. Both use `dir="auto"` so Hebrew-led text reads correctly. A hint does
  not change scoring.

### Authored item shapes (per type)

| type | required fields |
|---|---|
| `mcq`, `paradigm-tag`, `root-pattern-compose`, `spot-error`, `flash-timed` | `stimulus, stimulusIsScript, options[], answer, optionIsScript` (`prompt`, `seconds` optional) |
| `translit-normalize` | `direction, stimulus, stimulusIsScript, answer, answerIsScript` (`prompt` optional) |
| `match-by-line` | `prompt, left[], right[], answer{left→right}, leftIsScript` |
| `categorize` | `prompt, columns[], words[{text,cat}], isScript` |
| `translate-phrase` | `prompt, stimulus, stimulusIsScript, accepted[]` (`answerIsScript` optional → typed Hebrew, RTL input, niqqud-insensitive; `source` optional → scan links) |
| `dictation` | `prompt, stimulus, stimulusIsScript, answer, transliteration` |
| `paradigm-fill` | `prompt, rows[{label, answer, options[]}], isScript` |
| `parse-form` | `prompt?, stimulus, stimulusIsScript, fields[{key, label, options[], isScript?}], readings[{field: value}]` — every select also offers "—" (not applicable); an answer is correct when it matches any reading, and a field a reading leaves out accepts any value; `grade` returns `fields{key: bool}` against the closest reading and `expected` = that reading + the fields to check |
| `fill-blank-verse` | `prompt, before, after, options[], answer, isScript` (`blankLabel` optional) |

Validation is enforced by `build/schemas/authored-exercises.json` via
`scripts/validate`; the render/collect/grade contract is asserted by
`scripts/e2e.py --authored`.

## 5. Distractor sourcing (the non-SRS "remind")

- Right-answer pool = items the unit `teaches` (for new-vocab drills) or the known set (for
  review/transform drills).
- Wrong-answer (distractor) pool = known set filtered by `distractorDepth`, excluding the
  right answer and near-duplicates (same root, same gloss).
- As the student advances, `distractorDepth` widens → older vocab naturally reappears as
  distractors. This replaces spaced-repetition review queues (ADR-005).

## 6. Grading and feedback

- Each `grade` returns correctness + the expected answer + optional feedback. Drills give
  **immediate** feedback (not delayed); wrong answers reveal the correct one.
- No penalty queue, no rescheduling, no per-card intervals — ever (ADR-005).
- Score per session → unit `bestScore` in progress; passing threshold unlocks the next unit
  (soft unlock: recommended-next highlight, not a hard gate).
- **No single-option MCQ.** Every choice-based item (`mcq`, `parse-noun`, `parse-verb`,
  `produce-form`, and spiral review) must render at least two visibly distinct options with
  exactly one correct answer. Generators deduplicate by displayed value and skip items that
  cannot meet this invariant; spiral review draws distractors from the full known set rather
  than a one-word pool. `scripts/e2e.py --keyboard` asserts the invariant across all units.
- **Keyboard navigation.** Each question focuses its first control on render; after checking,
  focus moves to the Next/See-results button and Enter advances to the next question (or the
  result screen). `scripts/e2e.py --keyboard` also drives this flow.
- **Typed Hebrew + niqqud-insensitive grading.** `translate-phrase` supports an
  `answerIsScript` item: the input becomes an RTL `hebrew-input`, and grading uses
  `util.normalizeHebrew()` (strips niqqud but keeps the sin/shin dot, folds the maqqeph),
  so a student's unpointed typing matches a pointed accepted answer. (`dictation` already
  typed Hebrew via NFC; this extends typed-Hebrew grading to `translate-phrase`.)
- **Scan provenance.** Any item may carry a `source` block with `promptUrl`/`answerUrl`
  (plus `*ImageUrl`) and a `note`. `engine/views/drill.js` renders them as "Original
  exercise page" / "Answer key page" links under the question, so OCR-derived items can be
  checked against their scans (ADR-017).

## 7. Adding a type (checklist)

1. Add `engine/exercise-types/<type>.js` with `{id, generate, render, grade}`.
2. Register it in the type registry (`engine/exercise-types/index.js`).
3. Add authored instances and/or generator config that use it.
4. **Update this doc** (catalog table + type→plugin map + any contract changes) — mandatory.
