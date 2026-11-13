# STATUS — Live task-state table + materials inventory

> Updated as work proceeds (no batching). Source of truth for "where are we".
> Plan details + acceptance tests: `docs/ROADMAP.md`. Session continuity: `handover.md`.
> Last updated: 2026-11-12.
## Current state — 2026-11-14

| Area | State |
|---|---|
| Engine | Vanilla JS, no build step; browser-only progress with Export/Import, reset all / reset a unit, mark a unit or an exercise done (ADR-019, P12-T10); tap-to-pair matching and a per-unit Words track (ADR-023); drill retries and test mode — unit tests, part tests, mock final (ADR-024) |
| `courses/biblical-hebrew-davidson` | 79 units, playable end to end; follows Davidson's 22nd edition (ADR-021). Exercise ladder (P12-T4): five rungs per sentence, typed Hebrew→English, pointed English→Hebrew. Sentences placed by the grammar they use (P12-T1); noun phrase taught first (units 18–26, P12-T8); article-less phrases in units 14–15; recognition questions for the script units 6, 9–12 (P12-T9); corpus expansion (P12-T5): 659 new sentences and 65 Bible verses, 8,281 ladder items |
| `courses/biblical-hebrew-oer` | 20 units, playable end to end; corrected as the user works through it (ADR-027) |
| `exwb/` | Davidson exercises transcribed: 47 files, 1,431 items (40 blocks / 1,138 items exported; reading drills §1–5/7/9 held); in the course as drills since 2026-11-10 (P9-T6) |
| Tests | `e2e.py` (units, exercise types, authored, accessibility, keyboard, ladder, routes, progress-ops, words, modes, corpus), `e2e-synthetic.py`, `e2e-fork.py`, `e2e-docker.py`, `unittest`, `public-audit` — green on Davidson/OER |
| Hosting | Live at <https://fatihd.github.io/coursekit/> (GitHub Pages, deployed by `.github/workflows/pages.yml` on push); Cloudflare Pages mirror parked (P10-T10) |
| Greek | P11 restarted 2026-11-12: backbone Machen (1923) + Davis (1923) sentences (ADR-025); sources fetched, OCR and inventory done (`docs/GREEK-SOURCES.md`); Greek graders wired (`engine/script.js`); shared ladder core with Hebrew/Greek profiles; exwb Greek support + Machen profile; Lessons III–XXIII curated with our answers, every Greek word attested (`build/greek_corpus.py`); typed Greek accepted in any valid word order; `courses/biblical-greek-machen` units 1–24 build, validate and pass `e2e.py --units 24`; in the public repo, not on the site yet (P11-T6) |

## Open items

- Deferred (user, 2026-11-10): P9-T11 pointing in typed answers, P9-T9 reading exercises.
- Parked (user, 2026-11-10): P10-T10 Cloudflare Pages mirror.
- Greek (P11): curate Machen Lessons XXV–XXXIII with our answers and add their units (units 1–24 done 2026-11-14); the vocabulary layers (all 50+ NT lemmas in the core units; optional reading vocabulary for 10–49) need glosses beyond Machen's lists.
- Bundled Hebrew font still deferred.
