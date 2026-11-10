# KNOWLEDGE-GRAPH

> `teaches` / `assumes` item IDs + the **known set**. The mechanism that replaces spaced
> repetition: as a student completes units across levels, the known set grows; recap +
> spiral distractors + review draw from it. Earlier-level vocab/grammar is **assumed
> known** — generators never re-teach known items, only re-surface them.

## 1. Items and IDs

A **knowledge item** is anything a unit can teach or assume: a lexeme, a morpheme, a
paradigm, or a grammar rule. Shape: see `docs/DATA-MODEL.md` §5.

- Item IDs are **globally unique** across levels: `<lang>-<course>-<unit>-<n>` (lexemes, e.g.
  `he-dav-01-001`), or a slug for non-lexeme kinds (e.g., `he-dav-paradigm-qatal`,
  `he-dav-rule-definite-article`).
- Items live in two places:
  - **Authored inline** in the units that teach them (the unit's `teaches` list).
  - **Snapshotted** in `prerequisites/knowledge.json` for items a later level assumes
    (so a later course stands alone).

## 2. `teaches` and `assumes`

Every unit declares:

```jsonc
{
  "unit": 12,
  "teaches": ["he-dav-12-001", "he-dav-12-002", "he-dav-rule-construct-chain"],
  "assumes": ["he-dav-01-001", "he-dav-paradigm-qatal", "he-dav-rule-noun"]
}
```

- `teaches` — items introduced or formalized by this unit. On completion, these are added
  to the student's known set.
- `assumes` — items the unit's lesson assumes the student already knows (from earlier units
  or earlier levels). Used for: the "Previously…" recap, and for surfacing assumed items
  as spiral distractors.

`assumes` items are not necessarily re-taught — the lesson references them; if a student
lacks them (e.g., they skipped a prior level), the recap + the `prerequisites/knowledge.json`
snapshot fill the gap.

## 3. The known set

- The **known set** = union of `teaches` over all completed units **across all levels** for
  which the student has progress, plus the current course's `prerequisites/knowledge.json`
  snapshot (for items assumed from prior levels the student may not have taken).
- Stored in `progress.json.knownSet` as an array of item IDs; rebuilt on load from unit
  completion states (source of truth = completed units, not a manually-maintained list).
- The known set is the engine's pool for:
  - **"Previously…" recap** — first sentences of recently-completed units' summaries,
    shown on the next unit's overview.
  - **Spiral distractors** — older vocab appears as wrong answers in current drills
    (distractor `distractorDepth: recent | known` — see `docs/EXERCISE-TYPES.md` §5).
  - **Optional Warm-up review** — mixed set drawn from the known set.

**Implemented (P3-T5):** `engine/knowledge.js` builds the known set from completed
units (`vocabList` filtered by `unit ∈ done-units`); `buildRecap` returns the last ≤3
completed units' titles for the lesson "Previously…" block; `spiralItems` draws 2
review items from older units into the front of each drill session (tagged "Review").
Known-set derivation is on-the-fly from completed units; `progress.json.knownSet` is
persisted in P3-T7.

### Optional weakness diagnostics (ADR-015)

When `course.json.features.diagnostics` is on, the engine additionally records aggregate,
unit-level correctness in `progress.json.skills` (`{ "<unit>": { correct, attempts } }`).
`weakUnits(progress, currentUnit, count)` sorts completed prior units by their accuracy
(lowest first, with never-attempted units last) and `reviewItems(...)` uses that ordering to
bias the spiral/review items pulled into a session toward the units the student is weakest
at. On a wrong answer the drill shows a "Review Unit N" link, and (when
`features.reviewWarmup` is on) the lesson offers an optional warm-up listing weak prior
units. This is evidence-based and on-demand — there are no intervals, due dates, or review
queues (ADR-005 still governs).

## 4. Cross-level continuity

- A course's `course.json.prerequisites` lists prior courses whose `teaches` items are
  assumed — e.g. a level-B course sets `[{ "course": "<level-A course id>", "level": "A" }]`.
- `prerequisites/knowledge.json` ships a **snapshot** of the prerequisite courses' taught
  items, so the later course stands alone for recap/review even if the student never ran the earlier one.
  Generate it with `scripts/validate <prior-course> --snapshot`; the snapshot is the prior
  course's authored vocab as `kind:"lexeme"` items carrying the vocab rows' own ids.
- If the student **has** prior course progress files locally (multiple course repos on
  disk with their own `progress.json`), the engine merges their known sets across levels
  for richer spiral review. (Mechanism: per-course progress is local; the engine can be
  pointed at a directory of course repos to build a combined known set. UI for this is
  minimal: a "Cross-level review" toggle on the Warm-up.)

## 5. Enforcement: assumed-known, not retaught

- Generators drawing from the known set **never** produce lessons that re-teach known
  items; they only re-surface them as:
  - recap text on unit overviews,
  - distractors in current drills,
  - Warm-up review prompts.
- This is the founding "no SRS" principle (ADR-005): reminding comes from progression +
  cumulative known set, not from a per-card review scheduler.

## 6. Authoring workflow

When authoring a unit:
1. List every lexeme introduced → `teaches` with new IDs.
2. List any paradigms/rules formalized → `teaches` with slug IDs.
3. List items the unit's prose relies on the student already knowing → `assumes`.
4. When the unit is finalized, ensure its `teaches` items are also in the course's
   `prerequisites/knowledge.json` **if** a later level assumes them. For a whole-level
   baseline snapshot, run `scripts/validate <course> --snapshot`, which emits
   `prerequisites/knowledge.json` from the course's authored vocab (lexeme items with the
   vocab rows' own ids; later re-run after vocab changes keep it in sync).

## 7. Schema notes

- Unit `teaches`/`assumes` arrays are validated against the course's knowledge item pool
  (a unit may not `teaches` an ID that doesn't exist somewhere in the course's authored
  items or its prerequisites snapshot). `scripts/validate` enforces this (P2-T4).