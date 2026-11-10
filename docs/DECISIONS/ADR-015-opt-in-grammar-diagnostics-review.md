# ADR-015 — Opt-in grammar diagnostics and review (non-SRS)

Date: 2026-11-03. Status: Accepted.

## Context

The user asked for richer drills (noun and verb parsing, reverse form production, more items
per session), and for the app to surface weak topics and let the student review earlier units
before a new one. ADR-005 forbids any spaced-repetition scheduler, review queue, or per-card
due-date system. These features must therefore be **evidence-based and optional**, not a
scheduling system.

## Decision

1. Add three exercise types — `parse-noun`, `parse-verb`, and `produce-form` — registered in
   the shared engine but generated only for a course that opts in.
2. Add opt-in feature flags on `course.json.features`: `parsing`, `diagnostics`,
   `reviewWarmup`, plus `targetItems` and `reviewItems` session-size knobs.
3. Track aggregate, unit-level correctness in `progress.json.skills` (`{ "<unit>": { correct,
   attempts } }`). There are no intervals, due dates, or per-card state.
4. When `diagnostics` is on, a wrong answer shows a "Review Unit N" link to its source unit;
   when `reviewWarmup` is on, the lesson offers an optional warm-up listing weak prior units.
   Review is always student-initiated and skippable.

## Consequences

- Existing courses (no `features`) keep the exact prior drill mix and progress shape.
- `progress.json` schema gains an optional `skills` object; older progress files remain valid.
- This stays within ADR-005: no scheduler, no queue, no due dates — only aggregate diagnostics
  plus optional, on-demand review.
