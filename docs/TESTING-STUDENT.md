# TESTING-STUDENT

> How to run a course the way a **student** does — from the released, forkable artifact —
> and verify the whole loop: launch → map → lesson → drill → unlock → export/import progress.
> The complement of `scripts/e2e.py`, which tests from the **authoring-hub** side
> (`courses/<name>` + engine in place). This covers both the automated regression
> (self-contained, no GitHub) and a manual walk-through as a real student on the
> published repos. Last updated: 2026-11-06.

## 1. The student loop (what you should observe)

The app marches a student through a visible unit map: *teach → drill → unlock next*,
and progress is kept in the browser, backed up with **Export progress** (ADR-019).

1. Roadmap shows all units; unit 1 is available, later units locked.
2. Open unit 1 → lesson page → **Start drill** (`gate-btn`).
3. Drill = a fixed session (MCQ / match / translate / dictation), ~11–13 questions;
   ≥70% marks the unit done.
   In `biblical-hebrew-oer`, an MCQ selection is visibly highlighted, correctness status
   occupies a separate status area from the Check/Next action, Enter submits typing answers,
   and the on-screen Hebrew keyboard is centered.
4. Back on the roadmap: unit 1 is **done**; unit 2 is unlocked.
5. **Export progress** downloads a progress JSON; **Import progress** in another (or a
   fresh) browser restores it, merging with whatever is there.

## 2a. Hosted site

The courses are also served as a static site (ROADMAP P10-T8): a landing page links each course.
Locally, `python scripts/e2e-site.py` builds the site, serves it under `/coursekit/` like GitHub
Pages, and checks the landing links, each roadmap's unit count, a unit-1 drill, Export → Import in
a fresh browser, and that progress stays per course. After a deploy, run the same checks on the live
site with `python scripts/e2e-site.py --url https://fatihd.github.io/coursekit/`.

## 2. Docker ZIP path

This is the primary non-developer path:

1. Install Docker Desktop.
2. Download and extract the course ZIP.
3. Double-click `run.command` on macOS, `run.bat` on Windows, or run `sh run.sh`.
4. Open the printed `http://127.0.0.1:8787/app/index.html` URL if it does not open
   automatically.
5. Complete a lesson, stop the launcher, restart it, and confirm progress remains
   (same browser). Export progress, open the app in another browser, import the file.

The ZIP path needs no host Python, Node, npm, Git, or GitHub credentials. Docker only
serves the files (read-only mount); progress lives in the browser. Any other static server
or static host works too.

## 3. Automated student-POV regression — `scripts/e2e-fork.py`

This is the closest thing to "act like a student" in CI. It does, entirely locally:

```
release-course → push to a bare "GitHub" remote → clone the "fork" → run the clone's
OWN vendored engine (no hub dependency) → complete a drill → Export progress →
import the file into a fresh browser → unit 1 is done again.
```

Run it for a releaseable course:

```bash
.venv/bin/python scripts/e2e-fork.py biblical-hebrew-davidson   # [--port 8150]
.venv/bin/python scripts/e2e-fork.py biblical-hebrew-oer
```

Requires Playwright (`.venv/bin/pip install playwright && .venv/bin/python -m playwright install chromium`).

What it asserts (see `scripts/e2e-fork.py`):
- fork roadmap shows the unit count declared by that course (56 for Davidson; 20 for OER);
- unit-1 drill passes and marks the unit done;
- **Export progress** downloads a file; importing it into a fresh browser restores unit 1.
- For `biblical-hebrew-oer`, also checks selected MCQ styling, keyboard alignment, feedback/action
  placement, and Enter-to-check in text-entry exercises.

PASS output ends with:
`E2E-FORK PASS — release -> clone -> drill -> export -> import in a fresh browser`

For the Docker ZIP path, run:

```bash
.venv/bin/python scripts/e2e-docker.py biblical-hebrew-davidson
```

This builds a fresh release, serves it read-only in Docker, checks the served engine is
the browser-only progress version and that no `progress/` folder ships, and restarts it.

Generic-engine and accessibility regressions:

```bash
.venv/bin/python scripts/e2e-synthetic.py                    # 2-unit non-Hebrew course + export/import/merge
.venv/bin/python scripts/e2e.py courses/biblical-hebrew-davidson --accessibility
```

`e2e-synthetic.py` proves the engine is course-agnostic (launch → keyboard nav → drill →
unlock → authored item → export → import into a fresh browser → merge → wrong-course rejection).
`--accessibility` asserts roadmap keyboard navigation and the on-screen Hebrew keyboard.

For a copy-paste **manual** walkthrough (Docker and dev-server, with a full checklist),
see `docs/MANUAL-TEST.md`.

Everything runs in a temp dir you never touch; nothing to clean up. It uses a local
bare remote, so **no real GitHub account is needed**. (It runs its own fresh
`release-course` into the temp dir, so it also re-verifies that release step.)

## 3. Manual walk-through as a real student (published repos)

Release a course with `scripts/release-course <course>` and publish the output folder as its own
repository (or use the hosted site, ROADMAP P10-T8). Two flavors:

### 3a. With GitHub (the real student path)

1. Fork the published course repo on GitHub.
2. Clone **your fork**: `git clone <your-fork-url>`.
3. Run the course with Docker:
    ```bash
    ./run.sh
    ```
4. Play through unit 1 → drill → done. Observe unit 2 unlock.
5. Click **Export progress**; a `<course>-progress-<date>.json` file downloads.
6. Open the app in another browser (or clear site data) and **Import progress**: the
   completed units come back.

### 3b. Local-only (no GitHub)

The released artifact can be used directly from an extracted folder. Double-click the
platform launcher or run `sh run.sh` from the folder.

No account, remote or credentials are involved; progress stays in the browser until
exported.

## 4. Verification checklist

- [ ] 30 units on the roadmap; unit 1 available, unit 2 locked.
- [ ] Lesson page renders (`lesson-title`); **Check** grades an answer; drill shows
      per-question feedback.
- [ ] Unit 1 drill completes and the roadmap marks it **done**.
- [ ] Unit 2 unlocks (`unit--available`).
- [ ] Export progress downloads a schema-valid file with `currentUnit` advanced.
- [ ] Import into a fresh browser restores the units; importing twice changes nothing.
- [ ] Importing another course's file shows a clear error.
- [ ] After stopping/restarting Docker, progress is still there (same browser).
- [ ] A retry-with-wrong-answers (optional) scores <70% and leaves the unit
      `in-progress` (not `done`).

## 5. Reset after testing

- `scripts/e2e-fork.py` and the manual GitHub run write only to your own fork /
  temp dir — the published repo and the hub are untouched.
- Progress lives only in the browser: clear the site data (or use a private window) to
  start fresh. Nothing in the hub or `dist/` needs resetting.

## 6. Related docs

- `docs/GIT-SYNC.md` / ADR-019 — localStorage + export/import progress model.
- `docs/ARCHITECTURE.md` — runtime, views, drill/session generation.
- `scripts/README.md` — hub scripts; `scripts/e2e.py` (authoring-side regression),
  `scripts/e2e-fork.py` (this page).
- `scripts/release-course` — stamps the forkable artifact; writes the student
  `README.md` (a copy of which ships in `dist/<course>/README.md`).
