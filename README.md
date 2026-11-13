# coursekit (preview)

A small, local-first web app for text-based courses, taught one unit at a time:
*read the lesson → drill → unlock the next unit*. The engine is subject-agnostic; the first
courses teach Biblical Hebrew. No accounts, no server, no spaced-repetition
queue — progress stays in your browser, and **Export progress / Import progress** moves it
between browsers.

> Both Hebrew courses are playable end to end and are corrected as they are used. Report mistakes as GitHub
> issues.

## Courses

| Course | Units | Source | License |
|---|---|---|---|
| `courses/biblical-hebrew-davidson` | 79 | A. B. Davidson, *An Introductory Hebrew Grammar* (22nd ed., 1923) and McFadyen's *Key* (1924) — public domain | Lesson prose CC BY-SA 3.0 |
| `courses/biblical-hebrew-oer` | 20 | Aaron Christianson, *An Open Introduction to Biblical Hebrew* | CC BY-SA 3.0 |

Details and attribution: each course's `content/ATTRIBUTION.md`.

## Use it online

<https://fatihd.github.io/coursekit/>

## Run a course

Needs Python 3 (no packages) and a browser:

```bash
python3 scripts/run courses/biblical-hebrew-davidson
```

The app opens at `http://127.0.0.1:8000/app/index.html`. With Docker instead, release a course
(`python3 scripts/release-course biblical-hebrew-davidson`) and run `sh dist/<course>/run.sh`.

## For contributors

- Start with `AGENTS.md` (operating manual), then `docs/ARCHITECTURE.md` and `docs/ROADMAP.md`.
- Tests: `python3 -m unittest discover tests`; browser tests need Playwright
  (`pip install playwright && python -m playwright install chromium`), e.g.
  `python3 scripts/e2e.py courses/biblical-hebrew-davidson --units 2`.
- Exercise extraction tool: `exwb/` (see `exwb/README.md`); its scan inputs are downloaded with
  `python3 scripts/fetch-sources davidson`.
- Before committing: `python3 scripts/public-audit` must pass — no copyrighted material, scans,
  or files over 1 MB.

## License

Code: MIT (`LICENSE`). Course lesson prose: CC BY-SA 3.0. Curated exercise data in `exwb/curated/`:
CC0 1.0. Source books: public domain.
