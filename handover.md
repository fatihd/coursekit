# handover.md — Session continuity

> Pair with `docs/STATUS.md` (long-term) + `docs/ROADMAP.md` (plan). Last updated: 2026-11-10.
## Resume — 2026-11-09

- Read `AGENTS.md`, then `docs/STATUS.md` and `docs/ROADMAP.md`.
- Run a course: `python scripts/run courses/biblical-hebrew-davidson` (or `courses/biblical-hebrew-oer`).
- Scan inputs for exwb/build: `python scripts/fetch-sources davidson`.
- Exercise review tool: `cd exwb && python3 -m exwb serve myproject` (see `exwb/README.md`).
- Before any commit: `python scripts/public-audit`, `ruff check build/ scripts/`, `python -m unittest discover tests`,
  `python scripts/e2e.py courses/biblical-hebrew-davidson --units 2`.
- Site: `python scripts/build-site --out _site`; test with `python scripts/e2e-site.py` (or `--url` for the live site).
- Live site: <https://fatihd.github.io/coursekit/> (redeployed on every push to `main`).
- 2026-11-10: P9-T5b done — Davidson lessons cite the 22nd edition (same § numbering as the 19th).
- 2026-11-10: P9-T6 done — Davidson drills now come from the hand-checked exwb set
  (`python build/exwb_to_authored.py --course courses/biblical-hebrew-davidson`; map in
  `build/_sources/davidson/exwb-units.json`): 1,138 items in 34 units, 10 sampled per session
  (`features.authoredPerSession`); old OCR-paired drills removed.
- 2026-11-10: P9-T7 done — drill shows "Show hint" before answering and the explanation with the feedback;
  "give the form" items fixed (Hebrew-only stimulus, sibling-form distractors).
- 2026-11-10: P9-T8 done — `parse-form` exercise type (field-by-field parse drill, red/green selects) for the
  181 Davidson parse items.
- 2026-11-10: pushed to public `coursekit` (0f45c23, deploy green, live e2e PASS). P9-T9 deferred indefinitely.
  P9-T10 done (unread scan extras untracked + ignored; `EXERCISES-REPORT.md` removed).
- 2026-11-10: wrong-answer feedback fixed — the "Review Unit …" link sat in the same grid cell as the red
  "Not quite — answer: …" line and covered it; it now has its own row (`--authored` checks no overlap at 1000/400 px).
  P11 Greek and the Cloudflare mirror (P10-T10) parked (user, 2026-11-10).
- 2026-11-10: P9-T11 deferred (user). P9-T12 done — Davidson vocabulary even (units 9–56: 10–15 words, were 0–113):
  `build/rebalance_vocab.py --layout build/_sources/davidson/vocab-layout.json` (`--recount build/_oer/morphhb/books`
  refilled `frequency` from OSHB). `generate-lessons.py` is stale for Davidson — do not run it.
- Next up: nothing queued; P9-T9, P9-T11, P10-T10 and P11 are deferred/parked (user, 2026-11-10).
