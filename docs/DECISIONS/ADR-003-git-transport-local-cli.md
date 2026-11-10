# ADR-003 — Git transport is local CLI (no tokens in browser)

> **Superseded by ADR-019 (2026-11-06):** no git transport remains; the no-tokens-in-the-browser principle still holds.

Date: 2026-08-12. Status: Accepted.

## Context

The app is a local web app with no backend. To push attempt branches to a student's fork,
something must authenticate to the git host. Options: GitHub API + PAT, OAuth, or local
`git` CLI.

## Decision

Use **local `git` CLI** exclusively. The browser app shells out to `git` on the local clone
(via `engine/gitsync.js`) using the OS's configured credentials. No GitHub API, no PAT
field, no tokens in the browser, no fetch library.

## Consequences

- **Pro**: zero credentials in browser code/storage — a strong security posture; matches
  the "local-first, no backend" architecture (ADR-001).
- **Pro**: works with any git host (GitHub, GitLab, self-hosted), not just GitHub.
- **Con**: requires the student to have cloned their fork locally and have git credentials
  configured (SSH key / credential helper). If not, save degrades to localStorage-only
  with a clear message. Acceptable; documented in `docs/GIT-SYNC.md`.