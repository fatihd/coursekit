# ADR-019 — Browser-only progress with export/import

Date: 2026-11-06. Status: Accepted. Supersedes ADR-002 and ADR-003; amends ADR-011.

## Context

Progress used to be kept three ways: `localStorage` (live), `progress/progress.json`
written through the local server (`POST /__api/progress`), and an optional git
attempt branch pushed to the student's fork (`POST /__api/save`). The server write and
git sync are why students needed Docker with a writable mount (or Python), a cloned fork,
git and credentials, and they leaked dev-run state into tracked course folders.

## Decision

- `localStorage` (key `lang-research.progress.<courseId>`) is the only live store.
- **Export progress** downloads the progress object as
  `<courseId>-progress-<YYYY-MM-DD>.json` (same `progress-v1.json` schema, plus
  `lastExportedAt`).
- **Import progress** reads such a file, rejects other courses/schemas with a clear
  message, and **merges keeping the best**: per unit the furthest state and best score,
  union of the known set, max XP and current unit, the larger skill tally.
- The app calls `navigator.storage.persist()` and shows "last exported / progress made
  since" on the roadmap so students keep a copy.
- No server write, no git sync, no `progress/` folder in courses or releases. The app is a
  static site: `scripts/run` and the Docker launcher are plain static servers (Docker
  mounts the course read-only); static hosting (e.g. GitHub Pages) also works.

## Consequences

- Students need only a browser (plus any static server/host); no Docker requirement for
  progress, no git, no credentials, no tokens in the browser.
- Progress is per browser/origin and can be cleared by the browser (e.g. Safari's storage
  eviction); export is the backup and the way to move between devices.
- Rejected alternatives: IndexedDB (same trade-offs, more code), File System Access API
  autosave (Chromium-only; possible later enhancement), cloud sync via Gist/Drive (needs
  tokens/OAuth in the browser). A copy-paste progress code could be added later on top.
- Tests: `scripts/e2e-synthetic.py` (export → fresh browser → import → merge → wrong-course
  rejection), `scripts/e2e-fork.py` (release → clone → drill → export → import),
  `scripts/e2e.py` (stored progress), `scripts/e2e-docker.py` (read-only static serve).
  `scripts/e2e-save.py` was removed.
