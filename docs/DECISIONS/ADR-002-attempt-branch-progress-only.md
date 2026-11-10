# ADR-002 — Attempt branch carries progress only

> **Superseded by ADR-019 (2026-11-06):** progress is browser-only with export/import; attempt branches were removed.

Date: 2026-08-12. Status: Accepted.

## Context

A student's progress (`progress/progress.json`) is canonical to them and must persist across
devices/sessions via their fork. The question: what else rides on the attempt branch —
lesson edits? engine patches? content tweaks?

## Decision

Attempt branches (`attempt/<ISO>`) carry **`progress/progress.json` only**. Lessons are
authored in the offline content-generation phase (author-side), not in-app. No in-app
lesson editor ships; no content/engine changes are committed via the app.

## Consequences

- **Pro**: attempt branches are tiny and reviewable; no risk of a student accidentally
  diverging course content or engine; the fork's `main` stays the canonical course.
- **Pro**: keeps `gitsync.js` trivial — one file, one commit, one push.
- **Con**: students who want to annotate/fix lesson copy must do so out-of-band (send a PR
  to the course, or fork-and-edit manually). Acceptable per user choice.
- Reopens cleanly: if a richer "progress + notes" model is requested later, add a
  `notes.json` to the payload without changing the branch model.