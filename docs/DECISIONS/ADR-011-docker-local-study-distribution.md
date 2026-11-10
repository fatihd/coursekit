# ADR-011 — Docker local-study distribution

> **Amended by ADR-019 (2026-11-06):** Docker is an optional read-only static server; progress lives in the browser (export/import), not in the mounted folder, and there is no attempt-branch sync.

Date: 2026-08-29. Status: Accepted.

## Context

The browser application requires HTTP for module and JSON loading and requires a local
server for file-backed progress. Requiring Python, Node, npm, and Git from a student is
not an acceptable first-use experience. A GitHub ZIP also has no Git remote or
credentials for attempt-branch sync.

## Decision

Released courses include a Docker image definition and platform launchers. The primary
student path is:

1. Download and extract a ZIP.
2. Run `run.sh`, `run.command`, or `run.bat` with Docker Desktop installed.
3. Open the localhost URL printed by the launcher.
4. Persist progress in the mounted course folder.

The ZIP/local-study path is local-only. Attempt-branch synchronization remains an
optional advanced path for students who clone a fork and provide a usable `origin` and
Git credentials. The container exposes only a loopback host port and receives no host
credentials by default.

## Consequences

- Students need Docker Desktop, but no host Python, Node, npm, or Git for local study.
- The course folder must be mounted writable for progress persistence.
- Direct `file://` opening is not supported.
- Cross-platform launchers and a Docker-capable regression test become release gates.
- Git credential forwarding is intentionally excluded from the default ZIP path.
