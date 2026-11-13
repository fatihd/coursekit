# New Testament Greek — Machen Course

An introductory New Testament Greek course built on J. Gresham Machen's public-domain *New Testament Greek for
Beginners* (1923). Lesson text, answers and course data: CC BY-SA 4.0; see `content/ATTRIBUTION.md`.

**State (2026-11-14): in progress.** Units 1–25 follow Machen's Lessons I–XXV (Lessons XXVI–XXXIII to follow): recognition questions for the alphabet
and accents (units 1–2), and Machen's exercises with this course's answers from Lesson III on, each sentence a
five-rung ladder (true/false, choose, fill in, translate, translate with accents). Greek answers are graded on
letters, breathings and iota subscript, and on the top rung with full accents, in any order of the right words
(ADR-025). Not yet on the hosted site.

## Build

```bash
python build/machen_course.py --course courses/biblical-greek-machen      # vocab.csv + authored/ + exercises/
python build/materialize.py --course courses/biblical-greek-machen        # content/ -> vocab.json + units/
python scripts/validate courses/biblical-greek-machen --snapshot          # + prerequisites/knowledge.json
python build/greek_corpus.py check                                        # every Greek word attested
```

## Run

```bash
.venv/bin/python scripts/run courses/biblical-greek-machen
```
