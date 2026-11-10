# Prompt — Unit recap

> **Purpose**: regenerate (or extend) a unit's `## Summary` from its vocabulary + grammar
> points. Use when the extracted summary is a rough placeholder and needs re-authoring
> (see `docs/STATUS.md` P6-T2) or when a student wants a condensed study recap.
> Task: P5-T5. Convention: `docs/AI-EXAMS.md` §4.

## Inputs

| Placeholder | What to paste |
|---|---|
| `{{UNIT}}` | Unit number (e.g. 12) |
| `{{CHAPTER}}` | The full text of `content/chapters/{{NN}}.md` for that unit |
| `{{VOCAB}}` | The unit's rows from `content/vocab.csv` (filtered by `unit`) |
| `{{LENGTH}}` | Desired length: `short` (2–3 sentences), `medium` (1 paragraph), `long` (2–3 paragraphs) |

## Template

> You are a Hebrew-language tutor. Rewrite the **Summary** section below for Unit
> {{UNIT}} of a Biblical Hebrew course. Use ONLY the attached chapter text and
> vocabulary; never invent grammar rules or glosses.
>
> Requirements:
> - Keep `{{LENGTH}}` length.
> - Plain, student-facing prose; 2–5 short paragraphs separated by blank lines.
> - Mention the unit's key grammar points (verb forms, noun features, etc.) as they
>   appear in the chapter.
> - For each vocabulary item, keep the script form + transliteration + gloss together
>   so the recap doubles as a glanceable word list.
> - Do NOT reproduce copyrighted textbook prose verbatim — paraphrase.
>
> Return only the summary prose (no headings, no preamble).
>
> ## Unit {{UNIT}} chapter
>
> {{CHAPTER}}
>
> ## Unit {{UNIT}} vocabulary
>
> {{VOCAB}}