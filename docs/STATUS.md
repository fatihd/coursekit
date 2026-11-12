# STATUS — Live task-state table + materials inventory

> Updated as work proceeds (no batching). Source of truth for "where are we".
> Plan details + acceptance tests: `docs/ROADMAP.md`. Session continuity: `handover.md`.
> Last updated: 2026-11-10.
## Current state — 2026-11-12

| Area | State |
|---|---|
| Engine | Vanilla JS, no build step; browser-only progress with Export/Import, reset all / reset a unit, mark a unit or an exercise done (ADR-019, P12-T10) |
| `courses/biblical-hebrew-davidson` | 79 units, playable end to end; follows Davidson's 22nd edition (ADR-021). Exercise ladder (P12-T4): five rungs per sentence, typed Hebrew→English, pointed English→Hebrew. Sentences placed by the grammar they use (P12-T1); noun phrase taught first (units 18–26, P12-T8); article-less phrases in units 14–15; recognition questions for the script units 6, 9–12 (P12-T9); corpus expansion (P12-T5) still to come |
| `courses/biblical-hebrew-oer` | 20 units, playable end to end; **preview** — human review pending |
| `exwb/` | Davidson exercises transcribed: 47 files, 1,431 items (40 blocks / 1,138 items exported; reading drills §1–5/7/9 held); in the course as drills since 2026-11-10 (P9-T6) |
| Tests | `e2e.py` (units, exercise types, authored, accessibility, keyboard, ladder, routes, progress-ops), `e2e-synthetic.py`, `e2e-fork.py`, `e2e-docker.py`, `unittest`, `public-audit` — green on Davidson/OER |
| Hosting | Live at <https://fatihd.github.io/coursekit/> (GitHub Pages, deployed by `.github/workflows/pages.yml` on push); Cloudflare Pages mirror parked (P10-T10) |
| Greek | Reach goal, open sources only (P11, parked 2026-11-10) |

## Open items

- R3/R4 human review: Davidson Units 21–22 and a sample of OER units.
- Deferred (user, 2026-11-10): P9-T11 pointing in typed answers, P9-T9 reading exercises.
- Parked (user, 2026-11-10): P11 Greek, P10-T10 Cloudflare Pages mirror.
- Bundled Hebrew font still deferred.
