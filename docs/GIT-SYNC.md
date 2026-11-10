# GIT-SYNC (retired) — progress persistence

> Git attempt-branch sync was removed on 2026-11-06 (ADR-019, superseding ADR-002/003).
> This page now describes how progress is kept. Last updated: 2026-11-06.

## Model

- Live state: browser `localStorage`, key `lang-research.progress.<courseId>`, written on
  every change by `engine/store.js` (`saveProgress`). The app requests persistent storage
  (`navigator.storage.persist()`).
- **Export progress** (roadmap): `exportProgress` downloads
  `<courseId>-progress-<YYYY-MM-DD>.json` and records `lastExportedAt`.
- **Import progress** (roadmap): `importProgress` validates the file (schema
  `progress-v1.json`, same `courseId`) and merges it with `mergeProgress`:
  per unit the furthest state (done > in-progress) and best score, `lessonRead` OR-ed,
  latest `lastPlayed`; `currentUnit`/`xp` max; `knownSet` union; per skill the tally with
  more attempts. Importing never loses work from either side.
- The roadmap status line shows "Last exported …" / "you have made progress since" /
  "stored in this browser only".

## What is gone

- No `progress/progress.json` in course folders or releases; no `POST /__api/*`; no
  `engine/gitsync.js`; no attempt branches. `scripts/run` and the Docker launcher are
  static servers only.

## Security

- No tokens or credentials anywhere; progress files contain only learning progress.
