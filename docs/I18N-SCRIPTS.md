# I18N-SCRIPTS

> Per-script runtime config: direction, fonts, on-screen keyboards, normalisation. Language config
> arrives via `course.json.script`; keyboards load from `engine/keyboards/`.
> Last updated: 2026-11-13. **Implemented:** Hebrew (keyboard `he_IL`, pointed grading) and Greek (keyboard
> `el_GR`, grading through `engine/script.js` + `engine/greek.js`, tested by `scripts/e2e-greek.py`); no Greek course
> exists yet (ROADMAP P11-T5). **Aramaic: planned, nothing implemented.** No font is
> bundled and there is no `engine/fonts/` or `engine/translit/` folder.

## 1. Script registry

| Script | Languages | Direction | Font | Keyboard | State |
|---|---|---|---|---|---|
| Hebrew square (+ niqqud) | Biblical Hebrew | `rtl` | system fonts (Ezra SIL / SBL Hebrew if installed); none bundled | `he_IL` (incl. niqqud) | implemented |
| Greek polytonic | Biblical Greek | `ltr` | none yet; candidates Gentium Plus or GFS Didot (OFL) | `el_GR` (polytonic) | keyboard + graders (P11-T2, 2026-11-13); `script.profile: "greek"` |
| Aramaic square | Aramaic A | `rtl` | (would share the Hebrew font) | (`arc`, planned) | not started |

Transliteration schemes (`he-sbl`, `el-translit`, `arc-translit`) were planned but never built as modules; the
course vision forbids transliteration in exercises (AGENTS.md §0), so they are not planned any more.

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

**Pointed grading (2026-11-11, P12-T3):** `engine/exercise-types/util.js` `pointedForm` compares typed Hebrew
with its vowel points: cantillation and meteg are dropped, qamets qatan = qamets, holem haser = holem, maqqef =
space, a word-initial begadkefat dagesh is optional, and inside a word full and defective spellings compare equal
(וֹ / ֹ, וּ / ֻ, a mater י after hiriq/tsere/segol). `pointingDiff` marks wrong or missing points letter by letter.

**Mark keys (2026-11-11):** the niqqud row has the ten vowel signs, shewa, the three hatefs, dagesh,
**shin dot** (U+05C1), **sin dot** (U+05C2) and **maqqef** (U+05BE). Each key shows its mark on a
real letter (בָ; the shin/sin dots on ש; maqqef alone) in the Hebrew font, with its name underneath;
a layout key may set `name` and `base` (the carrier letter, `""` for none). Every key carries
`data-key` with the character it types (exwb uses this to skip marks the layout already has).

### `el_GR` (Greek polytonic) — groundwork 2026-11-12 (P11-T2)
`engine/keyboards/el_GR.js`: 24 letters, final ς and the elision mark; a mark row (`marks`, drawn on a carrier
letter with its name) with smooth, rough, acute, grave, circumflex, the four breathing+accent combinations, iota
subscript and diaeresis. The layout's `compose` function (`composeGreek`) runs after every key: marks are put in
canonical order (diaeresis, breathing, accent, iota subscript) whatever order they were typed in, the text is
NFC-composed to precomposed polytonic letters, and σ at the end of a word becomes ς (ς inside a word becomes σ).
`engine/keyboard.js` imports the layout lazily (`initKeyboard` returns a promise for `el_GR`), so exwb, which serves
only `keyboard.js`, `dom.js` and `keyboards/he_IL.js`, is unaffected. Inputs still need the `hebrew-input` class
to open the keyboard (a script-neutral name is planned with the grader work).

**Script profiles (`engine/script.js`, 2026-11-13).** `main.js` calls `setScript(course)` at start-up; graders and
prompts ask `script()` for the active profile. `course.json` `script.profile` picks it: absent or `"hebrew"` = the
Hebrew behaviour unchanged (`normalizeHebrew` for typed rungs, `pointedForm`/`pointingDiff` with points required);
`"greek"` = `greekKey(…, "breathings")` on typed rungs and `greekKey(…, "full")`/`accentDiff` where
`pointing: "required"`, LTR answer inputs with the on-screen keyboard, `lang` from `script.code` (default `grc`),
and wording ("Greek word", "with accents"). `script.grading` may change the levels or switch off `movableNu`,
`elision`, `clitics`.

**Greek normalisation (`engine/greek.js`; policy ADR-025, 2026-11-13):**
`sameGreek(a, b, level, options)` compares typed and expected Greek. Levels: `breathings` for the lower typed rungs
(letters, breathings and iota subscript must match; accents and diaeresis ignored — the iota subscript is required on
every rung), `full` for the top rung (accents too, but grave = acute, and enclitic/proclitic accent variants are
accepted: ἄνθρωπός τις = ἄνθρωπος τις, ἐστίν = ἐστιν, εἴ τις = εἰ τις; ὁ and ὅ stay distinct), and `letters`
(all marks ignored; not used by the policy). Always: NFC (oxia = tonos), capitals and punctuation ignored, final
ς = σ, Greek question mark ; = `;`, elision marks ’ ᾽ ' unified, a spacing breathing before a capital (᾿Ι) read as
its breathing. Defaults (each can be switched off in `options`): `movableNu` (-σι/-σιν, -ε/-εν, ἐστι/ἐστιν; not
οὐδέν/μηδέν or words of three letters), `elision` (δι’ = διά, ἀλλ’ = ἀλλά, καθ’ = κατά, …), `clitics`.
`accentDiff(answer, expected)` marks letters whose marks differ, for a red-marks view like `pointingDiff`.
Test: `python scripts/e2e-greek.py`.

### `arc` (Aramaic square) — not started
Would be based on `he_IL` with Aramaic-specific marks.

## 4. Transliteration

No transliteration module exists (`engine/translit/` was never created). Transliteration is not used in exercises
(AGENTS.md §0). The prototype `dictation` / `translit-normalize` exercise types carry their own Hebrew handling.

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