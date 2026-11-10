# Prompt — Practice quiz

> **Purpose**: generate N questions over a unit's (or unit range's) vocab + grammar for
> quick self-checking. Task: P5-T5. Convention: `docs/AI-EXAMS.md` §4.

## Inputs

| Placeholder | What to paste |
|---|---|
| `{{UNIT_RANGE}}` | e.g. `1–3` or `12` |
| `{{N}}` | Number of questions (e.g. 10) |
| `{{COURSE_TEXT}}` | The `content/chapters/NN.md` files for the range + the matching `content/vocab.csv` rows |
| `{{TYPE_MIX}}` | Desired mix, e.g. `6 vocab, 2 grammar, 2 reading` — omit for a sensible default |
| `{{DIFFICULTY}}` | `easy` / `medium` / `hard` (default `medium`) |

## Template

> You are a Hebrew tutor making a practice quiz. Make exactly {{N}} questions for
> Biblical Hebrew units {{UNIT_RANGE}}.
>
> Use ONLY the attached course text. Never invent words, glosses, or grammar not in
> the material.
>
> Question type mix: {{TYPE_MIX}}. Suggested shapes (adapt to the unit): script→gloss,
> gloss→script, transliteration→script, construct-chain building, verb-form parsing,
> and short reading/translation.
>
> Format *every* question and its answer exactly like this:
>
> ```
> Q<n>. <question>
> A: <answer>
> ```
>
> Difficulty: {{DIFFICULTY}}. Keep questions crisp; one clear answer each; accept
> common synonym glosses where the vocab allows (note alternatives in `( )`).

> ## Course text
>
> {{COURSE_TEXT}}