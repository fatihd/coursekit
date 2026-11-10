# ADR-021 — Davidson course follows the 22nd edition (1923)

Date: 2026-11-09. Status: Accepted. Amends ADR-014 (source-edition audit note).

## Context

The Davidson course's lessons follow the 19th edition (1914). The exercises transcribed in
`exwb/` come from the 22nd edition, and McFadyen's 1924 *Key* answers the 22nd edition (its
references section says so). The user chose the 22nd edition, provided it is public domain.

## Public-domain check

- The edition page of the scan (Internet Archive `introductoryhebr0000davi_w1b2`, PDF page 10) lists:
  20th ed. 1916, reprinted 1919; 21st ed. 1921; **22nd ed. (revised throughout) 1923**,
  reprinted 1925. The scan is the 1925 reprint, which adds no new text.
- **United States:** published 1923, so public domain (every work published before 1931 is PD as of 2026).
- **Life + 70 countries:** the authors are A. B. Davidson (died 1902) and the reviser J. E. McFadyen
  (died 1933), so public domain since 2004. The UK 25-year typographical-arrangement right has
  long expired.
- The 1924 *Key* (McFadyen) is public domain on the same grounds.

## Decision

The Davidson course moves to the 22nd edition (1923) as its single source: lesson sequence,
§ references, exercises and key all point to one edition. The 19th edition is no longer a source;
its scan stays in the archive references only as history.

## Consequences

- ROADMAP P9-T5b (done 2026-11-10): the 22nd edition has the same §1–§49 numbering and titles as the 19th, so
  the unit map stands; lesson Source lines now cite "(22nd ed., 1923)"; the non-existent "§23.6" became
  "§23 (final clauses)"; `content/ATTRIBUTION.md`, `build/_sources/davidson/SOURCES.md` and ADR-014 updated.
- P9-T6 can then map the exwb exercises to units by section without a crosswalk.
