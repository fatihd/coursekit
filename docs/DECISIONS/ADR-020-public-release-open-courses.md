# ADR-020 — Public release with open courses only

Date: 2026-11-06 (decisions 2026-11-09). Status: Accepted (2026-11-09). Plan: ROADMAP P10.

## Context

The user wants the project public and the app hosted. Two courses have open content:
`biblical-hebrew-davidson` (public-domain grammars) and `biblical-hebrew-oer`
(CC BY-SA 3.0). The other courses developed alongside them are derived from copyrighted course
material, and the hub's `source/` folder holds copyrighted PDFs. All of them are in every commit
of the private hub's history (44 commits, `.git` ≈ 181 MB).

## Decision

- The public repository contains only open material: engine, scripts, exwb, the Davidson and
  OER courses, the synthetic test course, and docs. The private courses, their build data and
  `source/` are excluded.
- The public repo starts from a **fresh history** (a clean snapshot). Deleting files in a new commit
  would leave them in history. The private hub keeps the full history and the private courses.
- A `scripts/public-audit` allowlist check guards the public tree (no `source/`, no private-course
  ids or text, no PDFs, no secrets).
- The app is published as a static site (GitHub Pages recommended): a landing page plus one folder
  per course. Progress stays in `localStorage` with Export/Import (ADR-019), so no server is needed.
- Both courses ship marked "preview".
- Regression gates and the rescue benchmarks (ADR-010) move to Davidson/OER.

## Decided (user, 2026-11-09)

- **New public repo** from a clean snapshot; this repo is not rewritten and stays private.
- **Host:** GitHub Pages first, Cloudflare Pages later. The site build stays host-neutral (plain static `_site/`).
- **No large files** in the new repo: scans, PDFs, DjVu/hOCR dumps and OCR caches are downloaded from
  archive.org by a fetch script into a git-ignored folder; `public-audit` enforces a size limit.
- **Tests stay clean:** harnesses are re-pointed at Davidson/OER/synthetic courses; no private-course content,
  fixtures or expected answers are carried into the public repo.
- **Licenses:** code (engine, scripts, exwb) **MIT**; curated exwb exercise data (transcriptions of the
  public-domain Davidson books, including hints/explanations) **CC0 1.0**. The newly written lesson prose of
  both courses keeps its existing **CC BY-SA 3.0** license; the Davidson source books are public domain
  (attribution in each course's `content/ATTRIBUTION.md`).

## Consequences

- Two repos to keep in sync while the private courses continue. The private one can pull engine changes from
  the public one.
- Tests and docs lose their private-course defaults; course-specific tests are dropped, not ported.
- Until publish, the hub is the single source: `scripts/make-public-snapshot` drops `<!-- private -->`
  doc blocks and unwraps `<!-- public` blocks, so hub docs carry both versions.
- Greek support for the public repo must use open sources (ROADMAP P11). Copyrighted Greek PDFs stay
  private.
