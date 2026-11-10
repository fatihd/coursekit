# MANUAL-TEST — Student-point-of-view walkthrough

> How to test the course by hand, from any terminal window, with no skipped steps.
> Complements the automated regressions (`scripts/e2e*.py`). Last updated: 2026-09-06.

## Prerequisites (one-time)

Pick one path. Path A needs only Docker; Path B needs no Docker but uses the repo's
Python venv.

- **Path A (recommended, the real student path):** install and start **Docker Desktop**,
  then confirm with `docker version`.
- **Path B (dev path):** the repo's `.venv/` (already present).

Both start from any terminal window:

```bash
cd ~/repos/lang-research
```

---

## Path A — Docker (the actual product)

```bash
cd ~/repos/lang-research
.venv/bin/python scripts/release-course biblical-hebrew-davidson
cd dist/biblical-hebrew-davidson
sh run.sh
```

What happens:

1. The first command validates the course and stamps `dist/biblical-hebrew-davidson/`
   (content + vendored engine + Dockerfile + launchers + an initial git commit).
2. `run.sh` builds the Docker image (first run only), starts it, opens the browser, and
   prints:
   - `Course is running at http://127.0.0.1:8787/app/index.html`
   - `Progress is kept in your browser; use Export progress to keep a copy.`
3. If the browser does not open automatically, paste that URL into any browser.
4. Stop with `Ctrl-C`.

> Port override: `PORT=9000 sh run.sh` → URL becomes `http://127.0.0.1:9000/...`.

---

## Path B — dev server (no Docker)

```bash
cd ~/repos/lang-research
python3 scripts/run courses/biblical-hebrew-davidson
```

Serves the hub course and opens `http://127.0.0.1:8000/app/index.html`. Stop with
`Ctrl-C`. Progress is kept in the browser only (see Reset below).

---

## Manual test checklist (do in this order)

### 1. Roadmap
- Expect **"Biblical Hebrew — Davidson Course"** and `0 of 56 units complete`.
- Unit **1** highlighted (available); all others locked/dim.

### 2. Unit 1 (smoke test)
- Click **Unit 1** → lesson page renders (title `Unit 1 — The Aleph-Bet`).
- Click **Start drills →** and answer the questions. At the end:
  `… correct — …%` and **Unit complete**.
- Back on the roadmap: unit 1 shows **done**, unit 2 is now **available**.

### 3. Unit 21 (Qal Qatal — grammar benchmark)
- Click **Unit 21**. Expect lesson prose about the suffix conjugation and a paradigm table.
- Start drills: besides vocabulary, expect parsing/production questions for Qatal forms.

### 4. Unit 22 (Qal Yiqtol — later benchmark)
- Click **Unit 22**. Expect the prefix-conjugation lesson and its parsing questions.

### 5. Export / import progress
- On the roadmap, click **Export progress** → a `biblical-hebrew-davidson-progress-<date>.json`
  downloads; the status line says it was downloaded.
- Open the URL in another browser (or a private window) → `0 of 56 units complete`.
  Click **Import progress** and choose the file → the completed units are back.
- Import the same file again → "nothing new". Import a file of another course → error.

### 6. Restart / persistence
- Stop (`Ctrl-C`), start again with the same command, reopen the URL.
- Expect completed units still **done** and the roadmap to resume where it left off.

---

## Reset after testing

```bash
cd ~/repos/lang-research
# progress lives in the browser: clear site data for 127.0.0.1 to start fresh
# Path A artifact lives outside the repo; just delete it:
rm -rf dist/biblical-hebrew-davidson
```

## Troubleshooting
- **`docker: command not found`** → install/start Docker Desktop.
- **Port already in use** → use a different port (`PORT=9000 sh run.sh`), or for the dev
  server the port is fixed at 8000 — kill the old process first.
- **Blank/error page** → the terminal must stay running (the app requires the server, not
  `file://`).
