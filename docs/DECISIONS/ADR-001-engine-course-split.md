# ADR-001 — Engine / course split + vendored release

Date: 2026-08-12. Status: Accepted.

## Context

The project targets a **family** of Biblical-languages courses (Hebrew, Greek,
Aramaic A), all sharing one interactive model (visible unit map, teach→drill→unlock,
attempt-branch progress, non-SRS). Students fork **one course** and play it locally.

Two constraints compete:
- **Reusability**: the interactive machinery must not be re-implemented per language.
- **Self-containedness**: a forked course must work offline, one clone, no external engine
  checkout or network dependency.

## Decision

Adopt a **two-layer split**:
- `engine/` — language-agnostic, vanilla JS + ES modules, no build step. Reused across
  every course.
- `courses/<course>/` — per-course content (course.json, vocab, units, exercises,
  knowledge, progress) + an `app/` shell that loads the engine.

Develop both together in the **authoring hub monorepo** (`lang-research`). At release,
`scripts/release-course <name>` stamps a **self-contained forkable repo** = course content
+ a **pinned vendored copy** of `engine/`, with author-side `build/` and `source/` stripped,
initialized as a new git repo ready to fork.

`scripts/sync-engine` re-vendors the latest hub `engine/` into course repos at a pinned
commit (to fix drift; never edit a vendored copy in situ — AGENTS.md §6).

## Consequences

- **Pro**: forks are self-contained (clone + `open index.html`); engine upgrades are a
  vendor bump per course; no runtime submodule/network dependency.
- **Con**: engine changes require re-vendoring per course (script handles it); some
  duplication across released course repos (acceptable — they're pinned).
- Engine must stay dependency-light (vanilla JS) so vendoring is just a file copy.