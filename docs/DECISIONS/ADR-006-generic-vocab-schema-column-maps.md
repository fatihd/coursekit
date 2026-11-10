# ADR-006 — Generic vocab schema + per-language column maps

Date: 2026-08-12. Status: Accepted.

## Context

The three probed lexicons already differ in shape:
- Source lexicons differ per course: column names, extra columns (e.g. a verb-stem column), and
  unit naming.
- Greek A: `Greek Word | English translation | Category | Unit #`, with **inline
  declension/gender baked into the word** (`ἀπόστολος, ‐ου, ὁ`), no transliteration column.

Forking the schema per language would fragment the engine; a single rigid schema can't fit
all three.

## Decision

- A **single generic vocab schema** (`docs/DATA-MODEL.md` §2): `scriptForm, plural?,
  transliteration?, pronunciation?, gloss, category, frequency?, root?, extra:{}`.
- Per-language **column maps** (`build/column-maps/<language>.json`) declare how source-PDF
  columns map to generic fields. Outliers ride in `extra`.
- Category taxonomy is **shared** (`noun|verb|adjective|preposition|proper-noun|number|…`);
  source-specific refinements (e.g., Greek `noun (proper)`) normalize into the taxonomy
  with the raw value kept in `extra.sourceCategory`.

## Consequences

- **Pro**: one engine, one validator, one exercise generator across languages; new
  languages add a column map, not a schema fork.
- **Pro**: Greek's inline declension stays intact in `scriptForm`; the transliteration
  scheme derives pronunciation at runtime (see `docs/I18N-SCRIPTS.md`).
- **Con**: `extra` is a loose bag; column maps are the contract. Documented thoroughly in
  DATA-MODEL §7 + CONTENT-GENERATION §2.