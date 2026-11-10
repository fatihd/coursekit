# Davidson source audit

Last updated: 2026-11-10.

**Tracked in the hub (2026-11-10, ROADMAP P9-T10):** only what `build/` and `exwb/` read — both PDFs, both DjVu
XMLs, the Vision OCR JSONs, `_tess/`, the OCR scripts, the generated inventories, `manifest.json`,
`exwb-units.json` and this file. The archive.org extras nothing reads (`*_hocr.html`, hOCR search text and page
index incl. their `.gz` copies, `key-1924_page_numbers.json`, both `*-djvu.txt`, the 19th-ed. `grammar.txt`) are
git-ignored; fetch them with `python scripts/fetch-sources davidson --all` when needed.

**Downloadable inputs (2026-11-09, ROADMAP P10-T3):** every Internet Archive file below is listed with its
URL and sha256 in `manifest.json` (byte-identical to the IA downloads, verified). In the public repo they are
git-ignored and fetched with `python scripts/fetch-sources davidson` (exwb/build inputs: both PDFs and both
DjVu XMLs, ~38 MB) or `--all` (plus text/hOCR locators and the 19th-ed. OCR, ~63 MB). The generated
`*-vision-en.json` (macOS Vision, `ocr_pdf.swift`) and `_tess/` (`ocr_tesseract.sh`) are regenerated
locally, not published. The course follows the 22nd edition (ADR-021).

## Local source files

| File | Source | SHA-256 | Use/status |
|---|---|---|---|
| `grammar.txt` | OCR text for Davidson/McFadyen, *An Introductory Hebrew Grammar*, 19th ed. (1914), Internet Archive item [`introductoryheb00daviuoft`](https://archive.org/details/introductoryheb00daviuoft) | `e2ae2e2ff5b0630d7576f7e3532dde3da67d1df0ce4ffa25a46e25e4ae6de50c` | Historical: the course's first sequence reference; since ADR-021 the course follows the 22nd edition. OCR is a locator. |
| `key-1924.pdf` | McFadyen, *Key to the Exercises in the late Professor A. B. Davidson's revised Introductory Hebrew Grammar* (1924), Internet Archive item [`keytoexercisesin0000mcfa`](https://archive.org/details/keytoexercisesin0000mcfa) | `1ae03d6a194cd9b23bcbf135d0b98d4eeed37c95ca3cd95cc2a8d82407254808` | Scan downloaded from `https://archive.org/download/keytoexercisesin0000mcfa/keytoexercisesin0000mcfa.pdf`. The printed edition history identifies 1924 as the first edition; the references section explicitly says bare § references are to the grammar's 22nd edition. Used as the answer source for the 22nd-edition prompts, with best-effort OCR and per-item scan links (ADR-017). |
| `key-1924-djvu.txt` | Internet Archive OCR for the 1924 key, same item | `9d9aec3fd6ffd59406125b5d486e15ac2d0d7b0b2533b74166afbc5845ab2278` | Downloaded from `https://archive.org/download/keytoexercisesin0000mcfa/keytoexercisesin0000mcfa_djvu.txt`; locator only, not authoritative for Hebrew forms. |
| `grammar-1923-22nd-djvu.txt` | Internet Archive OCR for Davidson/McFadyen, 22nd ed. (catalogued 1923), item [`introductoryhebr0000davi_w1b2`](https://archive.org/details/introductoryhebr0000davi_w1b2) | `52f71527b97ba9cefdcf1314e9807ff785de4e819c71a95005d12f0825d09671` | Downloaded from `https://archive.org/download/introductoryhebr0000davi_w1b2/introductoryhebr0000davi_w1b2_djvu.txt`. OCR locator for the edition comparison; Hebrew prompts still require scan verification. |
| `grammar-1923-22nd.pdf` | 22nd-edition grammar PDF (18 MB), item [`introductoryhebr0000davi_w1b2`](https://archive.org/details/introductoryhebr0000davi_w1b2) | (18,191,014 bytes) | Downloaded from `https://archive.org/download/introductoryhebr0000davi_w1b2/introductoryhebr0000davi_w1b2.pdf`. Input to Apple Vision OCR for the English prompt columns. |
| `grammar-1923-22nd-djvu.xml` | DjVu XML (word + coordinates) for the 22nd ed., same item | (6,833,055 bytes) | Per-leaf DjVu text with word boxes; used for page-leaf cross-checking and maps a leaf to its IA `page/nN` scan. |
| `key-1924-djvu.xml` | DjVu XML (word + coordinates) for the 1924 key, item [`keytoexercisesin0000mcfa`](https://archive.org/details/keytoexercisesin0000mcfa) | (4,595,812 bytes) | Per-leaf DjVu text with word boxes; the source of the pointed-Hebrew answer lists (Tesseract reads Hebrew that Vision mangles into Latin glyphs). |
| `grammar-vision-en.json` | Apple Vision OCR of the 22nd-ed. grammar PDF (English) | generated | `build/_sources/davidson/ocr_pdf.swift` → `ocr_pdf`; per-page line boxes. Source of the clean English prompt columns. |
| `key-vision-en.json` | Apple Vision OCR of the 1924 key PDF (English) | generated | Same tool; source of the clean English part-A answers (used for cross-checking, not yet emitted). |
| `exercise-inventory.json` | Machine-readable provenance ledger | generated | `build/recover_davidson_exercises.py --write`; one entry per emitted item with section, prompt, answer, prompt/answer scan URLs, and both leaf numbers. |
| `grammar-exercise-inventory.json` | Full grammar exercise-block inventory (ADR-018) | generated | `build/inventory_davidson_exercises.py --write`; 48 blocks with items, OCR regions, and prompt-page links. |
| `key-answer-inventory.json` | Answer-side inventory of the 1924 key (ADR-018) | generated | `build/inventory_davidson_answers.py --write`; per §/part numbered items — part A English via Vision, parts B/C/D Hebrew via the tesseract `heb+eng` TSV pass with DjVu §/part tracking — each with its own key leaf. |
| `_tess/` (key + grammar) | Tesseract 5.5.4 `heb+eng` per-page TSV at 400 DPI | generated | `build/_sources/davidson/ocr_tesseract.sh` (poppler + tesseract, both brew-installed 2026-11-05); word boxes + text for all 168 key and 264 grammar pages. This is the Hebrew OCR the recovery was originally asked to install; it reads the key's small pointed Hebrew far better than Vision or the IA DjVu export. |
| `exwb-units.json` | Curated exwb block → course unit map (P9-T6) | hand-written | Read by `build/exwb_to_authored.py`; lists held blocks, correction blocks, the grammar/key leaf offsets (+19/+15) and a reason per block. |
| `pair-inventory.json` | Prompt↔answer pairing ledger (ADR-018; historical — its `--write` is retired, drills now come from `exwb/curated/`) | generated | `build/pair_davidson_exercises.py --write`; every pair with §, part, number, direction, lexical sanity score/tier, and both leaves. Emits `authored/`/`exercises/` for ok+weak pairs only. |

## Edition relationship finding

McFadyen's key is explicitly keyed to the 22nd edition, while the course sequence is based
on the 19th edition (1914). The Archive scan's title/imprint and edition-history pages
identify the key's 1924 first edition; its references section names the 22nd grammar edition.
The 22nd-edition grammar's title and preface identify that edition as revised in 1923. Its
preface to the 19th edition says the translation exercises had been modified in places, and
its later-edition prefaces record further revisions. Therefore section-number agreement is
not sufficient evidence that an individual prompt or answer matches.

**Resolution (2026-11-10, ADR-021, ROADMAP P9-T5b):** the course now follows the 22nd edition. A heading
comparison of both OCR texts shows the same §1–§49 numbering and section titles, so every lesson's § reference
carries over. Paragraph-level references were checked in the 22nd edition: §1.2 (consonant sounds), §2.3
(vocalization / vowel letters) and §20.1 (the root) match; "§23.6" existed in neither edition (§23 has three
numbered paragraphs) and is now cited as "§23 (final clauses)", the sub-point on purpose clauses. Lesson Source
lines read "(22nd ed., 1923)". The exercises and key answers already come from this edition.

A limited OCR comparison found the §1 alphabet prompt in both grammar editions with the same
listed exercise items. The §3 transliteration exercise has changed sample transliterations
between the 19th- and 22nd-edition OCR. This establishes a potentially useful section-level
cross-reference, but not a general exercise/answer crosswalk. No Hebrew answer has been
verified from the scans in this audit.

## OCR quality (22nd-edition grammar)

The 22nd-edition item is fully OCR'd (`djvu.txt`, hOCR, search text) and also offers an
18 MB PDF with a text layer plus per-page images. Its OCR is markedly better than the 1914
item's for Hebrew consonants — words like בראשית are largely recoverable — but the
pointing is corrupted (dropped dagesh, wrong vowel signs; the OCR gives forms such as
בְרַאשִית and שָאוּנִי), so no pointed form may be trusted from OCR. English prose is
reliable enough to locate and read sections. Per-page scans are
retrievable on demand, e.g. `https://archive.org/download/introductoryhebr0000davi_w1b2/page/n60.jpg`
(HTTP 200, JPEG), so verifying a form against the printed page is a single fetch.

## Edition pairing

The 1924 key and this 1923-printed 22nd-edition grammar form a **matched pair**: the key's
references name the 22nd edition, and the grammar's title page and preface establish that
edition. Per the user's edition choice, the recovered exercise prompts come from that 22nd-ed.
pair; the course's lesson sequence and prose remain based on the 19th edition. Exercises are
matched to course units by §, not asserted as exact 19th-edition prompt matches. Their source
links expose the actual prompt and key pages.

**Current rule (supersedes the earlier "do not trust the key" rule):** the 1924 key is the
answer source for the recovered English→Hebrew exercises, keyed to the 22nd-edition grammar
prompts. Because the key's Hebrew OCR is imperfect, every emitted item carries its prompt and
answer scan URLs (`source.promptUrl` / `source.answerUrl`), and the drill renders them as
links — the student opens the scan and confirms a form rather than trusting the OCR. No
individual answer is asserted to be correctly pointed; grading is niqqud-insensitive. The
recovery is structural (right §, right unit, right scan leaf) and best-effort on the Hebrew
text, per ADR-017.

Coordinate-aware follow-up (2026-11-05): the extractor now reads the DjVu XML word boxes,
sorts each answer row right-to-left, segments at printed item-number boxes (including a few
common OCR substitutions), preserves the printed number rather than relying on a page-wide
linear join, and stores the exact answer leaf per item. The answer scan link now targets the
leaf containing that answer, not merely the first leaf of its section/part. Regression tests
check the first four numbered answers in §§11B and 14B against the coordinate parse.

Remaining limitation: Hebrew OCR still corrupts some forms and digits; a marker that OCR
cannot identify leaves that numbered item out rather than shifting later answers onto its
prompt. Grammar-side prompt extraction can also miss items when English sentences cross OCR
lines. Some residual pairing errors remain possible where the DjVu word boxes themselves
interleave columns or a printed number is unreadable. The parser is substantially better at
keeping neighboring items apart, but output remains best-effort; the per-item scan links are
still the correction path, not a claim that the OCR answer is correct.

The inventory (ADR-018) now recovers Hebrew-in-English garble with the DjVu coordinates:
Apple Vision reads the grammar's pointed Hebrew column as Latin garble glued onto the English
column, while the DjVu export keeps Hebrew script and per-word boxes. The inventory maps the
two OCR coordinate spaces per page (anchored on the exercise heading line), finds the printed
Hebrew block's y-range from the DjVu words, drops the Vision rows that fall inside it, and
salvages the clean English runs of any remaining mixed lines. This replaced the 78 garbled
English fragments with their real English content (or dropped them): the current inventory
holds 865 items — 339 Hebrew and 526 English — with 0 unrecoverable fragments, 791
distinct. Where both OCRs mangle a line, the coordinates cannot invent text; those rows stay
out and the per-page scan link remains the arbiter.

Full-book discovery is now separate from key pairing (ADR-018). Run
`python build/inventory_davidson_exercises.py --write` to regenerate
`grammar-exercise-inventory.json`: it contains all 48 OCR-detected exercise headings, item
extraction (numbered and unnumbered Hebrew forms/words plus English sentences and
transliteration word lists), complete region OCR from Vision and DjVu, and the original grammar
page link per block. It does not inspect or match the key. Current yield: 48 blocks, 865 items (339 Hebrew, 526 English), 0 unrecoverable fragments,
791 distinct. The grammar's pointed-Hebrew prompt column is now extracted with the same DjVu
coordinate segmentation as the key's answers (numbered phrases instead of word fragments). The
counts are OCR yields: heading misreads (e.g. § rendered as $, digit 9 as 0), merged columns,
and footnote noise make them approximate; the preserved page OCR and scan links remain the
arbiter.
