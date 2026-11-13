# Exercise Workbench (exwb)

Rule-based candidate generation + a local review UI for recovering exercises from OCR'd books.
No AI, no dependencies: Python 3.9+ standard library only. State lives in one SQLite file.

Part 3 of the project's three-part split (`AGENTS.md` §2): exwb is standalone (stdlib only, no imports
from `build/` or `scripts/`); it borrows the engine's on-screen keyboard over HTTP. `tests/test_layout.py`
checks these boundaries.

## Run
    python3 -m exwb build profiles/davidson.json myproject    # ingest OCR + generate candidates (safe to re-run: never touches existing work)
    python3 -m exwb serve myproject                           # http://127.0.0.1:8765
    python3 -m exwb export myproject -o done.json             # verified blocks only (--all for everything)
    python3 -m exwb reset myproject [--block 14 15]           # discard review work -> fresh candidates (backs up exwb.db; log kept)
    python3 -m exwb ocr myproject [--block 12 20] [--force]    # local tesseract OCR of exercise lines + their key pages (~3 min for all)

The tracked snapshot `curated/` feeds the Davidson course through the authoring step
`python build/exwb_to_authored.py --course courses/biblical-hebrew-davidson` (P9-T6); the course
never reads exwb directly.

`build` and "Re-detect items" run no OCR; they re-apply the rules to stored text. Only `ocr` / the UI button "Local OCR → items" OCR.

## Local OCR
* Engine: tesseract (needs `heb` + `eng` tessdata; poppler for `pdfimages`). macOS Vision is not used: it cannot read Hebrew.
* Bitmap: the PDF's own 1-bit text layer at DjVu resolution (`pdfimages`), so DjVu line boxes crop it 1:1 (overlapping boxes are trimmed).
  Fallback when no such image: `pdftoppm -mono` at a matching width.
* Language per line from the candidate classifier: Hebrew side `heb`, English side `eng+heb`; psm 7, falling back to 6 then 13.
  Override in the profile: `"ocr": {"he": "heb", "la": "eng+heb", "psm": ["7","6","13"], "pad": 10, "workers": 4}`.
* Key book: the matched key segments of each exercise (or its guessed key pages) are OCR'd in the same pass; key entries and
  "Fill empty answers from key" use the result.
* Results live in the `ocr` table (with the DjVu box they were cut from), separate from review work: `reset` and `build` keep them,
  and items are always re-derived from them. Per line, OCR replaces DjVu only when clearly better (`detect.choose_text`:
  script-consistency score +0.1, not much shorter); the Source page shows used OCR in green, rejected OCR struck through.
* "Untouched" = no human edits since the block's last reset; only untouched candidates are re-derived automatically.
* Hebrew lines run 4 variants (`he_variants`: heb psm 7/6/13, heb+script/Hebrew psm 6); the kept one is the best-pointed
  among those whose consonants agree with the consensus (`ocr.pick_hebrew`). `ocr --force he` redoes Hebrew lines only.
  Tesseract still drops much of the pointing on this font; points it never saw cannot be recovered here.

## Structure overrides and curated transcriptions (both survive `build` / `reset`)
* Exercises before the first heading take the previous section number (block 1 = §1). Key: section numbers only move
  forward (a truncated `1` after §40 = §41; strays like `§ 124` are ignored); part letters before the first readable key
  heading are numbered back from it (each A-after-B restart = one section).
* A section's exercises take the key's parts in order (§45: exercise 1 = A/B, exercise 2 = C/D; §18 = A–D); a word list
  is folded into the next group when there are more groups than key parts (§19).
* Held blocks: `python3 -m exwb hold proj <id…> --reason "…"` (`--release` to undo) keeps a block and its curated items
  in the workbench but leaves it out of export; survives build/reset. Davidson: §1, §2, §3, §4, §5, §7, §9
  (transliteration/syllable/reading drills) are held as raw material for future reading exercises.
* Ignored blocks: "Skip (not an exercise)" in the UI or `python3 -m exwb ignore proj <id…> --reason "…"` – stored as an
  override, so build/reset never bring them back; excluded from export. Davidson: only the duplicate §18 block that was
  merged into its neighbour is skipped. The reading/transliteration exercises (§1–§5, §7, §9) are **held**, not skipped,
  and §1 is an explicit user exemption — see `EXEMPTIONS.md`.
* "⇣ Merge with next block" and edits to the Section field are stored as overrides (`meta.overrides`); a merged block keeps
  its sub-spans and items are derived per sub-span.
* `python3 -m exwb curate proj curated/<file>.json` stores a hand/LLM transcription (`curated` table) that replaces the
  derived items of that block; the OCR text stays in `prompt_ocr`.
* Item fields: `prompt`, `answer`, `hint` (student-facing, shown before answering), `explain` (student-facing, shown with
  the feedback after answering), `data` (structured: `parse` = person/gender/
  number/form/stem/state/root/suffix/waw/gloss/alt from `exwb/parse.py`; `pointed` = key's pointed text of a sentence
  printed unpointed), `note` (reviewer-only, never exported). Source errors are corrected in the data, not annotated.
  Files live in `curated/` (tracked). First one: `curated/davidson-s19.json`.

## Automatic clean-up of each item (after pre-fill; `core.autofix`, `detect.fix_pair`)
Uses both sides of an item (Hebrew prompt + English answer, or English prompt + Hebrew answer); every change is listed in
the item note (`auto: …`) and the raw OCR stays in `prompt_ocr` / `answer_ocr`.
* trailing `:` / `׃` removed from Hebrew;
* garbled italic marks `(w.)`/`(.)`/`(#.)`/`(wz.)` → `(m.)`, `(/.)`/`(/)` → `(f.)`, `(p24.)` → `(pl.)` (checked against the key); gender from the Hebrew suffix
  (-ם vs -ן) on short items, else from the OCR shape;
* final ך/ו read as ף/ד: ף/ד→ך when the English has thy/thee, ף→ו when it has his/him, at most as many words as pronouns,
  skipping common words that really end in ף/ד (`FINAL_OK`).

Source paths in the profile are relative to the profile file. The Davidson profile reads the DjVu XML directly from `build/_sources/davidson/` (no copies).
Project folders (`myproject/` etc.) hold `exwb.db` and are git-ignored; use `export --all` for a tracked snapshot.

## Workflow in the UI
* Left: all blocks, filter Unfinished/Done/Skipped. **Next unfinished** (Alt+→) jumps on.
* Centre: edit prompts/answers; OCR originals are kept next to your edits (edited prompts get a blue border).
  Row tools: move, merge with next, split at cursor, delete. Edits autosave; every change is logged (`log` table).
* **Mark done & next** (Ctrl+Enter). Skip = "not an exercise". Reopen any time.
* **Fill empty answers from key**: matches by item label (`L3`↔`L3`, `4`↔`4`); positionally only when few labels match
  and counts are equal. Re-derived candidates (build / reset / OCR / Re-detect) are pre-filled this way automatically.
* Key parsing: § / A. B. markers are taken from DjVu *or* local OCR (OCR often reads a `B.` that DjVu lost); footnote
  blocks (`14 This might…`, `1° …`) are skipped; Hebrew answer parts use tolerant numbering (skips, truncated `2` for 12).
  `L1, L2…` are unnumbered list entries before item 1 (e.g. §19 "His law; his lips; …"), split on `;`/`:` (English) or
  `.`/`,`/`;` (Hebrew); they are renumbered automatically when you split/merge/move/delete rows.
* Sections known only from a running header: the heading is searched for by number on that page and the next
  (`6 20. THE VERB.` = misread `§ 20.`); running headers alone never end a block.
* Right panel: source page text (current block highlighted), the matched key segments (→ puts an entry into the answer box), scan image (if `images_dir` set).
* **Missing block**: click a start line in the page view, Shift-click the end line (may be on a later page), then "+ Block from selection".
* `leaf Δ`: archive links use `{leaf}` = scan + Δ. Davidson: Δ = −1 (DjVu scan 70 = PDF page 70 = archive leaf n69 = printed p.50).
  The build never overwrites a Δ you set in the UI.
* **Key row** (above the items): the key page for the block's section — from a matched `§ N` / `A.` segment, else the key's
  heading or running header (`§ 13. B-§ 14. A.`), else a guess between neighbouring sections. "view text" / "view scan" / archive link.
* **Scan tab**: page images rendered locally from the profile's `pdf` (pdftoppm, cached in `<project>/cache/`), current block
  highlighted; zoom 100–300%.
* **Hebrew input**: "⌨ א keyboard" = the course app's on-screen keyboard (`engine/keyboard.js`, served read-only;
  override with `EXWB_ENGINE_DIR`) plus an extra row for shin/sin dots, meteg, maqaf, sof pasuq, ḥaṭefs.
  "Type Hebrew" (Alt+H) maps physical keys to Hebrew in prompt/answer boxes; "?" shows the map.

## Frontend
One file, `exwb/static/index.html`: vanilla JS (an ES module, no framework, no build step, no npm) + inline CSS,
talking JSON to the stdlib server. The only shared code is the engine keyboard module, imported at runtime.

## Greek books (P11, 2026-11-13)
The profile's `"script"` (`"hebrew"` default, `"greek"`) sets the script side's letters (`exwb/script.py`): Greek
lines are not re-ordered, local OCR uses the profile's `ocr` languages (`grc`; `ocr` needs `grc`+`eng` tessdata), and the
UI loads the `el_GR` keyboard (served with `greek.js`). `profiles/machen.json`: Machen's 32 exercise sets (part I
Greek→English, part II English→Greek); no key, so answers are ours. Curated files `curated/machen-lNN.json` carry
`block_id`, `lesson`, `pages`, items with `data.accept` (more accepted answers) and `data.book_prompt` (Machen's
wording when a prompt is modernised, e.g. thou → you (sg.)); `python build/greek_corpus.py check` checks every Greek word.

## Generalising to another book
Everything book-specific is in the profile JSON: source files + format (`djvu-xml`, `hocr`, `text`), printed-page offset
(auto-detected when omitted), URL template, and regexes: `block_start` (what starts an exercise), `section_heading`
(group 1 = section id), `key_section` / `key_part` (how the answer key is organised). A new book = a new profile.
To support a new OCR format add a parser to `exwb/ingest.py::PARSERS`. Items come from `exwb/detect.py::candidate_items`;
later a model (e.g. DeepSeek) can be plugged in as another candidate source writing into `prompt_ocr/answer_ocr`.

## How candidates are derived
* Ingest re-orders words of Hebrew-dominant lines right-to-left by word x position (DjVu stores bidi lines scrambled).
* A line is English only if it contains real English words (`detect.is_english`); Latin junk that OCR made of Hebrew
  stays with the Hebrew part and is shown as `⟨tok⟩` so it is easy to retype. Bare-number/junk lines inherit the previous side.
* Hebrew numbering is split tolerantly (a skipped number or truncated `3` for 13 is accepted).
* `build` re-derives boundaries + items only for blocks that are still `candidate` with no log entries; anything you touched is kept.

## Known limits (honest)
* Hebrew OCR is poor and numerals are scrambled, so numbered splitting is often wrong - expect to merge/split rows. The UI shows item counts vs the key to find them.
* Pointing is whatever the OCR produced; nothing is normalised. Compare against the scan.
* Part A/B labels are Davidson-specific defaults (A = Hebrew item, B = English sentence); rename freely.
