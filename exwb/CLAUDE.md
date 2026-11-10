# Exercise Workbench (exwb): context for Claude Code

Goal: recover every exercise (prompts + key answers, with pointing) from Davidson's Introductory Hebrew Grammar
(22nd ed.) via rule-based candidates + a human review UI. No AI in the pipeline yet; a cheap model (e.g. DeepSeek)
may be added later as another candidate source. Human approval is a data field (status=done), not a reason to stop.

## Layout
- exwb/detect.py  candidate generation (block starts, sections, items, key segments), all regex-driven by the profile
- exwb/core.py    build pipeline, block/item edits (with log), key matching, export
- exwb/server.py  stdlib HTTP API;  exwb/static/index.html  the review UI
- profiles/davidson.json  book profile; sources = ../build/_sources/davidson/*-djvu.xml (paths relative to the profile; no copies)

## Run
python3 -m exwb build profiles/davidson.json proj && python3 -m exwb serve proj

## Known issues / next steps (2026-11-06)
1. Local per-line tesseract OCR (exwb/ocr.py, `python3 -m exwb ocr proj`) beats DjVu on most Hebrew lines (first pass 2026-11-06: 571 of 1054 exercise lines replaced, 4098 key lines OCR'd); pointing is still imperfect and some numerals are lost, so items still need manual checks.
2. Sections 1, 20, 26, 27 have no usable body heading in OCR: blocks fall back to running headers (flagged in UI).
3. Some blocks still overrun into following grammar prose where the next heading is unreadable; trim in the UI.
4. Never silently normalise printed Hebrew; keep prompt_ocr/answer_ocr alongside edits. ⟨tok⟩ marks are display aids in candidates only.
5. No remote OCR / AI translation for now (user decision 2026-11-06: conserve credits).
6. §1 (block 1, the alphabet/transliteration drill) is an **explicit user exemption (2026-11-06)**; it is transcribed
   and *held* together with the other reading drills (§2–§5, §7, §9). See `EXEMPTIONS.md` — do not release or re-add
   them to the export, and do not count them as recovery gaps.
