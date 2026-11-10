# CONTENT-PORTABILITY

> Canonical plaintext content formats (P5 Theme A). Content and machinery depend on
> each other as little as possible: the **text is the source of truth**, the engine's
> JSON is a **derived build artifact**. See ADR-009 and `docs/ROADMAP.md` P5.

## 1. Layout

A course's canonical content lives under `courses/<course>/content/`:

```
content/
  vocab.csv          # word list (one row per lexeme)
  chapters/NN.md     # unit lessons, one Markdown file per unit
  ATTRIBUTION.md     # source/license notices for adapted and OER content
```

`build/textify.py` emits these from the current JSON; `build/materialize.py` reads them
back and regenerates the engine JSON (`vocab.json`, `units/NN.json`). Editing happens
in the text; JSON is regenerated, never hand-edited.

**Authored exercises** (`courses/<course>/authored/NN.json`) are a separate
engine-consumed layer and are **not** part of the vocab/chapter text round-trip; they
are authored directly as JSON (see `docs/EXERCISE-TYPES.md` §4).

## 2. `vocab.csv`

CSV, UTF-8 (no BOM), header row, one row per lexeme. Columns (in order):

```
id,unit,category,scriptForm,plural,transliteration,pronunciation,gloss,gender,number,frequency,root,strong,pos,binyan,oer_source,oer_license
```

- `id` — stable `<lang>-<level>-<unit>-<n>` id (e.g. `he-dav-01-001`).
- `category` — normalized part of speech (`noun|verb|adjective|preposition|proper-noun|number|adverb|demonstrative|pronoun|particle|conjunction|interjection|article|other`).
- `scriptForm`, `plural` — the script (Hebrew/Greek/Aramaic), inline Unicode.
- `transliteration`, `pronunciation` — Latin, diacritics intact.
- `gloss` — clean English translation, **no** gender/number suffix.
- `gender` — `m|f|c` (common), or empty.
- `number` — `s|p|d` (dual), or empty.
- `frequency` — integer, or empty.
- `root` — triliteral root (from Wiktionary `he-rootbox`), or empty.
- `strong` — Strong's number(s) (OSHB/MorphHB), or empty.
- `pos` — OSHB part-of-speech label (`noun|verb|…`), or empty.
- `binyan` — Hebrew verb stem (`Qal|Nifal|Piel|Pual|Hifil|Hufal|Hitpael`), verbs only,
  or empty. Maps to engine `extra.binyan`; courses without stems leave the column empty so the CSV
  shape stays uniform.
- `oer_source` — OER source(s) for the enrichment, `; `-joined (e.g. `OSHB/MorphHB; Wiktionary`), or empty.
- `oer_license` — license(s) matching `oer_source`, `; `-joined (e.g. `CC BY 4.0; CC BY-SA 3.0 / GFDL`), or empty.

The OER columns (`root`↝ engine `root`, `strong`/`pos`/`oer_source`/`oer_license` ↝
`extra.{strong,pos,source,license}`) are **derived**: `build/generate-lessons.py`
populates them from the local OER cache (`build/_oer/`), never by hand. They must be
present only when the row was enriched; empty values materialize to missing/null so a
row without OER data stays attribution-free (ADR-004).

Fields not carried in CSV (dropped on materialize): `category_raw` (extraction
artifact). The `binyan` column (verb stem — see row spec above) is one such addition;
further per-language fields (e.g. Greek declension) follow the same pattern: add a
column and note it here + in the column map.

## 3. `chapters/NN.md`

One Markdown file per unit. Structure:

```markdown
# Unit 1 — The Aleph-Bet

Welcome! – After introducing ourselves, …

## Summary

This unit explored the historical development of the Hebrew alphabet. …

## Word roots (OER)

| Hebrew | Transliteration | Gloss | Root | Strong |
| --- | --- | --- | --- | --- |
| לֹא | lō’ | no, not |  | 3808 |

## Vocabulary

- he-dav-01-001
- he-dav-01-002

## Teaches

- he-dav-01-001
- he-dav-01-002

## Assumes

- he-dav-01-001

## Did You Know

According to OSHB/MorphHB (CC BY 4.0), the most frequent word in this unit is …
```

- Line 1 is the heading `# Unit {n} — {title}` (separator: space-emdash-space).
- The description follows the heading (plain text until the first `## `).
- `## Summary` and other teaching headings → ordered `prose` blocks with the heading in
  `caption` and body text in `html` (paragraphs separated by blank lines; `materialize`
  wraps each paragraph in `<p>` and re-escapes `& < >`). The lesson view displays the
  caption as a heading; `textify` restores the same Markdown section heading.
- `## Word roots (OER)` → one `table` block (GFM table: Hebrew, Transliteration,
  Gloss, Root, Strong), only emitted when at least one unit item has root/strong data.
- `## Vocabulary` → one `vocab` block (a `- `-bullet list of item ids).
- `## Teaches` / `## Assumes` → bullet lists of item ids (teaches = the unit's items;
  assumes = the *prior* unit's items for the spiral recap). Absent for unit 1's
  `Assumes`. These materialize to the lesson's `teaches`/`assumes` lists.
- `## Did You Know` → a single paragraph (`didYouKnow` string) generated from OSHB
  token counts, attributed to the source+license.
- `ATTRIBUTION.md` is release content, not a lesson; keep author/title/URI/license and
  adaptation notes there for the prose and datasets it adapts (e.g. ADR-013 for the OER course).

All of `Word roots (OER)`, `Teaches`, `Assumes`, `Did You Know` are written by
`build/generate-lessons.py` (P6-T2); an author editing a chapter keeps `Summary` +
`Vocabulary` + description and can hand-adjust the rest. `materialize` defaults a
section to `[]`/`""`/missing when its heading is absent.

## 4. Block types (schema ↔ markdown)

| JSON block type | Markdown representation | Status |
|---|---|---|
| `prose` | `## {caption}` section (defaults to `Summary`) | implemented |
| `vocab` | `## Vocabulary` `-` list | implemented |
| `table` | GFM table under a `## Word roots (OER)` heading | implemented (P6-T2) |
| `paradigm` | same as `table` | spec'd, add when used |
| `callout` | `## {variant}` blockquote | spec'd, add when used |

## 5. Round-trip guarantee

- `materialize(textify(json))` produces a schema-valid JSON the engine consumes unchanged.
- `textify(materialize(text))` is byte-identical to the input `text` (idempotent).
- The engine is **not** modified by this work: it keeps reading JSON only. The new
  `table` blocks and `teaches`/`assumes`/`didYouKnow`/`extra.*` fields flow through
  the existing JSON schema (see `docs/DATA-MODEL.md`).

## 6. Commands

```bash
python build/textify.py --course courses/biblical-hebrew-davidson     # JSON -> content/
python build/materialize.py --course courses/biblical-hebrew-davidson # content/ -> JSON
python scripts/validate courses/biblical-hebrew-davidson
python scripts/e2e.py courses/biblical-hebrew-davidson --units 2
```
