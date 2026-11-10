# Rescue Plan — Usable Course
> Release-quality contract for the open courses. Gates re-based 2026-11-09 (ROADMAP P10-T5,
> ADR-010 amendment): the benchmarks are the Davidson and OER courses.

## 1. Objective

> A student can open a course (hosted site or released copy), study a substantive grammar
> lesson, complete real authored exercises, close and reopen the app without losing progress,
> and move progress to another browser with Export/Import.

Davidson Unit 1 (and OER Unit 1) is the beginner smoke test. Davidson **Unit 21** (Qal Qatal)
is the primary content benchmark; **Unit 22** (Qal Yiqtol) is the later grammar check.

## 2. Non-negotiable boundaries

- The engine remains language- and course-agnostic; no unit-specific runtime branches.
- No SRS scheduler, due dates, review queue, or per-card retention state.
- Content remains canonical in `courses/<course>/content/`; runtime JSON remains derived.
- Student-facing lesson content must be human-reviewed, not merely schema-valid.
- Only open material: `python scripts/public-audit` passes; scans are fetched, never committed.

## 3. Work sequence

- **R1 — Truthful contracts:** docs describe actual behaviour (done).
- **R2 — Runtime foundations:** launch, release, browser-only progress with Export/Import
  (ADR-019), read-only Docker/static serve (done).
- **R3 — Meaningful courseware:** Davidson Units 21–22 lessons and their authored/parsing
  exercises reviewed for accuracy; exwb exercises wired into the course (ROADMAP P9-T6).
- **R4 — Student acceptance:** the acceptance tests below pass on the exact release / site.

## 4. Acceptance tests

### Platform contract

- `scripts/e2e-synthetic.py`: a synthetic two-unit non-Hebrew course launches, completes a
  drill, exports, imports into a fresh browser, merges, and rejects another course's file.
- `scripts/e2e-fork.py <course>` and `scripts/e2e-docker.py <course>`: a fresh release runs
  with its vendored engine only, read-only.
- Local use needs no account, remote, or credentials.

### Course contract

- Davidson Unit 1 renders Hebrew and the on-screen keyboard (`e2e.py --accessibility`).
- Davidson Units 21–22 present coherent grammar lessons and grade their parsing exercises.
- `e2e.py courses/biblical-hebrew-davidson --units 56` and `courses/biblical-hebrew-oer
  --units 20` complete; `--authored`, `--exercise-types`, `--keyboard` pass.

### Human checks

- A non-developer can follow the README.
- A human reviewer approves Davidson Units 21–22 and a sample of OER units.
- A keyboard-only user can operate the roadmap, lesson gate, and drill.
- Errors explain the next action in ordinary language.

## 5. Explicitly deferred

- Additional languages before the open Greek plan (ROADMAP P11).
- More exercise types beyond what the courses need; AI exam automation.
- Visual redesign beyond clarity, accessibility, and mobile usability.
