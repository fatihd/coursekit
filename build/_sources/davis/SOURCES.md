# Davis source audit

Last updated: 2026-11-13.

Extra sentence source for the open Greek course (ROADMAP P11, ADR-025): sentences are placed one by one in the
Machen-based unit map. Scans and OCR output are git-ignored; `manifest.json` has URLs and sha256. Fetch with
`python scripts/fetch-sources davis`; local OCR with `bash build/_sources/davis/ocr_tesseract.sh` (`grc+eng`, about
1 minute). Nothing is sent to any online service.

## Book and edition

W. Hersey Davis, *Beginner's Grammar of the Greek New Testament*, New York: George H. Doran Company; copyright 1923
by the Sunday School Board of the Southern Baptist Convention.

| File | Internet Archive item | Printing | Use |
|---|---|---|---|
| `davis-1923.pdf`, `davis-1923-djvu.xml` | [`beginnersgrammar0000will_n9j4`](https://archive.org/details/beginnersgrammar0000will_n9j4) | George H. Doran imprint (the firm became Doubleday, Doran in 1927), no "Note to fifth edition" | The 1923 text |

Avoided: the Harper printings on archive.org (`beginnersgrammar0000davi`, `beginnersgrammar00davi`,
`beginnersgrammar00davi_0`, `beginnersgrammar0000unse_g3q7`, `_z2a3`, `beginnersgrammar0000will_e7i0`) carry a
"Note to fifth edition" dated 1942 ("various corrections and a few additions"), i.e. a different text.
Scan page = printed page + 4 (printed p. 39 = PDF page 43).

## Public-domain status

- **United States:** public domain (published 1923; any copyright ended by 2018-12-31).
- **Life + 70 countries:** public domain. William Hersey Davis, 1887–1950; public domain there since 2021-01-01.

## OCR note

Davis's Greek type has a kappa shaped like chi, so tesseract often reads κ as χ (`χαὶ`, `χόσμου`); only 84% of the
OCR'd Greek words are attested NT forms (Machen: 91%). The swap is systematic and can be fixed with MorphGNT forms.
