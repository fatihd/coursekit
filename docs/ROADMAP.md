# ROADMAP — Phased plan with task IDs + acceptance tests

> Task IDs are referenced in commit messages and PR titles once git is initialized (P1-T1).
> Live state lives in `docs/STATUS.md`. Dates are ISO `YYYY-MM-DD`. Last updated: 2026-11-10.
> Each task lists **exit criteria** (artifacts produced) and an **acceptance test** (a
> concrete command/check that must pass). A task is Done only when its acceptance test
> passes AND `STATUS.md`/`handover.md` reflect it (see AGENTS.md §5).

## Rescue phase — release-quality gates

The earlier phases built a prototype; this phase makes it a verified student product before
further expansion. Scope and acceptance tests: `docs/RESCUE-PLAN.md`; decision: ADR-010.

| ID | Task | Exit criteria | Acceptance test |
|---|---|---|---|
| R1 | Reconcile contracts and docs | Docs describe actual behavior | ✅ Done |
| R2 | Runtime foundations | Launch, release, browser-only progress with Export/Import (ADR-019), local-only use | ✅ Done: fresh release → launch → restart → export → import restores progress |
| R3 | Substantive lesson flow | Davidson Units 35 and 38 (Qal Qatal, Qal Yiqtol) lessons and exercises built to final quality; their exercises run in the drill (no review step: the user corrects while using the course, ADR-027) | A student can learn and practice the unit's grammar, not only vocabulary MCQs |
| R4 | Student release gate | Exact release artifact / site passes platform, course, accessibility, and content checks | Synthetic + Davidson + OER contract tests pass |

Legend for acceptance tests:
- `AT-<id>`: the check that must pass for task `<id>`.
- Visual/QA checks ("show sample", "eyeball") require the human/agent reviewer to confirm.

---

## P1–P7 — Foundation, engine, release, portability, content generation

Done in the private hub before the public repository existed: docs and repo skeleton (P1),
extraction pipeline and schemas (P2), engine runtime — roadmap, lesson, drill, known set,
on-screen keyboard (P3), release and engine vendoring (P4; its git progress sync was replaced
by ADR-019), plaintext canonical content and AI-exam conventions (P5, see
`docs/CONTENT-PORTABILITY.md`, `docs/AI-EXAMS.md`), and OER enrichment plus extra exercise
types (P6). P7 (more courses) continues as P11 for Greek.

---

## P8 — Independent Hebrew OER course

This scoped exception creates a separate Biblical Hebrew course from *An Open Introduction
to Biblical Hebrew* (CC BY-SA 3.0). It does not reuse any other course's data.

| ID | Task | Exit criteria | Acceptance test |
|---|---|---|---|
| P8-T1 | Record OER source and license | ADR-013 and a shipped attribution notice identify the author, title, URI, license, and changes | Attribution notice is present in a fresh release |
| P8-T2 | Create independent unitized course | `courses/biblical-hebrew-oer` has its own 20-unit map, chapters, vocabulary, progress, and app shell; no other course's source artifacts | `scripts/validate courses/biblical-hebrew-oer` passes; source scan finds no other course's IDs or workbook artifacts |
| P8-T3 | Verify student study and release | Fresh release omits author-only metadata and launches with its own content | `scripts/e2e.py courses/biblical-hebrew-oer --units 20` and `scripts/e2e-fork.py biblical-hebrew-oer` pass |

---

## P9 — Independent public-domain Hebrew course (user-directed exception)

Creates a third course, `biblical-hebrew-davidson`, built on public-domain grammars
(ADR-014) with opt-in grammar diagnostics and parsing/production drills (ADR-015). It does
not modify or reuse the other courses.

| ID | Task | Exit criteria | Acceptance test |
|---|---|---|---|
| P9-T1 | Scaffold the public-domain course | `courses/biblical-hebrew-davidson` has its own 56-unit map, chapters, vocabulary, progress, app shell, and attribution; no other course's artifacts | `scripts/validate courses/biblical-hebrew-davidson` passes; source scan finds no other course's ids |
| P9-T2 | Author lessons and independent vocabulary | 56 units with lesson prose + tables; a curated public-domain-sourced vocabulary | `build/materialize.py` + `scripts/validate` green; no duplicate scriptForm/gloss/transliteration in the vocab |
| P9-T3 | Add opt-in parsing/production + diagnostics | `features`-gated `parse-noun`/`parse-verb`/`produce-form`, per-unit skills, review links, and warm-up; existing courses unchanged | `scripts/e2e.py courses/biblical-hebrew-davidson --units 56` passes; the other courses' `e2e.py` runs still pass |
| P9-T4 | Verify release + fork flow | Fresh release is self-contained with attribution and no author-only data | `scripts/e2e-fork.py biblical-hebrew-davidson` passes |

> P9 follow-up (2026-11-04, ADR-016): the course was expanded from its initial 30-unit map
> to a **56-unit** map that covers the whole Davidson grammar, including the previously
> omitted sections (§§10, 18, 22, 29–30, 41, 43, 45, 47, 48, 49). Noun inflection is taught by
> pattern family rather than by Davidson's numbered declensions, and the `categorize` exercise
> was removed from generated sessions. `scripts/e2e.py courses/biblical-hebrew-davidson
> --units 56` (and `--keyboard`) are green.

### P9 follow-ups (added 2026-11-06)

| ID | Task | Exit criteria | Acceptance test |
|---|---|---|---|
| P9-T5 | Decide the Davidson edition | ✅ Done 2026-11-09: **22nd edition (1923)**, verified public domain (ADR-021) | ADR-021 accepted |
| P9-T5b | Move the course to the 22nd edition | Unit map + lesson § references checked against the 22nd ed.; `content/ATTRIBUTION.md`, `build/_sources/davidson/SOURCES.md`, ADR-014 note updated | ✅ Done 2026-11-10: same §1–§49 numbering/titles in both editions (heading comparison); paragraph refs checked (§23.6 → §23 final clauses); 56 Source lines, `units.json`, README, ATTRIBUTION, SOURCES, ADR-014/021 updated; materialize diff = source lines only |
| P9-T6 | Wire exwb exercises into the Davidson course | ✅ Done 2026-11-10: `build/exwb_to_authored.py` (map `build/_sources/davidson/exwb-units.json`); 1,138 items in 34 units, 10 sampled per session. `exwb export --all` output (40 blocks / 1,138 items; held §1–5/7/9 excluded) becomes `courses/biblical-hebrew-davidson/authored/*` via a build step, mapped to units by 22nd-ed. section (after P9-T5b) | `scripts/validate` green; `scripts/e2e.py courses/biblical-hebrew-davidson --authored` drives at least one item per exwb block shape |
| P9-T7 | Show `hint` / `explain` in the drill | ✅ Done 2026-11-10: "Show hint" button + explanation with feedback; 65 Davidson items hint the pointed form, 13 carry explanations. Authored-exercise schema gains optional `hint` (shown before answering, on request) and `explain` (shown with feedback); engine renders both | `--authored` e2e asserts a hint opens before answering and an explanation appears with feedback; `docs/EXERCISE-TYPES.md` + `docs/DATA-MODEL.md` updated |
| P9-T8 | Parse lists → parse drills | ✅ Done 2026-11-10: new authored type `parse-form` (dropdown per field, accepted readings incl. the key's alternatives, wrong fields outlined red); 181 Davidson items. exwb `data.parse` (person/gender/number/form/stem/state/root/suffix) feeds `parse-verb`/`parse-noun` items instead of free-text answers | A parse-list item grades field by field in e2e |
| P9-T9 | Reading exercises (later) | ⏸ Deferred indefinitely (user, 2026-11-10); the held blocks stay in exwb. The held §1–5/7/9 blocks (transliteration/syllable/reading) get a reading exercise type; until then they stay held | Out of scope until a reading type is designed (`exwb/EXEMPTIONS.md`) |
| P9-T10 | Repo hygiene (private hub) | ✅ Done 2026-11-10: unread archive.org extras untracked + git-ignored (still on disk, re-fetchable with `fetch-sources --all`), `EXERCISES-REPORT.md` removed; `tests/test_layout.py` keeps the extras out of git. Remove the staged redundant OCR files (`build/_sources/davidson/*.gz` duplicates, the ~13–22 MB `*_hocr.html`) and the stale root `EXERCISES-REPORT.md`, or move them out of git | `git ls-files build/_sources` lists only inputs the build/exwb actually read |
| P9-T11 | Pointing in typed Hebrew answers (⏸ deferred 2026-11-10, user) | Grading stays niqqud-insensitive by default; feedback highlights missing or wrong vowel points in red; optional per-item `pointingRequired` for exercises where pointing is the skill (open question: which ones) | e2e: a correct-consonant answer with a wrong vowel shows the highlight; a `pointingRequired` item marks it wrong |
| P9-T12 | Even Davidson vocabulary | ✅ Done 2026-11-10: units 9–56 teach 10–15 words each (were 0–113: unit 9 had 113, unit 10 78, unit 19 67); a word a drill uses is taught by that unit; frequent words first (OSHB counts); verb classes and the core numerals keep their topic units | `build/rebalance_vocab.py --check`; `tests/test_davidson_content.py` (spread, core numerals, weak-noun examples) |

---

## P10 — Public release: open courses only, hosted (planned 2026-11-06)

Goal: a **public** repository and a **hosted** app with the two courses whose content is
open — `biblical-hebrew-davidson` (public-domain sources) and `biblical-hebrew-oer`
(CC BY-SA 3.0) — shipped as "preview" quality. Courses built from copyrighted material and
all source PDFs stay in a private repository. Decision record: ADR-020.


| ID | Task | Exit criteria | Acceptance test |
|---|---|---|---|
| P10-T1 | Decide public scope (user decisions) | ADR-020 accepted. Decided 2026-11-09: **new public repo** from a clean snapshot; **GitHub Pages** first, Cloudflare Pages later; **no large files** in the new repo. Licenses: code **MIT**, curated exwb data **CC0 1.0** | ✅ Done 2026-11-09 (ADR-020 Accepted) |
| P10-T2 | Allowlist + audit script | `scripts/public-audit` fails on private paths, private-course ids/names/text, PDFs/scans, files over 1 MB (fonts excepted), secrets, unbalanced doc markers, or missing licenses; a public allowlist of paths | ✅ Done 2026-11-09: `scripts/public-audit` + `scripts/public-allowlist.txt`; `python3 -m unittest tests.test_public_audit` |
| P10-T3 | Clean public tree | Private courses, their build data and private-only scripts/docs are left out; no scans, PDFs, DjVu/hOCR dumps or OCR caches are committed: `scripts/fetch-sources davidson` downloads them from archive.org into a git-ignored folder; licenses added | ✅ Done 2026-11-09: `scripts/make-public-snapshot OUT` (hub-only) builds the tree with the overlay licenses; scan hashes verified against archive.org; `validate` green for both courses; `e2e.py courses/biblical-hebrew-davidson --units 2` PASS |
| P10-T4 | Re-point regression gates | Test harnesses and script examples default to Davidson/OER; no private-course content, fixtures, expected answers or ids are carried over; content-generation tools require an explicit `--course` | ✅ Done 2026-11-09: on Davidson `e2e.py --units 2`, `--exercise-types`, `--authored`, `--accessibility`, `--keyboard`, `e2e-fork.py`, `e2e-docker.py` PASS; OER `--units 2` + `e2e-fork.py` PASS; `e2e-fork.py` reuses the `e2e.py` answerer |
| P10-T5 | Re-base the rescue gates | Benchmarks: Davidson Unit 1 (smoke), Units 21–22 (grammar), OER; R4 = both courses + synthetic | ✅ Done 2026-11-09 (docs): public `docs/RESCUE-PLAN.md`, ADR-010 public text, `docs/MANUAL-TEST.md`; human review still open (R3) |
| P10-T6 | Three-way split in the tree | Physical layout for the split recorded in AGENTS.md: app (`engine/` + course runtime), course authoring (`build/`, `courses/*/content/`), exercise extraction (`exwb/`) — directories, READMEs and ownership of each | ✅ Done 2026-11-10 without folder moves: AGENTS.md §2 maps each part to folders, README, run command and allowed dependencies; READMEs corrected (engine README no longer claims missing fonts/keyboards); `tests/test_layout.py` enforces the boundaries |
| P10-T7 | Docs scrub | Public docs describe only the open courses; private passages in hub docs sit in `<!-- private -->` blocks (dropped by the snapshot) with `<!-- public` replacements; private-only docs/ADRs are denied; root `README.md` for the public repo | ✅ Done 2026-11-09: snapshot `public-audit` PASS (0 problems) |
| P10-T8 | Static site build + hosting | `scripts/build-site` writes `_site/`: landing page listing the two courses ("preview" banner), each course at `/<course-id>/` with its vendored engine; GitHub Actions deploys to Pages. Progress stays per course in `localStorage` (keyed by course id) with Export/Import | ✅ Done 2026-11-10: live at <https://fatihd.github.io/coursekit/>; workflow green; `e2e-site.py --url https://fatihd.github.io/coursekit/` PASS |
| P10-T9 | Publish | Fresh-history public repo pushed (only after explicit user go-ahead); private repo keeps the full history | ✅ Done 2026-11-10: `github.com/fatihd/coursekit` public with a single clean commit; the earlier private push was renamed to `coursekit-old` (private) so no older commit is reachable |
| P10-T10 | Cloudflare Pages mirror (parked 2026-11-10, user) | Same `_site/` build deployed to Cloudflare Pages as a second host | `e2e-site.py --url <cloudflare url>` PASS |


Order: T1 → T2 → T3/T4/T5 → T7 → T8 → T9; T6 any time. P9-T5b–T7 are not prerequisites
(the courses ship as preview) but make the Davidson course much better if done first.

---

## P12 — Exercise ladder and corpus expansion (ADR-022, 2026-11-11)

The course vision (AGENTS.md §0): exercises of increasing difficulty, sentences from the start, and a
large, growing exercise corpus. Applies to Davidson first.

| ID | Task | Exit criteria | Acceptance test |
|---|---|---|---|
| P12-T1 | Per-sentence placement | ✅ Done 2026-11-11: 869 sentences tagged (`build/_sources/davidson/sentence-grammar.json`), feature → unit in `grammar-units.json`; sentences now span units 13–46 (none wait for 47–56); early units 13/15/18/20/32 gained short sections (verbless sentence; מִי/מָה, אֲשֶׁר, object marker; construct state, directional ־ָה; לְמַעַן/פֶּן; object suffixes on the verb). Every Davidson sentence tagged with the grammar it uses; units tagged with the grammar they teach; each sentence placed in the first unit where its grammar and words are taught (replaces block placement in `exwb-units.json`). Fixed 2026-11-12: features split to match the one-topic units (imperative 41, jussive 42, infinitive 43, question 32) | Test: no sentence sits before its grammar/words; sentences appear from the first grammar units |
| P12-T2 | Typed Hebrew→English | ✅ Done 2026-11-11 (ladder rung 4): typed English graded against the Key's variants, self-marking when no exact match. The 442 Hebrew→English items become typed translation, checked against the Key | e2e: a typed Key translation grades correct; no Hebrew→English `mcq` left |
| P12-T3 | Pointed Hebrew grading | ✅ Done 2026-11-11 (ladder rung 5): `pointedForm`/`pointingDiff`, red per-letter marks, pausal/contextual and Key alternatives accepted. Top-rung English→Hebrew requires pointing; pausal/contextual final word, maqqef and Key alternatives accepted; wrong/missing points shown in red | e2e: right consonants with a wrong vowel → wrong, highlighted |
| P12-T4 | The ladder | ✅ Done 2026-11-11: five rungs per Davidson sentence (4,510 items), sessions climb from the lowest open rung, next unit unlocks when rungs 1–3 are right (`unlockRung`), stars per rung on the roadmap, ladder panel + rung practice links on the lesson; gate `e2e.py --ladder`. Session builder orders T/F → choice → fill-in → translate without points → with points; every exercise counts toward the unit (no random 10) | e2e: a unit session climbs the ladder; unit done only when its exercises are passed |
| P12-T6 | One topic per unit | ✅ Done 2026-11-11: Davidson rearranged from 56 to 79 units, each on one topic: splits of old units 7, 8, 11, 13, 15, 17, 18, 19, 20, 21, 25, 32/47, 46, 54, 55; new units for Davidson §4 (vowel letters with points), §9 (quiescents), §24 (stem scheme), §32 (weak-verb classes); declensions moved after the suffixes / participle. Exercises, grammar layout and vocabulary remapped. No progress migration (user: not needed yet) | `validate`, unit tests, `e2e.py --units 40`, `--keyboard` (reading-aid headings in units 10–12) green |
| P12-T7 | Deep links and finer progress | ✅ Done 2026-11-11: item codes shown in drills; hash routes `#/<slug>`, `/drill/<seed>/<q>`, `/block/<block>/<seed>/<q>`, `/item/<id>`; seeded randomness; sessions resume after reload; right answers recorded per exercise block (lesson shows counts + Practice links; sessions prefer unanswered items; import merges) | `e2e.py --routes` |
| P12-T8 | Noun phrase first | ✅ Done 2026-11-12: Davidson units 18–26 reordered (construct state 18, prefix prepositions 19, independent prepositions 20, waw 21, noun suffixes 22, preposition suffixes 23, demonstratives 24, who/what/relative 25, object marker 26) | `validate`, unit tests, `e2e.py --units 27` |
| P12-T9 | Recognition for the script units | ✅ Done 2026-11-12: units 6 and 9–12 get rungs 1–3 from `build/_sources/davidson/recognition.json` (vowel letters, quiescents, pause, maqqeph/metheg, Qere/Kethib) | `test_script_units_have_recognition_ladders`, `e2e.py --units 27` |
| P12-T10 | Progress operations | ✅ Done 2026-11-12: reset all progress (roadmap), mark a unit done / reset a unit (lesson), mark an exercise done / not done (drill), in-page confirm for resets; stale async renders dropped | `e2e.py --progress-ops` |
| P12-T11 | Matching exercise UX | ✅ Done 2026-11-12: tap-to-pair tiles (touch, mouse, keys 1–9/a–i), per-pair feedback, right with ≤ 1 miss, two extra options, no duplicate glosses, both directions, singular↔plural sets, word cards after checking, this unit's open words first, match sets in ladder-unit sessions | `e2e.py --words`, `--exercise-types`, `--authored` |
| P12-T12 | Words track | ✅ Done 2026-11-12 (ADR-023): per-unit Words section, four word rungs, own sessions and progress, word star on the roadmap, optional for unlocking | `e2e.py --words` |
| P12-T13 | Drill mode | ✅ Done 2026-11-12 (ADR-024, feature `retries`): hinted retry, requeue at the end of the session, first-try credit only | `e2e.py --modes` |
| P12-T14 | Test mode | ✅ Done 2026-11-12 (ADR-024, feature `tests`): unit test (testing out at 80%), part tests, mock final; one attempt, graded at the end, self-marking for English, results in `progress.tests` | `e2e.py --modes` |
| P12-T5 | Corpus expansion (offline authoring pass) | ✅ First pass done 2026-11-12 (ADR-026): 659 sentences written for the course (`build/_sources/davidson/corpus.json`, every word form attested in the Hebrew Bible, placed by the words and grammar its OSHB analyses show) and 65 whole Bible verses that use only course words (`bible-excerpts.json`, World English Bible translation), units 16–79; 8,281 ladder items (was 5,385). They top each rung up to `ladderTarget` (20) right answers; the rest are practice and test material. Later passes: more sentences for units 13–15 and 72–79 (few new words to build on), recognition items for units 1–5, 7, 8, 13 | Count per unit per rung reported; a retake shows different items |

---

## P11 — Biblical Greek support (reach goal, planned 2026-11-06)

**Parked 2026-11-10 (user); restarted 2026-11-12; backbone decided 2026-11-13 (user):** J. G. Machen, *New Testament
Greek for Beginners* (1923), public domain everywhere, with W. H. Davis, *Beginner's Grammar of the Greek NT* (1923) as an
extra sentence source (ADR-025). Full course textbooks only, never the Harper "inductive" books. Machen has no key:
answers are written by us and every Greek form is checked against MorphGNT. Sources, OCR, inventory and grading policy:
`docs/GREEK-SOURCES.md`.

A Greek course built **only from open sources**, so it can be public. Copyrighted Greek
course PDFs stay private and are not part of this plan.

| ID | Task | Exit criteria | Acceptance test |
|---|---|---|---|
| P11-T1 | Choose the open Greek sources (user decision) — **done 2026-11-13** | ADR-025: Machen (1923) backbone, Davis (1923) extra sentences; `scripts/fetch-sources machen`, `davis`, `morphgnt`; local OCR scripts in each `build/_sources/<book>/` | ADR accepted; licenses recorded in `docs/CONTENT-GENERATION.md` allowlist |
| P11-T2 | Greek script support in the engine — **done 2026-11-13** (`engine/script.js` profiles, graders wired; acceptance on a real Greek course follows with P11-T5) | `docs/I18N-SCRIPTS.md` Greek profile: polytonic `el_GR` on-screen keyboard (breathings, accents, iota subscript), open font (e.g. Gentium Plus / GFS, OFL), LTR, no transliteration (§0); grader normalises Unicode (NFC, final sigma) and grades lower rungs on letters + breathings + iota subscript, the top rung with full accents (grave = acute, clitic variants, movable ν, elision accepted) | `e2e.py --accessibility` and `--keyboard` on a Greek course: type a polytonic word with the on-screen keyboard; a lower rung grades `λογος` = `λόγος`, the top rung does not |
| P11-T3 | Greek parse features | `parse-noun`/`parse-verb` generalised to Greek categories (case/number/gender; tense/voice/mood/person/number) via course config, not Hebrew-specific code | Synthetic Greek parse items grade field by field |
| P11-T4 | exwb Greek profile — **in progress 2026-11-14** (exwb script switch with Greek look-alike item numbers, `profiles/machen.json`, `build/greek_corpus.py`; Machen Lessons III–XXIV curated, XXV–XXXIII and Davis open) | exwb Greek support (LTR, tesseract `grc`+`eng`, `el_GR` keyboard) and a Machen profile; Machen (~980) and Davis (~580) items curated with our answers, every Greek form checked against MorphGNT (`docs/GREEK-SOURCES.md` §6–7) | `exwb export --all` produces valid authored items; the form check passes |
| P11-T5 | `courses/biblical-greek-machen` — **in progress 2026-11-14** (units 1–24 = Machen Lessons I–XXIV; `build/machen_course.py` builds every course file from the repo, `--check` covers them; in the public repo, not on the site; next: Lessons XXV–XXXIII, then the 50+ / 10–49 frequency layers with Dodson glosses) | Unit map, lessons, vocabulary (core: Machen + all 50+ NT lemmas; optional reading vocabulary 10–49), authored exercises, attribution (CC BY-SA 4.0) | `scripts/validate` + `e2e.py --units N` green (no review step, ADR-027) |
| P11-T6 | Add to the hosted site | Third course on the P10 site | Deployed smoke test covers the Greek course |

---

## Cross-cutting (apply throughout)

- **Doc-sync rule** (AGENTS.md §5): every task update also updates STATUS + handover.
- **Acceptance tests are executable checks or eyeball checks** — both count; eyeball
  checks require an explicit human/agent reviewer statement.
- **New tasks/reprioritization** go here AND propagate to STATUS + handover.
- **ADRs**: any new architectural decision creates `ADR-NNN-…md` and updates this map.
- **Regression gate (engine/UI):** `python scripts/e2e.py courses/biblical-hebrew-davidson
  --units 2` is the pinned browser regression test — it headlessly drives the app and
  asserts the teach→drill→unlock loop (completes units 1..N, verifies unit N+1 unlocks,
  checks the progress stored in the browser). Run it after any engine/UI change and before a manual
  test. Requires Playwright (`pip install playwright` + `playwright install chromium`).
- **Regression gate (exercise types):** `python scripts/e2e.py courses/biblical-hebrew-davidson
  --exercise-types` drives every registered exercise-type plugin (generate→render→
  collect→grade with the correct answer) in a headless browser and asserts each grades
  correct. Run after adding/changing any exercise type; does not touch `progress.json`.
- **Regression gate (authored exercises):** `python scripts/e2e.py courses/biblical-hebrew-davidson
  --authored` drives authored item shapes (render→collect→grade with the item's own
  correct answer) and asserts `buildSession` includes authored items before generated
  fill. Run after changing the authored schema, session builder, or `main.js` loading;
  does not touch `progress.json`.
- **Regression gate (accessibility):** `python scripts/e2e.py courses/biblical-hebrew-davidson
  --accessibility` asserts roadmap keyboard navigation (Enter opens a unit) and the
  on-screen Hebrew keyboard (shows on focus, inserts a key). Run after changing roadmap
  rendering or keyboard handling; does not touch `progress.json`.
- **Regression gate (generic engine):** `python scripts/e2e-synthetic.py` builds a tiny
  two-unit non-Hebrew course, validates it, and drives launch → keyboard nav → lesson →
  drill → unlock → authored item → export → import into a fresh browser → merge →
  wrong-course rejection. Run after changing engine bootstrap, session building, or progress.
  next unit exists).
- **Regression gate (fork flow):** `python scripts/e2e-fork.py biblical-hebrew-davidson`
  releases → pushes to a bare remote → clones the fork → runs the vendored app →
  completes a drill → exports progress → imports it into a fresh browser and asserts
  unit 1 is restored.
- **Regression gate (hosted site):** `python scripts/e2e-site.py` builds the static site
  (`scripts/build-site`), serves it under `/coursekit/`, and checks the landing page, every course's
  roadmap, a unit-1 drill, export/import and per-course progress; `--url <site>` runs it on the live site.
- **Regression gate (Docker ZIP flow):** `python scripts/e2e-docker.py biblical-hebrew-davidson`
  builds a fresh release, serves it read-only in Docker, checks the served engine is the
  browser-only progress version and no `progress/` folder ships, and restarts it.
