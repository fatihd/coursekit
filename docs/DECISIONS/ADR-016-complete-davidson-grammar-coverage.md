# ADR-016 — Complete Davidson grammar coverage (56 units, pattern families not declensions)

Date: 2026-11-04. Status: Accepted.

## Context

The 47-unit restructure (see STATUS, 2026-11-04) matched the course map to Davidson's
organization, but a section-by-section comparison against the grammar exposed content that
was cited in lessons yet never taught: noun declensions (§§18, 29–30), accents and
Qere/Kethib (§10), transitive/stative verbs (§22), weak-root noun patterns (§§41, 43, 45),
adjective comparison (§47), numerals (§48), and particles (§49). Separately, the generated
`categorize` exercise produced a one-option sort whenever a unit's vocabulary held a single
part of speech (e.g. an all-verb unit), and its single-category choice was not caught by the
no-single-option check (which inspected `options`, not `columns`).

## Decision

1. Expand the course to **56 units**, closing the gaps above. Each added unit carries newly
   authored prose and a student-visible `## Source` line citing its Davidson section:
   §10 (unit 8); §§18/29–30 (unit 11); §47 (unit 14); §48 (unit 19); §49 (unit 20); §22
   (unit 26); §41 (unit 41, after hollow verbs); §43 (unit 43, after double-Ayin verbs);
   §45 (unit 45, after Lamed-He verbs).
2. **Teach noun forms by pattern family** (segholate, strong/verb-like, participial, hollow,
   geminate, Lamed-He), **not** as Davidson's numbered First/Second/Third Declensions. The
   declension numbers are retained only as source cross-references. This keeps the historical
   correspondence without presenting Davidson's author-specific numbered classes as the
   standard modern taxonomy.
3. Move all numeral lemmas out of the preposition unit into the numerals unit and extend them
   to cover 11–19, the tens, 200, and the ordinals 1st–10th (the OCR Hebrew tables are not
   authoritative; forms are standard and remain subject to human review).
4. Remove `categorize` from generated sessions. The type remains registered; its `generate`
   returns nothing when a pool has fewer than two parts of speech.

## Consequences

- The initial 56-unit implementation had 533 vocabulary rows; the follow-up below expanded that
  to 567. The course has 56 chapters/units across four parts (1–8, 9–20,
  21–50, 51–56). The shared `engine/` change (no `categorize` in sessions) is behavior-neutral
  for the other courses (both still pass their pinned regressions).
- Weak-class verb forms in `extra.forms` are now gated to their own class unit instead of the
  stale pre-restructure numbering.
- Human Hebrew review of the new prose, forms, and glosses remains the release gate; it has
  not yet occurred.

## Implementation follow-up (2026-11-04)

- The weak-noun and general noun-pattern lessons now include representative lexemes assigned
  to those units, so their sessions drill noun parsing and plural production instead of only
  offering earlier-unit review.
- Numeral vocabulary now includes masculine and feminine forms for 11–19, feminine ordinals
  1st–10th, 300–900, and 2,000. The prose also explains compound numbers and the counted-noun
  number patterns. This brings the vocabulary to 567 rows; numeral niqqud and glosses still
  require human review.
- Prose section captions now survive Markdown → JSON → Markdown and render as headings in the
  lesson view. Tests cover the format round-trip, noun-unit placements, numeral coverage, and
  the browser-rendered headings.
