# Biblical Hebrew — Davidson Course

A standalone introductory Biblical Hebrew course built on A. B. Davidson's
public-domain *An Introductory Hebrew Grammar* (1914). Lesson prose and vocabulary are
newly written for this course and released under CC BY-SA 3.0; the source grammar and
lexica are public domain. See `content/ATTRIBUTION.md` for source and license details.

This course is fully independent of the other courses (including the Open (OER) course): it
does not reuse their vocabulary, chapters, exercises, progress data, or app shell.

## Run

From the `lang-research` repository root, run the authoring copy locally:

```bash
.venv/bin/python scripts/run courses/biblical-hebrew-davidson
```

The app opens at `http://127.0.0.1:8000/app/index.html`; press Ctrl-C to stop. For a
standalone student release, run `scripts/release-course biblical-hebrew-davidson` and
start the generated `dist/biblical-hebrew-davidson/run.sh` with Docker Desktop.
