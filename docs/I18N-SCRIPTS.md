# I18N-SCRIPTS

> Per-script runtime config: direction, bundled fonts, on-screen keyboards, transliteration
> schemes. Language config arrives via `course.json.script` and loads from `engine/keyboards/`,
> `engine/translit/`, `engine/fonts/`. Scripts supported: Hebrew, Greek, Aramaic (square).

## 1. Script registry

| Script | Languages | Direction | Bundled font (OFL) | Keyboard | Translit scheme |
|---|---|---|---|---|---|
| Hebrew square (+ niqqud) | Biblical Hebrew, Aramaic | `rtl` | Ezra SIL **or** SBL Hebrew | `he_IL` (incl. niqqud) | `he-sbl` (SBL-style academic) |
| Greek polytonic | Biblical Greek | `ltr` | SBL Greek **or** GFS Didot | `el_GR` (polytonic) | `el-translit` (Beta Code ↔ Unicode) |
| Aramaic square | Aramaic A | `rtl` | (shares Hebrew square font) + Aramaic-specific marks | `arc` (based on `he_IL` with additions) | `arc-translit` |

Fonts are **bundled** (not loaded from a CDN) so a fork works offline. Sources:
- Ezra SIL — SIL Open Font License (OFL).
- SBL Hebrew / SBL Greek — Society of Biblical Literature, OFL-equivalent free for non-commercial; to be confirmed before release (P4).
- GFS Didot — Greek Font Society, OFL-compatible.
For licensing notes see `docs/CONTENT-GENERATION.md` §OER allowlist.

## 2. `course.json.script` (loaded at runtime)

```jsonc
"script": {
  "direction": "rtl",
  "font": "EzraSIL",
  "fontFile": "fonts/EzraSIL-Regular.woff2",
  "keyboard": "he_IL",
  "translitScheme": "he-sbl"
}
```

The engine applies `dir="<direction>"` on the mount root, injects `@font-face`, loads the
named keyboard overlay, and uses the named transliteration scheme for transliteration
input/grading.

## 3. On-screen keyboards (`engine/keyboards/`)

A keyboard is a JSON layout: `{ rows: [ [ {label, output, hold?, shift?}, … ], … ] }`.
- `output` is either a literal string (e.g., `"אָ"`) or a key code for special actions
  (`SPACE`, `BACKSPACE`, `NIQQUD_PREFIX`).
- `hold` lists alternate forms under long-press (rare `.had-pataḥ → ḥataf`).
- Active only when an input is focused; otherwise hidden.

### `he_IL` (Hebrew, with niqqud)
Two surfaces: **consonants** row and **niqqud** (vowel points, dagesh, maqqef). Niqqud
inputs combine with the preceding consonant (the engine normalizes canonical combining
order). Includes final-form letters (ך ם ן ף ץ) on the consonant layer.

**Implemented (P3-T6):** `engine/keyboards/he_IL.js` layout (consonants + finals +
niqqud) and `engine/keyboard.js` overlay manager (fixed bottom bar, shows on
`.hebrew-input` focus, cursor-aware insertion, backspace/space/done). The `dictation`
exercise type consumes it (type Hebrew for a gloss) and accepts transliteration as an
alternative input unless the course sets `features.transliteration: false`. Font **file** still not
bundled — see §6.

**Mark keys (2026-11-11):** the niqqud row has the ten vowel signs, shewa, the three hatefs, dagesh,
**shin dot** (U+05C1), **sin dot** (U+05C2) and **maqqef** (U+05BE). Each key shows its mark on a
real letter (בָ; the shin/sin dots on ש; maqqef alone) in the Hebrew font, with its name underneath;
a layout key may set `name` and `base` (the carrier letter, `""` for none). Every key carries
`data-key` with the character it types (exwb uses this to skip marks the layout already has).

### `el_GR` (Greek polytonic)
Letters + accents (acute/grave/circumflex), rough/smooth breathing, iota subscript. Outputs
precomposed polytonic where possible; engine normalizes to NFC.

### `arc` (Aramaic square)
Based on `he_IL` with Aramaic-specific marks (e.g., sěgōlā where distinct). Mostly a
superset; kept separate for clarity.

## 4. Transliteration schemes (`engine/translit/`)

Each scheme is a pair of maps: `toLatin(scriptForm) → latin` and
`fromLatin(latin) → scriptForm` (best-effort; used to grade transliteration input
without requiring the student to type pointed script).

### `he-sbl` (SBL academic transliteration)
 groceries… rough rules (canonical):
- א = ʼ (aleph), ע = ʻ (ayin), ח = ḥ, ט = ṭ, צ = ṣ, שׂ = ś, ת = t (or th per tradition)
- Vowels: qamats = ā, pataḥ = a, ḥataf = ă, tsere = ē, segol = e, ḥireq = i, ḥolam = ō, shureq = u, qibbuts = u
- Dagesh, shewa (ə / silent), maqqef remain as combining marks

### `el-translit` (Greek)
Beta Code-compatible direction plus a dead-key polytonic keyboard map; the engine
prefers precomposed output and falls back to canonical combining.

### `arc-translit`
Hebrew-based plus distinct Aramaic conventions (to be finalized when the Aramaic course is
authored).

## 5. Direction and rendering notes

- **RTL** is set via `dir="rtl"` on the app `.hebrew` (and `.aramaic`) containers, **not**
  on the whole document; mixed-direction pages (e.g., Hebrew text inside English UI) use
  `<bdi>`/`<bdo>` isolation per block.
- Niqqud placement depends on the font having correct GPOS/OpenType tables. Ezra SIL and
  SBL Hebrew do; system fallback fonts on some OSes do not — hence bundling.
- Diacritics normalization: on input, the engine normalizes to NFC; grader comparison is
  done on NFC-normalized strings.

## 6. Pre-release font licensing check (P4)

Before any `release-course`, confirm each font's license permits redistribution in a
forkable repo. If SBL fonts turn out to be non-redistributable, fall back to Ezra SIL /
GFS Didot (OFL). Record the decision in an ADR + `docs/CONTENT-GENERATION.md`.

**Current status (P3-T2):** RTL direction + a `.script` font stack are applied
(`"Ezra SIL", "SBL Hebrew", "Arial Hebrew", "Times New Roman", serif`), relying on
system Hebrew fonts for now. The actual OFL font **file** is not yet bundled — defer
sourcing/downloading Ezra SIL (OFL) to the P4 pre-release pass; do not guess download
URLs.