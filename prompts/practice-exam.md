# Prompt — Practice exam

> **Purpose**: generate a full practice exam (rubric + blank + answer key) over a part
> or level, self-contained and AI-markable per `docs/AI-EXAMS.md` §1–§3. Task: P5-T5
> (prompt); P5-T6 (example exams + rubrics); P5-T7 (answer-format convention).

## Inputs

| Placeholder | What to paste |
|---|---|
| `{{PART_RANGE}}` | Part or unit range (e.g. `Part 1 (units 1–9)` or `units 10–19`) |
| `{{TOTAL}}` | Total exam marks (e.g. `40`) |
| `{{COURSE_TEXT}}` | The `content/chapters/NN.md` files for the range + the matching `content/vocab.csv` rows |
| `{{TYPE_MIX}}` | Desired question-type mix, e.g. `2 translate, 2 match, 1 paradigm, 1 reading` |
| `{{BANDS}}` | Grading bands, e.g. `A ≥90%, B ≥80%, C ≥70%, D ≥60%` |

## Template

> You are composing a markable practice exam for Biblical Hebrew units
> {{PART_RANGE}}. Output THREE clearly separated sections:
>
> ## 1. Rubric
>
> List every question id with its marks and partial-credit rule, then the grading bands
> ({{BANDS}}). Model:
>
> ```
> Q1 (translate, 4 pts) — 1 pt per correct word; gloss may be any accepted synonym.
> Q2 (match, 6 pts) — 1 pt per correct pair; no partial within a pair.
> ```
>
> ## 2. Exam (blank)
>
> Numbered questions with blank answer slots. Question types to include:
> {{TYPE_MIX}}. Draw ONLY from the attached course text.
>
> ## 3. Answer key
>
> Answers keyed by question id, following the rubric's acceptance rules (give the
> accepted variants, incl. transliteration tolerance where relevant).
>
> Use ONLY the attached material — never invent words, glosses, or grammar.

> ## Course text
>
> {{COURSE_TEXT}}