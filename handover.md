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
- 2026-11-13: P11 Greek restarted (user): backbone Machen (1923), Davis (1923) as extra sentences (ADR-025); sources,
  OCR, inventory and grading policy in `docs/GREEK-SOURCES.md`; `el_GR` keyboard + `engine/greek.js` groundwork.
- 2026-11-10: P9-T11 deferred (user). P9-T12 done — Davidson vocabulary even (units 9–56: 10–15 words, were 0–113):
  `build/rebalance_vocab.py --layout build/_sources/davidson/vocab-layout.json` (`--recount build/_oer/morphhb/books`
  refilled `frequency` from OSHB). `generate-lessons.py` is stale for Davidson — do not run it.
- 2026-11-11: course vision restated by the user and written to AGENTS.md §0 + ADR-022 (exercise ladder, sentences
  from the start, per-sentence placement, typed translation both ways, no transliteration, corpus expansion by
  a later offline pass; static course data, no live agent). Docs that caused the drift got superseded-notes: RESCUE-PLAN (exercise expansion freeze),
  CONTENT-GENERATION (Hebrew→English mcq), P9-T6 block placement + random sampling, EXERCISE-TYPES/ARCHITECTURE
  (difficulty = distractor lookback).
- 2026-11-11: `docs/DECISIONS/` deleted (user: ADR files pollute context); every decision is one line in
  AGENTS.md §12 under its old ADR-NNN label, so existing references still resolve.
  Uncommitted: Davidson `features.transliteration: false` (engine switch).
- 2026-11-11: P12-T1 done — per-sentence placement (869 sentences tagged by hand from their pointed Hebrew;
  `build/_sources/davidson/sentence-grammar.json` + `grammar-units.json`); new sections in chapters 13, 15, 18, 20, 32;
  vocabulary re-laid out (core numerals pinned to 19). New sentences need tags or `exwb_to_authored.py` stops.
- 2026-11-11: P12-T6 done — 79 one-topic Davidson units (splits + new units for §4, §9, §24, §32); exercises,
  `grammar-units.json`, `exwb-units.json`, `vocab-layout.json` remapped; new `prep-suffix` and `segholate` grammar
  features; old progress not migrated (user). P12-T7 (deep links, per-block progress) recorded as ideas.
- 2026-11-11: pushed P12-T6 to both repos (public 97df8d8). P12-T7 done: item codes, hash routes with seeds
  (`#/<slug>/drill/<seed>/<q>`, `/block/…`, `/item/<id>`), resume after reload, per-block progress; `e2e.py --routes`.
  AGENTS.md §0 gained the goal (exam-ready literacy) and a private note.
- 2026-11-11: keyboard — shin dot, sin dot, maqqef keys; mark keys drawn on a letter with their names (all four courses' CSS).
- 2026-11-11: P12-T2/T3/T4 done — exercise ladder (`build/davidson_ladder.py`, 4,510 items), `true-false` type, typed
  English with self-check, pointed grading with red marks, ladder sessions, unlock at rungs 1–3 (`unlockRung`), stars,
  rung practice routes; progress now `units[n].done` per rung. Keyboard pads the page so Check stays visible. Gates:
  `e2e.py --ladder`, `--authored`, `tests/test_davidson_ladder.py`. Pushed P12-T7 + keyboard to both repos (public 38131e2).
- 2026-11-11: review now covers every earlier unit (gaps first), mixes ladder sentences, random wrong options,
  credits the source unit; warm-up uses the same ranking. Not pushed: 6127ee4 (ladder) + this.
- 2026-11-12: placement fix — the grammar feature `volitive` (one unit, 43) split into `imperative` (41), `jussive` (42, incl. cohortative and אַל) and `infinitive` (43); `particle` split into `question` (32: הֲ, אָנָה/מֵאַיִן, יֵשׁ/אֵין) and `particle` (34: הִנֵּה, adverbs, interjections). 266 sentences re-tagged from their Hebrew; units 41/42 had no sentences, now 9/5; vocabulary re-laid out.
- 2026-11-12: units 14–15 get phrases — 31 Davidson phrases with the article taken off (`build/_sources/davidson/indefinite-phrases.json`, hand-pointed; English a/an, (some), (two)) as ladder items; the articled exercises stay in 16+. Wrong options: a changed subject takes an agreeing "to be"; bare noun phrases also get number/article changes. Vocabulary first use counts plurals and ignores units 1–12 (0 words taught after first use, pinned words aside). Every phrase word is now taught by its unit: eye/light/mountain/water/people unpinned from units 62–66 (taught at first use), wolf/palace/cow/side/רָם added to the word list, and first use also matches adjective endings and plurals spelled without the vav (max 17 words per unit; test `test_phrase_words_are_taught_by_their_unit`).
- 2026-11-12: Davidson units 18–26 reordered, noun phrase first (18 construct + directional, 19 prefix preps, 20 independent preps, 21 waw, 22 noun suffixes, 23 prep suffixes, 24 demonstratives, 25 who/what/relative, 26 object marker); chapters, units.json/course.json, grammar-units, exwb-units, vocab and knowledge snapshot renumbered. Units 6 and 9–12 got recognition ladders (rungs 1–3) from `build/_sources/davidson/recognition.json` (41 questions, shape `recognition`).
- 2026-11-12: pushed to `coursekit` (9b47df2): phrases, noun-phrase-first order, recognition. P12-T10 done — progress operations: reset all (roadmap), mark unit done / reset unit (lesson), mark an exercise done / not done (drill item toggle); in-page confirms; stale async renders dropped; gate `e2e.py --progress-ops`.
- 2026-11-12: P12-T11/T12 done (ADR-023) — tap-to-pair matching (per-pair feedback, ≤ 1 miss, extras, no duplicate glosses, both directions, plural sets, word cards) and a per-unit Words track (four word rungs, own sessions, word star, optional for unlocking); gate `e2e.py --words`.
- 2026-11-12: P12-T13/T14 done (ADR-024) — drill mode (hinted retry, requeue at the end, first-try credit) and test mode (unit tests that test out at 80%, part tests, mock final; graded at the end, self-marked English, `progress.tests`); gate `e2e.py --modes`. Fixed: lesson/test feedback buttons shared one grid cell; e2e clicks scoped to the drills gate.
- 2026-11-12: P12-T5 first pass done (ADR-026) — corpus expansion for Davidson: `build/davidson_corpus.py` checks every word of `build/_sources/davidson/corpus.json` (659 sentences written for the course, units 16–79) against the Hebrew Bible (OSHB forms, `corpus-forms.json`) and places each sentence by its words' lemmas and the grammar their morphology shows (plus tags for verbless sentences, look-alike constructs, segholates, apocopated forms); `bible-excerpts.json` holds 65 whole verses that use only course words, with the World English Bible (`fetch_oer.py --source web`). Items carry `extra: true`; a unit needs every book exercise plus new sentences up to `features.ladderTarget` (20) per rung, the rest stay for practice and tests (`ladder.json` `extra`, progress keys `x1`…`x5`). Drill sessions now save their item ids so a resumed session is the same session. Numerals got Strong's numbers; possessive and subject swaps in wrong options keep the number (no "I am evil men"). Gate `e2e.py --corpus`, `tests/test_davidson_corpus.py`.
- 2026-11-13: P11 Greek restarted (ADR-025): Machen (1923) backbone, Davis (1923) extra sentences, SBLGNT/MorphGNT;
  course data CC BY-SA 4.0; core vocabulary = Machen + every NT lemma occurring 50+ times, optional reading vocabulary
  for 10–49. Sources, local OCR, inventory and grading policy in `docs/GREEK-SOURCES.md`; `el_GR` keyboard and
  `engine/greek.js` groundwork (`scripts/e2e-greek.py`).
- 2026-11-13: P11-T2 done — Greek answers graded through `engine/script.js` (letters + breathings + iota subscript on
  typed rungs, full accents on the top rung); the ladder builder split into a shared core with Hebrew and Greek
  profiles (Davidson unchanged); exwb reads Greek books (`profiles/machen.json`); Machen Lessons IV–V curated with
  our answers, every Greek word checked against SBLGNT/MorphGNT (`build/greek_corpus.py`).
- 2026-11-13: no separate review step (user, ADR-027): the courses are corrected as they are used; human-review
  gates removed from the roadmap, rescue plan and site notice.
- 2026-11-13: typed Greek accepted in any valid word order (no postpositive first, no article last; feedback shows our
  order); Machen Lessons III–VIII curated; `courses/biblical-greek-machen` scaffold (units 1–8) validates and passes
  `e2e.py --units 7`, `--ladder`, `--keyboard`, `--accessibility`; not on the site yet (P11-T6).
- 2026-11-14: Machen Lessons IX–XXIII curated and their units 9–23 added; the Greek course is in the public repo
  (not on the site yet).
- Next up: Machen Lessons XXIV–XXXIII and their units; vocabulary layers; optional corpus pass 2 (units 13–15, 72–79).
