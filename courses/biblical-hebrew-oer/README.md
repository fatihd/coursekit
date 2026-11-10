# Biblical Hebrew — Open Course

A standalone introductory Biblical Hebrew course whose lesson sequence is adapted from
Aaron Christianson's *An Open Introduction to Biblical Hebrew*. Lesson prose is newly
written for this course and released under CC BY-SA 3.0. See `content/ATTRIBUTION.md` for
source and license details.

This course has its own vocabulary, units, and progress data. It does not use any copyrighted
textbook, workbook, lexicon, extracted summaries, or answer keys.

## Run

From the `lang-research` repository root, run the authoring copy locally:

```bash
.venv/bin/python scripts/run courses/biblical-hebrew-oer
```

The app opens at `http://127.0.0.1:8000/app/index.html`; press Ctrl-C in the terminal to stop
it. To run another course, pass its folder (e.g. `courses/biblical-hebrew-davidson`).

For a standalone student release, run `scripts/release-course biblical-hebrew-oer` and start
the generated `dist/biblical-hebrew-oer/run.sh` with Docker Desktop.
