# ARCHITECTURE

> Two-layer split: a reusable, language-agnostic **engine** + per-course **content repos**.
> The hub (`lang-research`) develops engine + all courses together; `scripts/release-course`
> stamps a self-contained forkable repo = course content + vendored engine. See ADR-001.

## 1. Runtime model

- **Local web app.** Vanilla JS + ES modules. No build step, no npm install.
- The app is a static site: any static server or host works (hosted copy: `scripts/build-site`;
  the bundled Docker launcher
  `run.sh`/`run.command`/`run.bat` and `scripts/run` are plain static servers). Direct
  `file://` opening is not supported because the app loads course data with `fetch()`.
- State: `localStorage` is the only progress store; **Export/Import progress** (JSON
  download/upload, merge on import) backs it up and moves it between browsers (ADR-019).
- Fonts/keyboards are configured per script (see `docs/I18N-SCRIPTS.md`).

This is explicitly **NOT spaced repetition** (ADR-005). Progress is a visible unit map;
"reminding" = cumulative **known set** + spiral review + "Previously…" recap.

## 2. Layer 1 — Engine (`engine/`, language-agnostic)

| Module | Responsibility |
|---|---|
| `engine/main.js` | Bootstrap: load `course.json`, route to views, mount keyboard/font config |
| `engine/store.js` | Progress state in localStorage; `exportProgress` / `importProgress` / `mergeProgress`; unit states |
| `engine/views/roadmap.js` | 30-unit path in 3 parts; node states; soft-linear highlight of recommended next |
| `engine/views/lesson.js` | Paged teaching: renders typed blocks (headed prose, table, vocab, callout, paradigm); "Mark lesson read → start drills" gate |
| `engine/views/drill.js` | One item at a time, immediate feedback, end-of-session score → unlock next; manages question focus and Enter-to-advance after checking; an item's optional `hint` shows behind a "Show hint" button before answering, its `explain` appears with the feedback (P9-T7); calls a type's optional `annotate` after grading to mark the answer in place (P9-T8) |
| `engine/views/lesson.js` | Also renders the optional warm-up (weak prior units) when `features.reviewWarmup` is on (ADR-015) |
| `engine/exercise-types/` | Plugin registry. Each plugin = `{id, generate(params, pool), render(item), grade(item, answer)}` (see `docs/EXERCISE-TYPES.md`) |
| `engine/keyboards/` | On-screen keyboards per script (`he_IL`, `el_GR`, `arc`) for typing niqqud/diacritics |
| `engine/translit/` | Per-language transliteration schemes for input matching |
| `engine/fonts/` | Bundled OFL fonts: Ezra SIL / SBL Hebrew (Hebrew), SBL Greek / GFS Didot (Greek), square Aramaic |
| `engine/config/` | Language-specific runtime config loaded from `course.json`: script direction, font, keyboard, translit scheme |

**Implementation status (P3-T1..T5):** `main.js` (bootstrap + navigation),
`store.js` (load/save/state), `views/roadmap.js` (unit map), `views/lesson.js`
(typed blocks + vocab cards + read gate + recap), `views/drill.js` (drill session),
`dom.js` (el/scriptSpan helpers), `session.js` (session builder), `knowledge.js`
(known set + recap + spiral), and the exercise-type registry (11 types) are
implemented. The `app/` shell lives in `courses/<course>/app/` (`index.html` +
`styles.css`). `scripts/run` serves the course over HTTP and symlinks the hub
`engine/` into the course dir for development (the symlink is gitignored; real
vendoring happens at `release-course` time).

## 3. Layer 2 — Course content repo (`courses/<course>/`, what students fork)

```
courses/biblical-hebrew-davidson/
  course.json                  # manifest (see docs/DATA-MODEL.md)
  vocab.json                   # generic-schema lexicon
  units/NN.json                # lesson content + teaches/assumes + authored exercises + generator config
  prerequisites/knowledge.json # snapshot of items assumed from earlier levels
  engine/                      # vendored engine (pinned; via scripts/sync-engine)
  app/                         # the HTML/CSS shell that loads the vendored engine + course data
  build/                       # per-course extraction + content-gen scripts (author-side only)
  source/                      # original PDFs (author-side only; stripped at release)
```

`exercises/NN.json` and `answer-key/NN.json` are author-side workbook extraction artifacts;
they are not included in student releases. Only `authored/NN.json` exercises are consumed by the
student app: hand-written items, or (Davidson) items generated from the hand-checked exwb
transcriptions by `build/exwb_to_authored.py` (P9-T6).

A `release-course <name>` output strips `build/`, `source/`, author-side `units.json`, and
textbook page references, vendors a pinned `engine/`, adds Docker launchers, creates an
initial Git commit, and produces a self-contained artifact. The forked or extracted repo
is fully self-contained for local study.

## 4. Views and states

### Unit states (roadmap node)

- **Locked** — not yet reachable via the recommended path (soft: still openable in browse
  mode, but visually de-emphasized).
- **Available** — the recommended next unit (or any unit a soft-linear policy allows).
- **In-Progress** — lesson read or drills started but not passed.
- **Done** — drills passed; next unit becomes Available.

> Per ADR-005 + user decision, progression is **soft-linear**: the roadmap highlights the
> recommended next, but any unit is openable. "Pass" = completing a drill session to
> threshold; unlocks the *recommended* next, not a hard gate.

### View flow

```
Roadmap  ──▶  Unit overview (with "Previously…" recap)  ──▶  Lesson (paged)
                                                            │
                                                            ▼ "Mark lesson read"
                                                          Drill session  ──▶  Score  ──▶  unlock next
                                                            ▲
                                                            │  (optional)
Review (Warm-up) ◀── anytime, from roadmap  ────────────────┘
```

### Lesson gate

The "Mark lesson read → start drills" gate is **soft**: it encourages the teach→drill
order but does not hard-block drilling. Drilling without reading the lesson is allowed;
the gate just tracks `lessonRead` in progress.

## 5. Progress and the known set (see `docs/KNOWLEDGE-GRAPH.md`)

- Every unit declares `teaches: [itemId…]` and `assumes: [itemId…]`.
- The **known set** = union of `teaches` over all **completed units across all levels** the
  student has progress for, plus the course-shipped `prerequisites/knowledge.json` snapshot.
  **Implemented 2026-08-17**: the engine builds the known set from the **running course's**
  completed units only (`engine/knowledge.js`); the snapshot ships as the standing
  cross-level data contract (see `docs/KNOWLEDGE-GRAPH.md` §4) — merging snapshot item ids
  into the running known set is deferred.
- The known set drives:
  - **"Previously…" recap** on unit overviews (drawn from recently completed units'
    summaries).
  - **Spiral distractors** in drills (older vocab resurfaces as wrong answers as you
    advance — the non-SRS "remind").
  - **Optional Warm-up review** sessions.
- Earlier-level vocab/grammar is **assumed known**; generators never re-teach known items,
  only re-surface them.

## 6. Exercise engine

- Plugin registry keyed by type id (see `docs/EXERCISE-TYPES.md`).
- Authored workbook instances and generated drills share the **same renderers**.
- A drill session = engine iterates an exercise list (authored + generated mix per unit's
  generator config), calling `render` per item and `grade` on the student's answer.
- Distractor pool = **known set** filtered by the generator's params; difficulty = lookback
  depth (how far back the pool reaches).

### Opt-in features (ADR-015)

`course.json.features` turns on grammar diagnostics without changing existing courses:

- `parsing` adds `parse-noun`, `parse-verb`, and `produce-form` items to generated sessions
  (gated by unit range: noun parsing from unit 9, verb parsing from unit 16).
- `diagnostics` records `progress.skills[<unit>] = { correct, attempts }` and shows a
  "Review Unit N" link on a wrong answer.
- `reviewWarmup` renders an optional warm-up of weak prior units on the lesson view.
- `targetItems` / `reviewItems` set session size and the number of front-loaded review items.
- `authoredPerSession` caps how many of a unit's authored items one session draws (a fresh
  random sample each session; default: all). Davidson uses 10, because its units carry up to
  86 transcribed exercises (P9-T6).

These flags flow `main.js → buildSession` and into `views/drill.js` / `views/lesson.js`;
when absent (all existing courses), the prior drill mix and progress shape are unchanged.

## 7. Persistence (ADR-019, `docs/GIT-SYNC.md`)

- `localStorage` (`lang-research.progress.<courseId>`) is the only store, written on every
  change; the app requests persistent storage.
- Roadmap **Export progress** downloads `<courseId>-progress-<date>.json`; **Import
  progress** validates the file and merges it keeping the best of both sides.
- No server write, no git, no tokens; the roadmap shows when progress was last exported.

## 8. Release / forkability

- `scripts/release-course <name>`:
  1. Validate the course data (`scripts/validate`).
  2. Copy the course content into `dist/<name>/`.
  3. Vendor a pinned `engine/` into `dist/<name>/engine/` (full copy, self-contained).
  4. Strip author-side `build/` and `source/`.
  5. Add Dockerfile and platform launchers for ZIP/local study.
  6. Initialize `dist/<name>/` as a new git repo with an initial commit.
- `scripts/release-course <name> --site` writes a static-site copy (no git, no Docker launchers,
  no `scripts/`), used by the hosted site.
- **Hosted site (P10-T8):** `scripts/build-site [--out _site]` reads `site/site.json`, releases each
  listed course into `_site/<course-id>/` (`--site`), and writes a landing page (`index.html`),
  per-course redirects to `app/`, `404.html` and `.nojekyll`. All links are relative, so the site
  works under any base path (GitHub Pages project path `/coursekit/`, later Cloudflare Pages).
  Each course keeps its own `localStorage` key, so progress stays per course on a shared origin.
  The public repo deploys it with `.github/workflows/pages.yml` (audit → unit tests → validate →
  build → Pages); tested by `scripts/e2e-site.py`.
- `scripts/sync-engine` re-vendors the latest `engine/` into existing course repos at a
  pinned commit (to fix drift; never edit a vendored copy in situ — AGENTS.md §6).

## 9. Constraints (founding)

- No SRS / review queue / per-card due dates (ADR-005).
- No tokens in the browser; git transport is local CLI only (ADR-003).
- No reproduction of copyrighted text; lesson copy is paraphrased and OER-enriched (ADR-004).
- Engine stays dependency-light: vanilla JS, no build step (ADR-001).
