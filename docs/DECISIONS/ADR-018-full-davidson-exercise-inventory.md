# ADR-018 — Inventory all Davidson exercise blocks without answer matching

Date: 2026-11-05. Status: Accepted.

## Context

The first recovery pass only emitted English→Hebrew items that could be paired with a
numbered answer in McFadyen's 1924 key. That is a useful student-drill subset, but it is not
an inventory of the exercises in Davidson's 22nd-edition grammar. The grammar also contains
writing, transliteration, correction, pointing, pronunciation, parsing, and other exercises;
answer-key alignment must not gate their discovery. The user explicitly directed: no caps,
no answer matching requirement, find every exercise.

## Decision

1. **The grammar alone is the inclusion source.** Inventory exercise headings and their OCR
   prompt-page content directly from the 22nd-edition grammar. Do not require, consult, or
   match a key answer to include an exercise block.
2. **No per-unit or per-type caps.** Preserve repeated exercises and all candidate material.
   OCR uncertainty is represented as raw OCR plus the exact scan link, not by dropping an item
   to satisfy a fixed quantity.
3. **Preserve all 48 OCR-detected exercise blocks**, their raw Vision page lines, DjVu page
   text (for Hebrew script), exercise-type guess, and prompt scan URL in
   `build/_sources/davidson/grammar-exercise-inventory.json`. The inventory is organized by
   printed exercise block; where OCR does not reliably separate individual questions, the
   whole prompt block remains available rather than pretending that its item count is known.
4. The prior answer-paired `authored/NN.json` output remains an optional, separate subset. Its
   count does not define total exercise coverage and it must not constrain the grammar-only
   inventory.

## Consequences

- The grammar-only inventory currently detects **48 exercise blocks** and extracts
  **865 individual items** with no cap (339 Hebrew, 526 English); 791 are distinct
  after removing OCR echoes. Block kinds: 29 translation, 7 parsing, 6 writing,
  2 correction, 1 transliteration, 1 pointing, 1 pronunciation, 1 unspecified.
- **Coordinate-based recovery of the garbled parts:** Vision reads the pointed Hebrew column
  as Latin garble glued to the English column. The inventory maps the two OCR coordinate
  spaces per page (anchored on the exercise heading), locates the printed Hebrew block's
  y-range from the DjVu word boxes, drops the Vision rows inside it, and salvages the clean
  English runs of remaining mixed lines. The first pass's 78 garbled fragments were thereby
  replaced with their real English content or dropped — the inventory now reports 0
  unrecoverable fragments. Rows both OCRs mangle are simply absent, with the scan link as
  arbiter.
- "Recoverable" still allows letter-level OCR errors inside an item; the per-item scan link
  remains the arbiter. The counts are OCR yields, not guarantees of a complete printed
  inventory: some headings are OCR-corrupted (e.g. §39 read as §30) and some items sit in
  columns or fonts the OCR merges.
- **Answer-side inventory (same method, better OCR).** `build/inventory_davidson_answers.py
  --write` mirrors the grammar inventory over the 1924 key: part-A answers (English) via
  Vision, keyed by the printed "N." markers; part-B/C/D answers (pointed Hebrew) via a
  tesseract 5.5.4 `heb+eng` 400-DPI TSV pass (word boxes), with the DjVu export supplying the
  §/part tracking; per-item key leaf and scan link; no caps and no grammar matching. Current
  yield: 815 items (600 English, 215 Hebrew). The tesseract pass reads the key's small pointed
  Hebrew far better than the previous sources (§13 B now reads מִי / מָה אַתֶּם / מִי הַזֹּאת;
  sections such as §19, §23, §36, §40 that had no Hebrew before now have lists), though a few
  printed rows still defeat it and lose their leading items.
- **Pairing with a sanity check (incorporation).** `build/pair_davidson_exercises.py --write`
  joins the two inventories on § + part + printed item number and scores every pair against
  the course vocabulary (gloss overlap for translation pairs, consonant patterns for
  transliteration pairs), re-assigning pairs that score as belonging elsewhere. Only "ok" and
  "weak" pairs become graded drills — typed-Hebrew `translate-phrase` for English→Hebrew,
  `mcq` over the section's English answers for Hebrew→English, `mcq`/`translit-normalize` for
  transliteration. Current yield: 380 pairs (67 ok, 43 weak, 270 suspect), of which the
  ok/weak pairs emit 176 item placements across 32 units; "suspect" pairs stay in
  `pair-inventory.json` for review. Every emitted item carries both scan links and its sanity
  score. The grammar's Hebrew prompts are extracted with the key's coordinate segmentation,
  and the sanity check surfaced two structural bugs that were fixed: the key's §-boundary
  handling (§12 B answers had been absorbed into §13 B) and a grammar-region spill onto the
  next leaf's running head.
- The answer-paired `authored/NN.json` translation subset is a separate, optional product and
  does not constrain this inventory.

