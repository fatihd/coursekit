# Dodson lexicon source audit

Last updated: 2026-11-14.

Glosses for the frequency layers of `courses/biblical-greek-machen` (ROADMAP P11-T5, ADR-025). The lexicon file is
git-ignored here; `manifest.json` lists it with URL and sha256. Fetch with `python scripts/fetch-sources dodson`
(`--all` adds the repository's LICENSE file).

| File | Source | Use |
|---|---|---|
| `dodson.xml` | github.com/biblicalhumanities/Dodson-Greek-Lexicon, commit `74f70358d4acfaf2f980bf2feb58ab7115cbbcbc` (2018-01-11) | Unicode headwords (with genitive and article) and brief English glosses, read by `build/machen_layers.py` |
| `LICENSE` (optional) | same commit | the repository's CC0 1.0 dedication |

## Public-domain status

John Jeffrey Dodson compiled the lexicon (copyright 2010) from public-domain sources — G. Abbott-Smith, *A Manual
Greek Lexicon of the New Testament* (1922); G. R. Berry, *A New Greek-English Lexicon to the New Testament* (1897);
A. Souter, *A Pocket Lexicon to the Greek New Testament* (1917); J. Strong, *Exhaustive Concordance* (1890) — and
"hereby released [it] by the copyright holder into the public domain" for any use (his note, kept in the repository's
`README-ulrikp.txt`). Ulrik Sandborg-Petersen's conversion and the biblicalhumanities XML are likewise public domain;
the repository carries a CC0 1.0 dedication. Checked 2026-11-14.

## How the course uses it

`build/machen_layers.py` looks up each MorphGNT lemma (by its letters, the exact spelling first), takes the brief
gloss, keeps its first three senses and writes `build/_sources/machen/frequency-layers.json`; glosses reworded by hand
are in `build/_sources/machen/layers-overrides.json`. Only glosses and headword forms enter the course data.
