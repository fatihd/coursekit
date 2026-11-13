# Machen source audit

Last updated: 2026-11-13.

Backbone of the open Greek course (ROADMAP P11, ADR-025). Scans, DjVu files and OCR output are git-ignored here;
`manifest.json` lists each Internet Archive file with URL and sha256. Fetch with `python scripts/fetch-sources machen`
(`--all` adds the optional files). OCR is local only: `bash build/_sources/machen/ocr_tesseract.sh` writes per-page
tesseract `grc+eng` TSV/TXT to `_tess/book/` (about 2½ minutes on 8 cores). Nothing is sent to any online service.

## Book and edition

J. Gresham Machen, *New Testament Greek for Beginners*, New York: The Macmillan Company, 1923.

| File | Internet Archive item | Printing | Use |
|---|---|---|---|
| `machen-1924.pdf`, `machen-1924-djvu.xml` | [`newtestamentgree00mach_0`](https://archive.org/details/newtestamentgree00mach_0) (Princeton Theological Seminary copy) | "Set up and electrotyped. Published March, 1923. Reprinted January, 1924." | **The course text.** A reprint from the 1923 plates, before the corrected reprint of 1927, so the text is that of the first printing |
| `machen-1925.pdf` (optional) | [`newtestamentgree0000jgre_j2c9`](https://archive.org/details/newtestamentgree0000jgre_j2c9) | "… Reprinted January, 1924; October, 1925." | Same plates; a second scan where the first is unclear |
| `machen-1937-corrected-djvu.txt` (optional) | [`newtestamentgree00mach`](https://archive.org/details/newtestamentgree00mach) | "… Reprinted with corrections September, 1927; … February, 1937." | Text only, to see which misprints Machen corrected in 1927 (source errors are corrected in our data anyway) |

The course follows one text: the 1923 plates (1924 printing). No scan of the March 1923 printing itself is on
archive.org; the 1924 and 1925 reprints carry no "corrections" note, so their text is the first printing's.
Scan page = printed page + 18 (printed p. 32 = PDF page 50). Lessons start on printed p. 9 (PDF 27).

## Public-domain status

- **United States:** public domain. Published 1923; the copyright was renewed in 1951 (later printings say
  "Copyright renewed, 1951, by Arthur W. Machen"), so it ran 95 years and ended on 2018-12-31. The 1927 corrections
  ended on 2022-12-31.
- **Life + 70 countries (UK, EU, Turkey, …):** public domain. John Gresham Machen died on 1937-01-01; his works
  entered the public domain there on 2008-01-01.

## OCR

Measured on 377 Greek words transcribed by hand from three exercise passages (Lessons V, XIV, XXXIII): archive.org
text 95.8% of Greek words exact; local page-level `grc+eng` 94.2%; local page + `grc` line re-read 95.8%; that merge
voted against the archive.org text with MorphGNT word forms 96.6%. Details: `docs/GREEK-SOURCES.md`.

## Derived data and licenses

| File | Derived from | License |
|---|---|---|
| `greek-forms.json` | MorphGNT `sblgnt` word forms and lemmas (SBLGNT text) | CC BY-SA 3.0 (MorphGNT); SBLGNT text CC BY 4.0 |
| `lemma-counts.json` | MorphGNT lemma counts | CC BY-SA 3.0 (MorphGNT) |
| `attested.json`, `corrections.json`, `course-map.json`, `recognition.json` | Machen (public domain) plus our own data | CC BY-SA 4.0, like the course |
| `exwb/curated/machen-*.json` | Machen's exercises plus our answers only | CC0 1.0 (no MorphGNT or SBLGNT data) |

The course credits MorphGNT and the SBLGNT in `courses/biblical-greek-machen/content/ATTRIBUTION.md`.
