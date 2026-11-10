# ADR-014 — Independent public-domain Hebrew course (`biblical-hebrew-davidson`)

Date: 2026-11-03. Status: Accepted.

## Context

The existing OER course (ADR-013) is adapted from a CC BY-SA 3.0 open textbook whose source
is a 2014–2016 draft: it advertises composition exercises its own source comments admit were
never made, its exercise file contains unfinished sections, and it lacks a syntax part. The
user rejected rebuilding on that half-finished source and requested instead a **third,
fully independent course** built on public-domain grammars. The user further required that
this course not modify or reuse the private copyrighted-source course or the OER course.

## Decision

1. Create `courses/biblical-hebrew-davidson/` as a separate, 30-unit, four-part course.
2. Base the sequence and exercises on **A. B. Davidson, *An Introductory Hebrew Grammar*
   (1914, 19th ed.)** and its **1924 *Key to the Exercises***; use Gesenius–Kautzsch–Cowley
   (1910), Davidson *Hebrew Syntax* (1901), and Kalisch (1875 + key 1881) as reference and
   supplementary exercise sources; use Harper's *Hebrew Vocabularies* (1890), Brown–Driver–
   Briggs, and Strong's as vocabulary/lexicon references. All are public domain in the US
   (pre-1931) and in life-plus-70 jurisdictions.
3. Author new lesson prose and a fully independent vocabulary (no reuse of the private course's or OER
   vocab, chapters, exercises, or app shell). License the new prose CC BY-SA 3.0; the
   underlying works remain public domain.
4. Do not write to the other courses' folders (`courses/biblical-hebrew-oer/`, the private course), and do not
   place public-domain scans under `source/` (forbidden); any fetched scans go under a
   gitignored `build/_sources/` with a tracked provenance manifest.

## Consequences

### Source-edition audit note (2026-11-04)

The 1924 McFadyen key explicitly refers to Davidson's 22nd edition, while the course's
sequence source is the 19th edition (1914). Sample exercise comparison shows that shared
section numbering does not guarantee identical exercise material. The key may be consulted
only for an individual exercise whose exact prompt and answer have been checked against the
19th-edition scan. See `build/_sources/davidson/SOURCES.md` for provenance, hashes, and the
limited comparison result. Superseded on the answer-authority question by ADR-017
(2026-11-05), which recovers the 22nd-edition key exercises as best-effort OCR with per-item
scan links rather than requiring an item-by-item 19th-edition cross-check.

- The course has its own `course.json`, `units.json`, `content/`, `app/`, `progress/`,
  `prerequisites/`, and `content/ATTRIBUTION.md`.
- Shared `engine/` changes are gated behind opt-in `course.json.features` so existing courses
  behave unchanged.
- The private course's content gates and the OER course's human-review gate remain in force and are not
  relaxed by this course.
