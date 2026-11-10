# build/

> Extraction + content-generation. Author-side, offline. Python 3, stdlib + `pypdf`.
> See `docs/CONTENT-GENERATION.md` for the full pipeline + OER allowlist.

## Layout

- `generate-lessons.py` — OER-enrichment pass (P6-T2): reads canonical text +
  `_oer/` cache, rewrites `content/vocab.csv` OER columns + `chapters/NN.md`
  (Word-roots table / Teaches / Assumes / Did-You-Know). Run before `materialize.py`.
- `fetch_oer.py` — fetch approved OER sources into `_oer/` (P6-T1). See
  `docs/CONTENT-GENERATION.md` §4.
- `materialize.py` / `textify.py` — canonical plaintext `content/` <-> engine JSON (P5).
- `schemas/` — JSON Schemas for course.json, vocab.json, unit lessons, exercises, progress
  (consumed by `scripts/validate`, P2-T4).
- `_oer/` — cached OER fetches (data gitignored; `manifest.json` + `wiktionary/index.json`
  tracked).
- `_raw/` — intermediate extracted text (gitignored).
- `_sources/<book>/` — scan provenance (`SOURCES.md`, `manifest.json`); the scans themselves are
  downloaded with `python scripts/fetch-sources <book>` (git-ignored in the public repo).
- `exwb_to_authored.py` — Davidson drills from the hand-checked exwb set: reads
  `exwb/curated/davidson-*.json` + `_sources/davidson/exwb-units.json`, writes the course's
  `authored/NN.json` + `exercises/NN.json` (`--check` to verify they are current; P9-T6).
- `*davidson*.py`, `tess.py` — the earlier Davidson OCR/exercise-recovery pipeline (ADR-017/018);
  report-only now (their `--write` is retired).

## Run

```bash
python build/materialize.py --course courses/<course>   # content/ -> engine JSON
python scripts/validate courses/<course>
python build/textify.py --course courses/<course>       # engine JSON -> content/ (round-trip)
python build/generate-lessons.py --course courses/<course>   # optional OER enrichment
python build/exwb_to_authored.py --course courses/biblical-hebrew-davidson   # exwb exercises -> drills
```

Part 2 of the three-part split (AGENTS.md §2): authoring writes course data for the app; it
never imports `exwb/` (it only reads the curated JSON files exwb exports).

## Status

The extraction and portability pipeline is implemented, but its output is not
student-release-ready without human lesson and exercise review. See
`docs/CONTENT-GENERATION.md` and `docs/RESCUE-PLAN.md`.
