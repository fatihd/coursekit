# Prompt — Gap-fill (cloze from verses)

> **Purpose**: cloze/gap-fill exercises generated from biblical verses for a unit —
> gives the student real-text reading practice with the unit's vocab. Task: P5-T5.
> Convention: `docs/AI-EXAMS.md` §4.

## Inputs

| Placeholder | What to paste |
|---|---|
| `{{UNIT_RANGE}}` | Unit range whose vocabulary should be targeted (e.g. `1–3`) |
| `{{N}}` | Number of cloze items (e.g. 8) |
| `{{VERSE_TEXTS}}` | Short biblical verses (Hebrew text + transliteration optional + a working English) that use words within the course vocab |
| `{{VOCAB}}` | The `content/vocab.csv` rows for the unit range (so the AI knows which words to blank) |
| `{{GAP_FOCUS}}` | What to gap: `vocab` (target words), `forms` (e.g. verb endings), `prepositions` — default `vocab` |

## Template

> Make {{N}} gap-fill items for Biblical Hebrew units {{UNIT_RANGE}}.
> Gap target: {{GAP_FOCUS}}.
>
> Use ONLY the supplied verses and vocabulary. Replace each target word with a
> blank `____`, and after each item give the answer key (script form + gloss).
> Prefer verses that contain the unit's vocabulary; if a supplied verse has no
> suitable target, say so rather than inventing one.
>
> Output format:
>
> ```
> Item <n>. <verse with ______>
> Answer: <scriptForm> — <gloss>
> ```
>
> ## Verses
>
> {{VERSE_TEXTS}}
>
> ## Vocabulary available (unit range)
>
> {{VOCAB}}