# Prompt — Study guide / curriculum map

> **Purpose**: turn a course's/part's unit metadata into a study plan or curriculum
> map — what to do in what order, what each unit teaches, and how units build on each
> other. Task: P5-T5. Convention: `docs/AI-EXAMS.md` §4.

## Inputs

| Placeholder | What to paste |
|---|---|
| `{{UNIT_META}}` | The unit list from `courses/<c>/course.json` (ids, n, titles, parts) — or a pasted summary |
| `{{SCOPE}}` | `part 1`, `all`, or a unit range (e.g. `10–19`) |
| `{{GOAL}}` | e.g. `one week to midterm` / `map dependencies` / `daily 20-min plan` |
| `{{CHAPTERS}}` | Optional: `content/chapters/NN.md` summaries if grammar points per unit are wanted |

## Template

> Build a study guide for a Biblical Hebrew course, scope {{SCOPE}}, for this goal:
> {{GOAL}}.
>
> Use the unit metadata and (if given) chapter summaries as the ONLY source of what
> each unit teaches. In particular:
>
> 1. A unit-by-unit map of the scope: unit number, title, and 1-line "what you learn".
> 2. Which units depend on which (obvious prerequisites only — from titles/order, do not invent links).
> 3. A suggested session order (break into blocks that fit the goal).
> 4. A short checklist to consider a unit "done" (read chapter → drill vocab → pass drill).
>
> Never invent unit titles or grammar not present in the supplied metadata.

> ## Unit metadata
>
> {{UNIT_META}}
>
> ## Chapter summaries (optional)
>
> {{CHAPTERS}}