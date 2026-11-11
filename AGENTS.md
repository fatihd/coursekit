# AGENTS.md — Operating Manual for AI Agents (and humans)

This document is the **operating manual** for anyone — AI agent or human — working in
this repository. Read it **in full before doing anything**. It is the root of the doc tree;
design docs live under `docs/` and are referenced from here.

> **TL;DR for impatient agents:** (1) Never commit copyrighted material, scans or large files —
> `python scripts/public-audit` must pass. (2) Doc sync is part of "done" —
> see [§ Keep the docs up to date](#keep-the-docs-up-to-date--mandatory). (3) Don't commit unless
> explicitly asked. (4) The course vision is §0: an exercise ladder and a growing exercise corpus.

---

## 0. Course vision — read first (user, 2026-11-11; ADR-022)

This overrides any older doc that conflicts with it.

**Goal.** A learner who works through a course can pass a university or seminary written exam in the
language and is literate in it: enough vocabulary and grammar (plus some semantics, translation and
pragmatics) to read texts, with a dictionary only for rarer words. The software gives many more
exercises than the original textbooks and grammars, with progressive difficulty, progress bookkeeping,
and mild gamification to keep motivation up. Literacy and the exam are the measure, not streaks.


- **The student progresses through exercises of increasing difficulty**, in this ladder:
  true/false → multiple choice → fill in the blank → translate without vowel points →
  translate with vowel points. A unit is learned by climbing it.
- **Sentences from the start.** The material is split and rearranged so the student reads and
  writes complete sentences early; nobody waits until the end of the book to translate.
- **A large exercise corpus, built offline.** The course ships as static files (data + tests);
  there is no live agent. A later authoring pass (an agent working in this repo) expands the
  corpus after the material is split and rearranged: many more exercises per unit — new
  sentences from the unit's grammar and words, and excerpts from real Bible prose that fit what
  has been taught — written into the course data. The goal is replayability: a student never
  memorises answers by retaking the same test, and never drops the course after two units
  because it is boring.
- **Every exercise sits where it can first be done**: a sentence goes in the first unit whose
  grammar and words it needs, not in the unit named after its source section.
- **Translation is typed, both directions.** Never turn a translation into multiple choice;
  multiple choice only where every wrong option is plausible and differs in the point being
  tested (not guessable from one known word). Hebrew answers at the top rung need full pointing.
- **No transliteration** in exercises.

---

## 1. What this repo is

`lang-research` is the **authoring hub** for a family of Biblical-languages courses
(Hebrew, Greek, Aramaic) powered by one reusable, language-agnostic **engine**.
The hub is a **monorepo**: `engine/` + all `courses/*` are developed together here. A
release script (`scripts/release-course <name>`) stamps a **self-contained forkable repo** =
course content + a pinned vendored copy of `engine/` — that artifact is what students fork.

The application is a **local web app** (vanilla JS + ES modules, no build step, no server)
that marches a student through a visible unit map: *teach → drill → unlock next*. It is
explicitly **NOT spaced repetition**; "reminding" comes from a cumulative **known set**
(spiral review + a "Previously…" recap built from prior units). See `docs/ARCHITECTURE.md`
and ADR-005.

Progress lives in the student's browser (`localStorage`) and is moved/backed up with
**Export progress** / **Import progress** (JSON download/upload, merge on import) —
no server write, no git sync. See ADR-019 and `docs/GIT-SYNC.md`.

## 2. Repository layout

```
lang-research/                      # authoring hub (THIS repo)
  AGENTS.md                         # ← you are here
  handover.md                       # live session handover
  docs/                             # design docs (see § Documentation map)
  engine/                           # reusable engine source (language-agnostic)
  courses/
    biblical-hebrew-davidson/       # public-domain-based course (+ vendored engine at release)
    biblical-hebrew-oer/            # CC BY-SA 3.0 OER-based course
    ...
  build/                            # content-generation scripts; build/_sources/<book>/manifest.json lists fetched scans
  exwb/                             # Exercise Workbench: standalone exercise-extraction/review tool
  scripts/                          # release-course, sync-engine, validate, run
```

The project has three separate parts (decided 2026-11-06; P10-T6 done 2026-11-10 by mapping them
onto the existing folders — no folder moves). `tests/test_layout.py` enforces the boundaries.

| Part | Folders | README | Run | May depend on |
|---|---|---|---|---|
| **1. Course app** (student runtime) | `engine/`; per course: `course.json`, `vocab.json`, `units/NN.json`, `authored/`, `prerequisites/`, `app/` | `engine/README.md` | `python scripts/run courses/<course>`; site: `python scripts/build-site` | only its own files (engine imports stay inside `engine/`) |
| **2. Course authoring** | `build/`; per course: `content/` (canonical text), `units.json`, `exercises/`; `site/site.json` | `build/README.md` | `python build/materialize.py --course courses/<course>` then `python scripts/validate courses/<course>` | writes part-1 data; never imports `exwb/` |
| **3. Exercise extraction** | `exwb/` (curated output in `exwb/curated/`) | `exwb/README.md` | `cd exwb && python3 -m exwb serve myproject` | stdlib only; reads `engine/keyboard.js`, `dom.js`, `keyboards/he_IL.js` over HTTP for its on-screen keyboard; its `exwb.db` is git-ignored (snapshot with `exwb export --all`) |

Shared tooling (release, tests, audit) lives in `scripts/` (`scripts/README.md`). exwb output reaches
a course only through an explicit authoring step (`build/exwb_to_authored.py`, P9-T6), never by the
engine reading exwb.

## 3. How to run things

> **NOTE:** These commands are the *target* interface. Not all scripts exist yet — check
> `docs/STATUS.md` for what is implemented before assuming a command works. If a command
> referenced here does not exist, that itself is a bug to fix (update AGENTS.md or
> implement the script).

```bash
# Run the engine against a course locally (opens the app in a browser)
python scripts/run courses/biblical-hebrew-davidson

# Run a released course with Docker (the student distribution path)
sh dist/biblical-hebrew-davidson/run.sh


# Generate/enrich lesson copy for a course (authoring phase; uses approved OER sources)
python build/generate-lessons.py --course courses/biblical-hebrew-davidson

# Fetch approved OER Hebrew sources into the local build/_oer/ cache (P6-T1)
python build/fetch_oer.py --source all --course courses/biblical-hebrew-davidson

# Canonical plaintext <-> JSON (content/ is the source of truth; JSON is derived)
python build/textify.py --course courses/biblical-hebrew-davidson      # JSON -> content/
python build/materialize.py --course courses/biblical-hebrew-davidson  # content/ -> JSON

# Validate all data files for a course against schemas
python scripts/validate courses/biblical-hebrew-davidson

# Browser regression test (drives the app headlessly; asserts drills + unlock flow)
# Requires: .venv/bin/pip install playwright && .venv/bin/python -m playwright install chromium
python scripts/e2e.py courses/biblical-hebrew-davidson --units 2

# Authored-exercise regression (render/grade + session mix)
python scripts/e2e.py courses/biblical-hebrew-davidson --authored

# URLs, seeded sessions that resume, item codes, per-block progress
python scripts/e2e.py courses/biblical-hebrew-davidson --routes

# Accessibility regression (keyboard navigation + on-screen Hebrew keyboard)
python scripts/e2e.py courses/biblical-hebrew-davidson --accessibility

# Generic-engine acceptance (synthetic non-Hebrew course + progress restore)
python scripts/e2e-synthetic.py

# Docker distribution regression (fresh release served read-only by Docker)
python scripts/e2e-docker.py biblical-hebrew-davidson

# Build the hosted static site, and test it (served under /coursekit/ like GitHub Pages)
python scripts/build-site --out _site
python scripts/e2e-site.py

# Check a tree is safe to publish (P10-T2; fails on private material, big files, secrets)
python scripts/public-audit --summary


# Download the public-domain Davidson scans (exwb/build inputs; never committed)
python scripts/fetch-sources davidson

# Stamp a self-contained forkable repo for a course (content + vendored engine)
python scripts/release-course biblical-hebrew-davidson
```

## 4. Mandatory checks before declaring work "done"

**Definition of Done** — ALL of the following must hold before a task may be marked Done:

1. The task's **acceptance test** (from `docs/ROADMAP.md`) passes.
2. **Lint / typecheck / tests** pass — `ruff check build/ scripts/` for Python, and for any
   engine/UI change run `python scripts/e2e.py courses/biblical-hebrew-davidson --units 2` (the
   browser regression test that asserts the teach→drill→unlock loop). If the change area
   has no test yet, that's a blocker — raise it, don't skip.
3. **Docs are updated** per [§ Keep the docs up to date](#keep-the-docs-up-to-date--mandatory).
4. `docs/STATUS.md` and `handover.md` reflect the new state.
5. No secrets, credentials, or licensed-non-OER text are committed.

Saying "I'll update the docs later" is ** grounds for reverting the work**. Later never comes.

## 5. <a id="keep-the-docs-up-to-date--mandatory"></a>Keep the docs up to date — MANDATORY

**Docs are source of truth, not afterthoughts. This rule is non-negotiable.**

Any change that touches something a doc describes MUST update the corresponding doc(s)
**in the same session, in the same change**. There are no exceptions for "small" changes.

### Why this is severe
This project is explicitly designed to be handed off across AI sessions and human
collaborators. A code change without doc sync is an **active lie** to the next agent, and
has historically caused wasted hours. Therefore: **staleness is a bug with the same
severity as a failing test.** An out-of-date doc is not "tech debt" — it is a defect that
must be fixed before the task that caused it is considered done.

### What must be updated, and when

| Change you made | Doc(s) you MUST update in the same change |
|---|---|
| Start / progress / finish any task | `docs/STATUS.md` (state table) + `handover.md` |
| End of a session | `handover.md` (last done / next up / resume command) |
| Schema, JSON contract, or data shape | `docs/DATA-MODEL.md` |
| Behaviour, module structure, view flow, runtime model | `docs/ARCHITECTURE.md` |
| Exercise type added/changed; generator/grader/render contract | `docs/EXERCISE-TYPES.md` |
| Knowledge graph / teaches-assumes / known-set logic | `docs/KNOWLEDGE-GRAPH.md` |
| Extraction pipeline, OER sources, lesson generation | `docs/CONTENT-GENERATION.md` |
| Progress persistence (localStorage, export/import) | `docs/GIT-SYNC.md` + ADR-019 |
| Script/font/keyboard/RTL/transliteration config | `docs/I18N-SCRIPTS.md` |
| Plan changes, new tasks, reprioritization | `docs/ROADMAP.md` |
| A new decision is made or an old one superseded | Add or edit its line in §12 Decisions (no ADR files) |
| Course content availability changes | `docs/STATUS.md` inventory table |
| Operating conventions change | THIS file (`AGENTS.md`) |


### Pre-done doc check (mandatory)
Before marking **any** task Done: **re-read** every doc the task affects and confirm the
docs still match reality. If they don't, **fix the docs first** — the task is not done.

### Reviewer / second-agent check
If you are reviewing another agent's work (or resuming a session), the first action is to
spot-check `docs/STATUS.md` and `handover.md` against the actual code. If they disagree,
**do not proceed** — reconcile the docs first, then continue.

### Enforcement
- A PR/change with code diffs but no doc diffs (where docs were owed) **will be rejected**.
- "Docs are out of date" is a valid, encouraged reason to block a task.
- If you are unsure whether a change requires a doc update: **err on the side of updating.**

## 6. Forbidden actions

- **Do NOT commit copyrighted material, scans, PDFs or files over 1 MB.** Public-domain scans are
  downloaded with `python scripts/fetch-sources <book>` into git-ignored folders.
  `python scripts/public-audit` must pass before any commit.
- **Do NOT edit a vendored engine in a released course repo in situ.** Edit `engine/` in the
  hub, then run `scripts/sync-engine` to re-vendor. Editing a vendored copy creates drift.
- **Do NOT commit unless explicitly asked** by the user. Stage only intended files.
- **Do NOT push, create PRs, force-push, or amend unless explicitly asked.**
- **Do NOT introduce secrets, tokens, or credentials** into the repo or browser code.
  Progress stays in the browser; it leaves only through the student's own Export (ADR-019).
- **Do NOT reproduce copyrighted text** in *engine/course content shipped to students*.
  Lesson generation paraphrases/transforms owned material and uses only approved OER sources
  (see ADR-004 + `docs/CONTENT-GENERATION.md`).
- **Do NOT add a spaced-repetition scheduler, review queue, or per-card due-date system.**
  This is a founding constraint (ADR-005). "Remind" via known-set spiral + recap only.
- **Do NOT assume a library is available.** Check existing usage / `package.json`-equivalent
  before importing. The engine is deliberately dependency-light (vanilla JS).

## 7. Conventions

- **Engine**: vanilla JS + ES modules, no build step, no npm install to run. Browser-only.
  `localStorage` is the only progress store; Export/Import moves it between browsers (ADR-019).
- **Build/extraction/content-gen**: Python 3, stdlib + `pypdf` (already vetted). New deps
  require a note in `docs/CONTENT-GENERATION.md`.
- **JSON**: 2-space indent, UTF-8, trailing newline. Hebrew/Greek text inline (not escaped).
- **Task IDs**: `<P><phase>-T<n>` from `docs/ROADMAP.md`. Reference them in commit messages
  and PR titles once git is initialized (P1-T1): e.g., `P10-T3: build the public snapshot`.
- **Doc dates**: always **ISO `YYYY-MM-DD`** when a date appears in any doc. Never use
  relative date words ("today", "tomorrow", "yesterday", "last week", "recently") to
  reference dates — they go stale and mislead the next agent. Use a "Last updated:
  YYYY-MM-DD" line (or the ISO date itself) instead.
- **No comments in code unless asked.** Docs carry the explanation; code stays clean.

## 8. How to add a course

1. Confirm source material exists (or will be OER-only) — update `docs/STATUS.md` inventory.
2. `cp -r courses/_template courses/biblical-< language >-< level >`.
3. Author `course.json` (language, script/font/keyboard, units[], prerequisites).
4. Author `content/vocab.csv` + `content/chapters/NN.md` (`docs/CONTENT-PORTABILITY.md`), then
   `python build/materialize.py --course courses/<name>`.
5. Author units, mark `teaches`/`assumes` items (see `docs/KNOWLEDGE-GRAPH.md`).
6. Run `scripts/validate <name>` then `scripts/release-course <name>`.

## 9. How to add an exercise type

1. Read `docs/EXERCISE-TYPES.md` for the plugin contract.
2. Add `{id, generate, render, grade}` to `engine/exercise-types/`.
3. Register it in the type registry.
4. Add authored instances / generator config that use it.
5. Update `docs/EXERCISE-TYPES.md` (catalog + contract if changed) — **mandatory**.

## 10. Documentation map

| Doc | Purpose |
|---|---|
| `AGENTS.md` (this file) | Operating manual; how to work here |
| `handover.md` | Session continuity (last done / next up / resume) |
| `docs/ROADMAP.md` | Phased plan with task IDs + acceptance tests |
| `docs/STATUS.md` | Live task-state table + materials inventory |
| `docs/ARCHITECTURE.md` | Two-layer engine/course split; runtime; views; states |
| `docs/DATA-MODEL.md` | Generic + per-language JSON schemas |
| `docs/EXERCISE-TYPES.md` | Plugin contract + type catalog |
| `docs/KNOWLEDGE-GRAPH.md` | teaches/assumes, known set, cross-level continuity |
| `docs/CONTENT-GENERATION.md` | Extraction + lesson generation + OER allowlist |
| `docs/AI-EXAMS.md` | AI-assisted exams: prompts, exam workflow, rubric, answer formats, ideas (P5) |
| `docs/CONTENT-PORTABILITY.md` | Plaintext content formats (`.md` chapters, `.csv` word lists) |
| `docs/RESCUE-PLAN.md` | Active rescue scope, gates, and document change matrix |
| `docs/GIT-SYNC.md` | Progress persistence: localStorage + export/import (git sync retired) |
| `docs/TESTING-STUDENT.md` | Student point-of-view testing: `e2e-fork.py` + manual published-repo walk-through |
| `docs/MANUAL-TEST.md` | Copy-paste manual walkthrough (Docker + dev server) with a full checklist |
| `docs/I18N-SCRIPTS.md` | Per-script font/keyboard/RTL/translit config |
| §12 of this file | Decisions (one line each; the ADR-NNN labels other docs cite) |


## 11. Current phase

See `docs/STATUS.md` and `docs/ROADMAP.md`. The repository holds two open courses, both
**preview** quality: `biblical-hebrew-davidson` (built on public-domain grammars; lesson prose
CC BY-SA 3.0) and `biblical-hebrew-oer` (CC BY-SA 3.0). The app is a static site (ROADMAP P10)
and Biblical Greek from open sources is the reach goal (P11).

The engine/course split, content portability, no-SRS constraint and copyright guardrails remain
in force. Release gates (`docs/RESCUE-PLAN.md`): synthetic course, Davidson Unit 1 and Units 35 and 38 (Qal Qatal, Qal Yiqtol),
OER, release, progress restore, authored exercises, and human content review.

## 12. Decisions

One line per decision; the ADR numbers are the labels other docs cite. There are no separate
ADR files any more: to make or change a decision, add or edit its line here.

| Id | Decision |
|---|---|
| ADR-001 | Two layers: a language-agnostic `engine/` (vanilla JS, no build step) and per-course content; developed together in this hub, released as a self-contained course repo with a vendored engine. |
| ADR-002 | Retired (attempt-branch progress); replaced by ADR-019. |
| ADR-003 | Retired (git transport); replaced by ADR-019. No tokens in the browser still holds. |
| ADR-004 | No copyrighted text shipped to students; extra material only from open sources with attribution and license per item. |
| ADR-005 | No spaced repetition: a visible unit map, teach → drill → unlock; reminding only via recap, known-set review and an optional warm-up. |
| ADR-006 | One generic vocabulary schema (`docs/DATA-MODEL.md`); per-language column maps; extra fields in `extra`. |
| ADR-009 | Canonical content is plain text (`content/`: Markdown chapters, CSV word lists); JSON is derived by `build/materialize.py`. |
| ADR-010 | Rescue on branch `rescue/usable-course`, with tests on a synthetic course and real benchmark units. Expanding the exercises is not paused (ADR-022). |
| ADR-011 | Retired (Docker as the main student path); Docker remains an optional read-only static server. |
| ADR-013 | `courses/biblical-hebrew-oer` is a separate CC BY-SA 3.0 course from the open textbook; nothing from the private courses. |
| ADR-014 | `courses/biblical-hebrew-davidson` is a separate course built on public-domain Davidson + McFadyen's Key. |
| ADR-015 | Opt-in course features (`parsing`, `diagnostics`, `reviewWarmup`, session sizes); unit-level skill counts, no per-card state. |
| ADR-016 | Davidson covers the whole grammar, one topic per unit (79 units since 2026-11-11); noun forms taught by pattern family. |
| ADR-017 | Every Davidson exercise links to its scan page (exercise and key) on archive.org. |
| ADR-018 | Every Davidson exercise block is inventoried from the grammar itself (no caps); curated by hand in exwb. |
| ADR-019 | Progress lives only in the browser (`localStorage`), moved with Export/Import (merge keeping the best). |
| ADR-020 | Public repo `fatihd/coursekit` (fresh history, open courses only, MIT code, CC0 exwb data, GitHub Pages); changes only via `scripts/make-public-snapshot`. |
| ADR-021 | Davidson follows the 22nd edition (1923) only. |
| ADR-022 | The course vision of §0: exercise ladder, sentences from the start, per-sentence placement, typed translation, no transliteration, a large exercise corpus built offline (static course data, no live agent). |
