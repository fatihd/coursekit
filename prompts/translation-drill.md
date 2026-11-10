# Prompt — Translation drill

> **Purpose**: batch Hebrew→English and/or English→Hebrew translation practice over a
> unit/part's vocabulary and grammar. Task: P5-T5. Convention: `docs/AI-EXAMS.md` §4.

## Inputs

| Placeholder | What to paste |
|---|---|
| `{{UNIT_RANGE}}` | e.g. `20–22` (verb units) |
| `{{DIRECTION}}` | `he→en`, `en→he`, or `he↔en` (mixed) |
| `{{N}}` | Number of items (e.g. 12) |
| `{{VOCAB}}` | The `content/vocab.csv` rows for the unit range |
| `{{GRAMMAR_NOTES}}` | 1–3 grammar points the drill should exercise (e.g. `Qatal 3ms forms`, `construct chains`) |
| `{{INCLUDE_ANSWER_KEY}}` | `yes` / `no` (default `yes`) |

## Template

> Translate drill for Biblical Hebrew units {{UNIT_RANGE}}, direction {{DIRECTION}},
> {{N}} items. Exercise these grammar points: {{GRAMMAR_NOTES}}.
>
> Use ONLY the attached vocabulary; do not add words absent from it. Keep items to a
> plausible single clause or short phrase the student can actually build.
>
> Output numbered items; then an answer key (script + a natural English rendering,
> note accepted variants). If {{INCLUDE_ANSWER_KEY}} is `no`, omit the key.
>
> ```
> <n>. <source line>
> ...
> Answer key:
> <n>. <script/direction> — <gloss>
> ```
>
> ## Vocabulary available
>
> {{VOCAB}}