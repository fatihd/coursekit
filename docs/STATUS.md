# STATUS — Live task-state table + materials inventory

> Updated as work proceeds (no batching). Source of truth for "where are we".
> Plan details + acceptance tests: `docs/ROADMAP.md`. Session continuity: `handover.md`.
> Last updated: 2026-11-09.
## Current state — 2026-11-09

| Area | State |
|---|---|
| Engine | Vanilla JS, no build step; browser-only progress with Export/Import (ADR-019) |
| `courses/biblical-hebrew-davidson` | 56 units, playable end to end; **preview** — lesson prose not yet human-reviewed; follows Davidson's 22nd edition (ADR-021; migration P9-T5b) |
| `courses/biblical-hebrew-oer` | 20 units, playable end to end; **preview** — human review pending |
| `exwb/` | Davidson exercises transcribed: 47 files, 1,431 items (40 blocks / 1,138 items exported; reading drills §1–5/7/9 held); not yet wired into the course (P9-T6) |
| Tests | `e2e.py` (units, exercise types, authored, accessibility, keyboard), `e2e-synthetic.py`, `e2e-fork.py`, `e2e-docker.py`, `unittest`, `public-audit` — green on Davidson/OER |
| Hosting | Static site built by `scripts/build-site`; GitHub Pages deploy via `.github/workflows/pages.yml`, later Cloudflare Pages |
| Greek | Reach goal, open sources only (P11) |

## Open items

- R3/R4 human review: Davidson Units 21–22 and a sample of OER units.
- P9-T5b move the Davidson course to the 22nd edition; P9-T6 wire in exwb exercises; P9-T7 hints/explanations
  in the drill; P9-T8 parse drills.
- P10-T6 three-way split in the tree; P10-T8 Pages deploy (site build and test are done: `scripts/build-site`,
  `scripts/e2e-site.py`).
- Bundled Hebrew font still deferred.
