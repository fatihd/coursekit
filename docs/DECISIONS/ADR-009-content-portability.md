# ADR-009 — Decouple course content from machinery; plaintext canonical content

Date: 2026-08-13. Status: Accepted (now scheduled as P5 — see ROADMAP P5).

## Context

Course content (lessons, word lists, exercises) currently lives in engine-consumed
JSON (`vocab.json`, `units/NN.json`). That JSON is effectively the canonical source of
truth, which couples the content to this specific engine and makes it awkward to reuse
in spreadsheets, other flashcard/study tools, or AI-assisted workflows. The author
wants the course material to be portable and to feed future AI-generated study
material (practice exams, prompts).

## Decision

1. **Content and machinery depend on each other as little as possible.** The engine
   keeps consuming JSON; the *canonical* content lives as **plain text**:
   - lessons → Markdown chapters (`.md`)
   - word lists → CSV/TSV (`.csv`/`.tsv`)
   - prompts + exams → Markdown (`.md`)
2. A **text ↔ JSON** build pair makes text the source of truth and JSON a derived
   build artifact (`build/textify.py` JSON→text, `build/materialize.py` text→JSON).
3. The engine is **not** changed to read prose directly; it stays format-agnostic and
   only sees JSON. Portability is achieved at the content layer, not by rewriting the
   engine.

## Consequences

- **Pro**: content is reusable outside the engine (spreadsheets, Anki, Obsidian,
  AI tools, future re-implementations); a hedge against tooling rot.
- **Pro**: AI workflows (practice exams, prompts) can operate directly on the `.md`/`.csv`
  text without knowing the engine's JSON schema.
- **Con**: a round-trip build step (textify/materialize) must stay faithful; drift
  between text and JSON is possible if the pair isn't enforced by `validate` + tests.
- JSON remains the runtime contract (`docs/DATA-MODEL.md`); text is the authoring
  contract (`docs/CONTENT-PORTABILITY.md`).