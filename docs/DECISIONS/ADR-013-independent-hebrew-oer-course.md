# ADR-013 — Independent OER Biblical Hebrew course

Date: 2026-11-03. Status: Accepted.

## Context

The original course ("the private course") is derived from owned/copyrighted course materials and may be
moved to a separate repository later. The user requested a separate course built from the
CC BY-SA 3.0 *An Open Introduction to Biblical Hebrew*, without depending on the original
textbook, workbook, lexicon, or extracted course data.

## Decision

1. Create `courses/biblical-hebrew-oer/` as a separate course; do not overwrite or reuse
   the private course's vocabulary, chapter files, authored exercises, answer keys, page references,
   or other source-derived artifacts.
2. Derive a new unit structure from the OER book's own topic progression and author new
   lesson text, examples, and practice. Attribute the source and license the adapted lesson
   prose under CC BY-SA 3.0.
3. Keep attribution and provenance within the new course. Do not copy assets, workbook
   exercises, or answer keys unless their license is explicitly verified.
4. `textbookPage` is optional metadata; an OER course without a print textbook does not
   invent page numbers.
5. Keep the private course separate (since 2026-11-09 it stays in the private repository;
   ADR-020).

## Consequences

- The new course has its own `course.json`, `units.json`, vocabulary source, progress file,
  lesson chapters, and OER attribution notice.
- The shared engine and app shell may be reused; course content and vocabulary are not shared
  with the private course unless separately sourced and attributed.
