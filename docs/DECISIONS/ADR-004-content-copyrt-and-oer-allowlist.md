# ADR-004 — Lesson content paraphrases owned material + OER allowlist only

Date: 2026-08-12. Status: Accepted.

## Context

The course source PDFs are **owned/copyrighted** (eTeacher / IIBS). Reproducing their text
in forkable repos would violate copyright. Yet the lessons need real teaching content. And
there are open, high-quality Biblical-languages resources (OSHB, Wiktionary, SBLGNT, CAL).

## Decision

1. Lesson copy generated from the student's **own course PDFs** is **paraphrased /
   transformed** — never reproduced verbatim. The generation pass (`build/generate-lessons.py`)
   uses LLM-assisted paraphrase to rewrite summaries/tables into original prose.
2. Additional enrichment comes only from an **approved OER allowlist** (OSHB/MorphHB,
   Wiktionary Hebrew + Greek, SBLGNT, Perseus, CAL), with attribution + license recorded
   per sourced row.
3. Copyrighted textbooks/grammars not on the allowlist are paraphrased only, never reproduced.

## Consequences

- **Pro**: forkable repos remain copyright-hygienic and redistributable.
- **Con**: generation quality depends on careful paraphrase; requires human QA of samples
  (built into ROADMAP acceptance tests).
- The OER allowlist lives in `docs/CONTENT-GENERATION.md` and is the single source of truth.

## Implementation audit addendum (2026-11-03)

The accepted rule remains unchanged. Courses built from copyrighted material stay in a private
repository and are not published (ADR-020).
