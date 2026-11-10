# scripts/

> Hub-level scripts: run, validate, sync-engine, release-course, export-exam. See
> `docs/ARCHITECTURE.md` and `docs/ROADMAP.md` for behavior and acceptance tests.

## Scripts

- `run` — internal HTTP server used by the Docker launcher; host development can run
  `python scripts/run courses/<name>`.
- `run.sh`, `run.command`, `run.bat` — Docker local-study launchers included in released
  artifacts; they mount the course folder and open the localhost app.
- `public-audit` — `python scripts/public-audit [ROOT] [--summary] [--fingerprints FILE]`: check a
  tree is safe to publish (ROADMAP P10-T2, ADR-020). Fails on paths outside
  `scripts/public-allowlist.txt` (or denied by it), banned file types (PDF/DjVu/hOCR/office/archives/DBs),
  files over 1 MB (fonts excepted), private-course ids/names and private source file names, secrets,
  lines whose hash is in a private fingerprint file, and missing required license files (`LICENSE` must be
  MIT). Build a fingerprint file in the private repo with
  `--make-fingerprints OUT --private <private course dirs> --open <open course dirs>`
  (it stores hashes, not text; keep it out of the public repo). Tests: `python3 -m unittest tests.test_public_audit`.
- `fetch-sources` — `python scripts/fetch-sources davidson [--all]`: download the public-domain scan inputs
  listed in `build/_sources/<name>/manifest.json` from the Internet Archive, verify sha256, gunzip `.gz`
  URLs; present files with the right hash are skipped (P10-T3, ADR-020: no large files in the public repo).
- `build-site` — `python scripts/build-site [--out _site]`: static site for hosting (P10-T8) from
  `site/site.json`: landing page + each course released with `release-course --site` into
  `<out>/<course-id>/`, per-course redirect, `404.html`, `.nojekyll`; relative links (any base path).
- `e2e-site.py` — `python scripts/e2e-site.py [--url URL]`: browser test of the built (or live) site.
- `validate` — `python scripts/validate courses/<name>`: validate all JSON against schemas
  in `build/schemas/` (P2-T4).
- `sync-engine` — re-vendor the latest hub `engine/` into a course at a pinned commit
  (ADR-001; P4-T3).
- `release-course` — `python scripts/release-course <name>`: validate and stamp a
  self-contained Docker/local-study artifact with vendored engine and an initial Git
  commit; strips `build/`+`source/` (ADR-001; P4-T4).
- `export-exam` — `python scripts/export-exam <course> <scope>`: emit a self-contained
  exam pack (`rubric.md` + `exam-blank.md` + `exam-answers.md`) for `part<N>` or
  `unit<N>`, per the P5-T7 conventions (P5-T8).
- `e2e.py`, `e2e-fork.py` — browser regression gates incl. progress export/import (see
  `docs/ROADMAP.md` cross-cutting section).
- `e2e.py --authored` — authored-exercise render/grade harness, one course item per `shape`
  (the Davidson exwb shapes), and the session-mix contract (honours `features.authoredPerSession`).
- `e2e.py --accessibility` — roadmap keyboard navigation + on-screen Hebrew keyboard.
- `e2e-synthetic.py` — generic-engine acceptance on a tiny non-Hebrew course (launch,
  keyboard nav, drill, unlock, authored item, progress restore).
- `e2e-docker.py` — fresh-release Docker test: serves the course, writes progress to
  the mounted folder, restarts, and verifies progress restoration.

## Status

Implemented. Run `ruff check build/ scripts/` for lint. See `docs/ROADMAP.md` for
per-task acceptance tests.
