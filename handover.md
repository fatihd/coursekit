# handover.md — Session continuity

> Pair with `docs/STATUS.md` (long-term) + `docs/ROADMAP.md` (plan). Last updated: 2026-11-09.
## Resume — 2026-11-09

- Read `AGENTS.md`, then `docs/STATUS.md` and `docs/ROADMAP.md`.
- Run a course: `python scripts/run courses/biblical-hebrew-davidson` (or `courses/biblical-hebrew-oer`).
- Scan inputs for exwb/build: `python scripts/fetch-sources davidson`.
- Exercise review tool: `cd exwb && python3 -m exwb serve myproject` (see `exwb/README.md`).
- Before any commit: `python scripts/public-audit`, `ruff check build/ scripts/`, `python -m unittest discover tests`,
  `python scripts/e2e.py courses/biblical-hebrew-davidson --units 2`.
- Site: `python scripts/build-site --out _site`; test with `python scripts/e2e-site.py` (or `--url` for the live site).
- Live site: <https://fatihd.github.io/coursekit/> (redeployed on every push to `main`).
- Next up: P10-T6 (three-way split), P9-T5b (22nd-edition migration), P9-T6 (exwb exercises).
