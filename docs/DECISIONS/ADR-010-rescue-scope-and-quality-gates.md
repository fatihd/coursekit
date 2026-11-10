# ADR-010 — Rescue scope and quality gates

Date: 2026-08-29. Status: Accepted.

## Context

The prototype has substantial extraction, schema, engine, and release work, but its
student-facing claims exceed its verified behavior. The current automated gates mostly
prove that predetermined generic drills can be completed. They do not prove readable
lessons, use of authored exercises, progress restoration, or a fresh release workflow.

Rebuilding in a new repository would discard useful history and make it harder to tell
which decisions remain valid. Continuing feature expansion would compound the gap.

## Decision

Rescue the existing project on `rescue/usable-course`, leaving `main` as the prototype
baseline. The rescue keeps the generic engine/course split and validates it with three
levels of fixtures:

1. A synthetic two-unit course for platform generality.
2. Davidson Unit 1 (and OER Unit 1) for beginner launch, script, and input behavior.
3. Davidson Unit 21 (Qal Qatal), plus Unit 22 (Qal Yiqtol), for substantive grammar instruction.

Early units must be accurate and functional, but their simplicity is not a
release-quality objection for this rescue. (Benchmarks re-based 2026-11-09, ROADMAP P10-T5.)

Release is blocked until a fresh artifact can be launched, a real authored exercise is
played, progress survives restart/recovery, and the meaningful lesson is human-reviewed.

## Consequences

- Existing history and reusable machinery remain available.
- Rescue work can replace implementation inside one branch without contaminating `main`.
- Early alphabet lessons do not consume the rescue's primary content-authoring budget.
- Schema-valid, generated, or automated content is not treated as educationally ready by
  itself.
- New courses, exercise types, AI features, and reference-grammar work are deferred until
  the rescue gates pass.
