# ADR-017 — OCR-derived Davidson exercises with per-item scan links

Date: 2026-11-05. Status: Accepted.

## Context

The Davidson course (`courses/biblical-hebrew-davidson`) has 56 units of lesson prose and
vocabulary, but no workbook exercises drawn from the actual Davidson exercise set. The 1924
McFadyen *Key to the Exercises* (paired with the 22nd-edition grammar, 1923) is the natural
exercise source, but it is a 1920s scan: the English prompts OCR cleanly, while the pointed
Hebrew answers OCR poorly. Any recovery that blocked on perfect Hebrew OCR would never ship,
and any recovery that silently trusted the OCR would teach wrong forms.

## Decision

1. **Ship best-effort, OCR-derived exercises, and make the original scan the escape hatch.**
   Each emitted item carries a `source` block with `promptUrl`/`answerUrl` (and image URLs)
   pointing at the exact Internet Archive pages the prompt and answer were read from. The
   drill renders these as "Original exercise page" / "Answer key page" links, so when a
   reading is wrong the student opens the scan and moves on — the user's explicit directive.

2. **Pair the two OCR engines by their strength.** English prompts and English answers are
   read with Apple **Vision** OCR (accurate English); pointed Hebrew answers are read from the
   Internet Archive **DjVu/Tesseract** export (which keeps Hebrew script that Vision renders
   as Latin glyphs). Neither is trusted for pointing; the answer is graded niqqud-insensitively.

3. **Recover English→Hebrew (`translate-phrase`) items only.** The typed answer is Hebrew;
   `engine/exercise-types/util.js` gained `normalizeHebrew()` (strips niqqud but keeps the
   sin/shin dot, and folds the maqqeph), and `translate-phrase` uses it plus an RTL
   `hebrew-input` when `answerIsScript` is set. This matches the user's "typed Hebrew
   translation" requirement.

4. **Match exercises to units by §, not by hand.** `build/recover_davidson_exercises.py`
   locates each `EXERCISE. TRANSLATE.` block, recovers its English column, and pairs it with
   the key's Hebrew answer list for the same §; the §→unit mapping comes from each chapter's
   `## Source` line. Emitted `authored/NN.json` files are the engine input; `exercises/NN.json`
   files are the author-side raw scaffolds; `build/_sources/davidson/exercise-inventory.json`
   is the machine-readable provenance ledger.

5. **Do not block on verification.** The recovery is structural (right §, right unit, right
   scan leaf) and best-effort on the Hebrew text. Imperfect readings are acceptable because
   every item links back to its scans. Coverage and quality are documented in
   `build/_sources/davidson/SOURCES.md`, not silently asserted.

## Consequences

- The initial linear-text extraction emitted 96 items across 24 units. Coordinate-aware
  regeneration superseded it; current counts are recorded below.
- The "do not use the 1924 key" rule is replaced by the link-based policy: the key is the
  answer source, and each answer carries the scan link that lets the student confirm it.
- Coordinate-aware follow-up (2026-11-05): the parser uses DjVu word boxes to split the
  right-to-left answer rows at printed item numbers and keeps each item's own key leaf. This
  replaces the initial linear page-text segmentation. Tests assert the numbered answer order
  for §§11B and 14B. The optional answer-paired translation subset currently emits 85 records
  in 22 units, with no per-unit cap. It is not the complete exercise inventory; see ADR-018.
- OCR can still corrupt Hebrew/digits or omit an unreadable number; omitted numbers no longer
  shift subsequent answers onto earlier prompts, but residual pair errors remain possible.
  Per-item scan links remain the correction path; this is not a human verification claim.
  Details are recorded in `build/_sources/davidson/SOURCES.md`.
