# Prompt — Explain this verse

> **Purpose**: walk through a unit's reading verse word-by-word — parse forms, explain
> grammar, give a smooth translation — so the student can study the "Review" reading
> units (e.g. Ruth) with support. Task: P5-T5. Convention: `docs/AI-EXAMS.md` §4.

## Inputs

| Placeholder | What to paste |
|---|---|
| `{{VERSE_TEXT}}` | The verse(s) in pointed Hebrew |
| `{{TRANSLIT}}` | Optional literal transliteration |
| `{{UNIT}}` | The unit the verse belongs to |
| `{{VOCAB}}` | The `content/vocab.csv` rows for that unit + earlier units (known set) |
| `{{DEPTH}}` | `brief` (gloss only) / `full` (word-by-word parse) — default `full` |

## Template

> You are a Hebrew-reading tutor. Explain this verse from Unit {{UNIT}} of a Biblical
> Hebrew course. Use ONLY the attached vocabulary and course facts.
>
> Depth {{DEPTH}}:
> - `full`: for each word give script form → parse (part of speech, gender/number where
>   applicable, verbal form) → gloss → how it links to the sentence. Then 1–2 sentences
>   on the overall grammar, then a smooth English rendering.
> - `brief`: give script → gloss per word plus the smooth rendering.
>
> If a word is not in the course's known set, mark it `⚠ not yet taught` instead of
> inventing a form. Never paraphrase copyrighted study material — analyze the Hebrew
> directly.
>
> ## Verse
>
> {{VERSE_TEXT}}
>
> ## Transliteration (optional)
>
> {{TRANSLIT}}
>
> ## Known vocabulary (unit {{UNIT}} and earlier)
>
> {{VOCAB}}