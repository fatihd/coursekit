# ADR-005 — Non-SRS progression model (visible course map + known set)

Date: 2026-08-12. Status: Accepted. **Founding constraint.**

## Context

The user explicitly rejected spaced repetition ("that is fucking BORING") and wants the
experience to be a **visible course plan** progressing through units, like a real course —
teach → drill → unlock next. "Reminding" must exist (you forget material) but must NOT be
a per-card scheduler, review queue, or due-date system.

## Decision

- The core experience is a **visible unit roadmap** (30 units in 3 parts), with progression
  measured by **units conquered**, not cards reviewed.
- Each unit: **teach first** (lesson), **then drill**, then unlock the next.
- "Reminding" is provided by:
  1. A **"Previously…" recap** on each unit's overview, built from recently-completed
     units' summaries.
  2. **Spiral distractors** in current drills, drawn from the cumulative **known set**
     (older vocab resurfaces as wrong answers / prompts as you advance).
  3. An **optional Warm-up** review session drawn from the known set — available anytime,
     not scheduled.
- The known set grows from completed units across levels; earlier-level vocab/grammar is
  **assumed known**, never re-taught, only re-surfaced.

## Consequences

- **Pro**: matches user intent; no SRS scheduler, no review queue, no per-card due dates.
- **Pro**: simpler engine (no scheduler state, no interval math, no per-card retention
  modeling) — fits the vanilla-JS, no-backend constraint.
- **Con**: less optimized forgetting-curve coverage than SRS; accepted (the point is the
  course feel, not max retention efficiency).
- Hard rule (AGENTS.md §6): never add a spaced-repetition scheduler, review queue, or
  per-card due-date system. Recap + known-set spiral + Warm-up cover "remind".