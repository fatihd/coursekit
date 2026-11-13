# Greek course sources: Machen (backbone) and Davis (extra sentences)

Last updated: 2026-11-13. ROADMAP P11. Decision: ADR-025 (AGENTS.md §12).

**Decision (user, 2026-11-13).** The open Greek course is built on J. Gresham Machen, *New Testament Greek for
Beginners* (1923), which is public domain everywhere. W. Hersey Davis, *Beginner's Grammar of the Greek New Testament*
(1923), also public domain everywhere, is an extra sentence source: its sentences are placed one by one in the
Machen-based unit map (ADR-022). NT text and morphology come from SBLGNT and MorphGNT. Machen has no public-domain
key, so we write the answers and check every Greek word form against MorphGNT. Everything below was done on this
machine: scans came from archive.org, MorphGNT from GitHub, and OCR ran with local tesseract only.


## 1. Sources

| Book / data | Copy used | Public-domain / license reasoning | Folder |
|---|---|---|---|
| Machen, *New Testament Greek for Beginners*, Macmillan, 1923 | archive.org `newtestamentgree00mach_0`: printing of January 1924 from the 1923 plates ("Set up and electrotyped. Published March, 1923. Reprinted January, 1924"), so first-printing text. Second scan of the same plates: `newtestamentgree0000jgre_j2c9` (October 1925) | US: published 1923, copyright renewed 1951, so it ran 95 years and ended 2018-12-31. Life + 70: Machen died 1937-01-01, public domain since 2008-01-01 | `build/_sources/machen/` |
| Davis, *Beginner's Grammar of the Greek New Testament*, George H. Doran, © 1923 Sunday School Board of the Southern Baptist Convention | archive.org `beginnersgrammar0000will_n9j4`: Doran printing (before 1928) without the 1942 "Note to fifth edition" | US: published 1923, ended by 2018-12-31. Life + 70: Davis 1887–1950, public domain since 2021-01-01 | `build/_sources/davis/` |
| SBLGNT text | inside MorphGNT, commit `aaed91e5` (2024-01-21) | CC BY 4.0 (sblgnt.com/license, checked 2026-11-12) | `build/_sources/morphgnt/` |
| MorphGNT parsing and lemmas | github.com/morphgnt/sblgnt | CC BY-SA 3.0 | same |

Not used: the Harper printings of Davis (1942 fifth edition, corrected and enlarged), later Machen printings
"reprinted with corrections" from 1927 (kept only as a text file to look up misprints; decided 2026-11-13: every
correction taken from it is recorded with its page), and the copyrighted answer
books to Machen (Zodhiates 1976; Thompson's study guide 1980).

**License compatibility.** The Davidson course data is CC BY-SA 3.0. SBLGNT text (CC BY 4.0) may be used in a
CC BY-SA adaptation as long as it is attributed. MorphGNT-derived data (CC BY-SA 3.0) may go into a CC BY-SA 3.0 or
a later-version (4.0) work. **Decided (user, 2026-11-13): the Greek course data is
CC BY-SA 4.0**, matching SBLGNT's 4.0. Keep SBLGNT text and MorphGNT-derived data **out of
`exwb/curated/`** (CC0). Machen's and Davis's own sentences are public domain and may go there.

## 2. OCR (local tesseract `grc+eng`)

Machen's scan was rendered at its native 310 dpi (the PDF page is oversized; the text is about 2,650 px wide).
Ground truth: 377 Greek words transcribed by hand from Lesson V Ex. I (p. 31–32, constructed sentences), Lesson XIV
Ex. I (p. 85, aorists) and Lesson XXXIII Ex. I 1–5 (p. 220, NT verses).

| Method | Exact | Diacritics only | Wrong |
|---|---|---|---|
| archive.org text layer | 95.8% | 0.8% | 3.4% |
| Local page `grc+eng --psm 6` | 94.2% | 1.9% | 4.0% |
| Local page + Greek lines re-read with `grc --psm 7` | 95.8% | 2.1% | 2.1% |
| **That, voted word by word against the archive.org text** (keep the reading that is an attested NT form) | **96.6%** | **1.9%** | **1.6%** |

Typical errors: `καί` read as `Kai`/`Kal`, `υἱός` as `vids`, `μου` as `pou`, a lost breathing on a capital, a word
broken at a line end. The late lessons (NT verses with small footnotes) are hardest (91–93%). Machen's own text is
clean: of the Greek words in his exercises, 91% are attested NT forms as OCR'd; most of the rest are OCR damage or
valid forms the NT happens not to use. Davis's type has a kappa shaped like chi, so tesseract reads κ as χ (`χαὶ`);
84% of the OCR'd words are NT forms, and the swap is mechanical to fix against MorphGNT.

## 3. Machen: lessons and exercises

- **33 lessons** (pp. 9–232), then paradigms, a Greek–English vocabulary (about 330 lemma entries) and an English–Greek
  vocabulary. Order: alphabet; accent; present active; second declension, word order, movable ν; first declension;
  article and adjectives; masculine first declension, prepositions; enclitics, personal pronouns, εἰμί; demonstratives,
  αὐτός; present middle/passive, deponents; imperfect; future; first and second aorist; aorist and future passive;
  third declension; participles (three lessons, genitive absolute); subjunctive; infinitive, indirect discourse;
  contract verbs; liquid verbs; more third declension; πᾶς, πολύς, numerals; interrogative, indefinite and relative
  pronouns; imperative; perfect; comparison and many case uses; δίδωμι; τίθημι, ἀφίημι, δείκνυμι, ἀπόλλυμι; ἵστημι,
  οἶδα, optative, conditions.
- **32 exercise sets** (Lessons II–XXXIII). Lesson II: accent drills (accent verb forms, accent noun forms, correct
  wrong accents) — material for recognition questions. Lesson III: 9 groups of verb forms Greek→English and 5 groups
  English→Greek.
- **Sentences start in Lesson IV (p. 27):** 20 Greek→English and 16 English→Greek. From Lesson IV to XXXIII every set
  has part I (Greek→English) and part II (English→Greek), usually 15–20 and 14–17 sentences: in all **about 490
  Greek→English and 490 English→Greek sentences**.
- **Source of the sentences:** compared with SBLGNT verse by verse, 70% of Machen's Greek sentences are constructed,
  9% are NT verses almost word for word and 9% are close to a verse; the NT verses sit in Lessons XXIX–XXXIII (where
  more than half the sentences are NT). Constructed early sentences suit the lower rungs; Davis and NT excerpts add
  real text earlier.
- **Accents** are taught fully (Lesson II, enclitics in VIII, contract syllables in XXIII), matching the accent policy
  in §6.
- **English:** about 15% of the English sentences use `ye`, `thou`, `thy`, `thee`, `art`, `wast`, `spake`.

## 4. Vocabulary against the NT (MorphGNT: 137,554 words, 5,461 lemmas)

| Set | Lemmas | NT running words covered | Lemmas 50+ (309) | 20+ (635) | 10+ (1,125) |
|---|---|---|---|---|---|
| Machen's Greek–English vocabulary (headwords recovered from OCR) | 303 | 68.4% | 221 | 290 | 295 |
| Lemmas used in Machen's Greek→English exercises | 354 | 79.3% | 269 | 343 | 351 |
| **Machen, vocabulary + exercises** | **386** | **80.5%** | **277** | **366** | **375** |
| Davis, Greek in its exercises (OCR'd, before κ/χ fixes) | 318 | 75.7% | 222 | 279 | 306 |

Machen teaches the core well (277 of the 309 lemmas that occur 50+ times) but stops at about 390 lemmas. Missing from
the top 200: τέ, Ἰωάννης, ἀμήν, ἑπτά, πληρόω. For §0 literacy (decided 2026-11-13, user): the core units teach Machen's words plus
the 32 lemmas that occur 50+ times and Machen lacks (so all 309), and an optional reading-vocabulary part after the last
lesson adds the lemmas that occur 10–49 times (Words track, ADR-023; optional for unlocking).

## 5. Davis as an extra sentence source

- **59 short lessons** (alphabet to -μι verbs), an exercise set in almost every lesson: part I Greek→English and
  part II English→Greek, typically 4–8 items each — roughly 280–310 items each way (235 + 258 counted in the
  48 sets the OCR inventory found).
- **NT-based:** of the Greek items long enough to test (four or more words), 23% match one NT verse almost word for word
  and 33% match closely (OCR damage pulls some down); the rest are short phrases (22% have three words or fewer)
  and adapted sentences. Early lessons use phrases and NT fragments; from about Lesson 33 most items are verses.
- **Use:** good extra material for replayability, especially real NT sentences in the middle units, where Machen is
  still constructed. Each item is placed by its grammar and words like any other. Answers for NT-derived items can
  start from the World English Bible (public domain) and must be reviewed; constructed items get our own answers.
- **Not the spine:** sets are small, Lesson 1 is a transliteration drill (§0: dropped), and there is no key.

## 6. Answers and grading (user, 2026-11-13)

- **Answers are ours.** For every Machen and Davis sentence we write the answer. Greek answers: every word form must be
  attested — the same form in SBLGNT (MorphGNT), in the book's own corrected text and paradigms, or in the course word
  list — as `build/davidson_corpus.py` does for Hebrew against OSHB. MorphGNT analyses also give lemma and grammar,
  which place each sentence (ADR-022). English answers accept variants.
- **Spelling:** answers use SBLGNT/MorphGNT spellings; the textbook's spellings are accepted as alternatives.
  Movable ν is optional (ἐστι = ἐστιν, λέγουσι = λέγουσιν), elided and full forms are equal (δι’ = διά, ἀλλ’ = ἀλλά).
- **Accents by rung:** lower typed rungs are graded on letters + breathings; the **iota subscript is required on every
  rung**; full accents only on the top rung, where a grave counts as an acute and enclitic/proclitic accent variants
  are not penalised (ἄνθρωπός τις = ἄνθρωπος τις, ἐστίν = ἐστιν, εἴ τις = εἰ τις). Implemented in
  `engine/greek.js` (`breathings` and `full` levels) and tested by `scripts/e2e-greek.py`; the graders are not wired
  yet (P11-T2).
- **thou / ye:** English→Greek prompts say "you (sg.)" / "you (pl.)"; Greek→English typed answers still accept
  thou/thee/thy/ye and archaic verb forms.

## 7. Next steps (Davidson corpus work merged 2026-11-13)

1. Wire `engine/greek.js` into the typed-answer graders; script-neutral input class; course setting for the accent
   levels (`docs/I18N-SCRIPTS.md`).
2. Builder refactor (shared core + Hebrew/Greek profiles): Greek ladder (rung 5 "with accents", one-point wrong options
   by case, number, voice, tense), lemma-based vocabulary layout from MorphGNT, sentence tagging from MorphGNT parses.
3. exwb Greek support (script switch in `detect.py`/`ocr.py`, LTR editing, `el_GR` keyboard), a Machen profile, then
   curation of the ~980 Machen and ~580 Davis items with our answers and the MorphGNT form check.
4. Unit map: Machen's 33 lessons split into one-topic units (as Davidson's 49 sections became 79 units).
