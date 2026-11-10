# AI-ASSISTED EXAMS & PROMPTS

> Design notes for P5 Theme B. See `docs/ROADMAP.md` P5 and ADR-009.
> The goal: a student can generate (or reuse) practice exams and have a free online AI
> mark them, using only plain-text files and a documented convention.

## 1. The exam workflow

A self-contained "exam pack" is three plain-text files:

1. **`rubric.md`** — the marking rubric: per-question marks, acceptable/partial-answer
   guidance, and the grading bands (e.g. full / partial / nil).
2. **`exam-blank.md`** — the empty exam: questions with blank answer slots.
3. **`exam-answers.md`** — the student's written answers (the same file, filled in).

The student uploads **all three** (or a single file containing rubric + questions +
answers) to a free AI (ChatGPT, Grok, Bing Copilot, Gemini, …) with a short marking
instruction. The AI returns marks + feedback per question, keyed to the rubric.

## 2. Answer-format conventions (decided in P5-T7)

Answers must be machine-parseable by an LLM. Decisions:

- **Canonical form — the ```` ```answer ```` fenced block**, one answer per `Q<n>:` line:

  ````
  ```answer
  Q1: the house
  Q2: he walked
  ```
  ````

  Rules:
  - One `Q<n>:` line per question; `n` must match the blank's question ids exactly.
  - Multi-line answers: keep typing after the `Q<n>:` line until the next `Q<` start
    (blank lines inside a multi-line answer are permitted).
  - Empty/skipped answer: write the line `Q<n>: —`.
  - Hebrew/Greek answers may be pointed and may carry a transliteration in
    parentheses; a gloss-only answer is acceptable where the question asks for gloss.
  - Nothing outside the block is marked — put all answers inside one block.
- **Fallback for single-token answers** that must sit inside a question line: inline
  `[answer]` brackets, e.g. `Q6. the mother is [אֵם]`. Only used when a fenced block
  would be awkward (a rubric with a couple of inline probes, mixed short-form items).

### Upload order + marking instruction

The student uploads **rubric, then blank, then answers** (order matters — the AI
should read the rubric first), or a **single combined file** containing all three in
that order. Recite the paste-ready instruction verbatim:

> Mark the attached exam against the attached rubric. Follow the answer-format
> convention in the exam header exactly. Output per-question marks, then section
> subtotals, then the total and the final band from the rubric. For each mark less
> than full, give one line of feedback.

One canonical marking-output shape (per-question mark, then totals):

```
Q1: 2/2
Q2: 1/2 — gloss imprecise ("boy" for "young man, lad")
...
Section A: 8/10
...
Total: 28/38 → C (70%)
```

## 3. Rubric shape

**Conformance rule:** every exam pack's rubric MUST state (a) the answer-format
convention (canonical ```` ```answer ```` block, or the fallback) and (b) the
marking-output format (per-question marks → section subtotals → total → band), so the
pack is self-contained and AI-markable with no extra context. The rubric is plain text
that pairs every question id with its marks and partial-credit rules.
Mechanical packs for any `part<N>`/`unit<N>` can be generated with
`scripts/export-exam <course> <scope>` (P5-T8; seeded, reproducible, vocab-only).
Model:

```
# Exam: Biblical Hebrew — Foundations
Total: 40

Q1 (translate, 4 pts) — 1 pt per correct word; gloss may be any accepted synonym.
Q2 (match, 6 pts) — 1 pt per correct pair; no partial within a pair.
Q3 (paradigm, 10 pts) — 2 pts per correct form; −1 per wrong gender/number.
…
Grading bands: A ≥90%, B ≥80%, C ≥70%, D ≥60%.
```

The AI marks strictly against the rubric, so the rubric must be explicit about what
counts as a correct answer (gloss variants, transliteration tolerance, niqqud
requirements).

## 4. Prompt templates

`prompts/*.md` (P5-T5) are reusable, parameterized templates. Each states its inputs
(e.g. unit range, level, mix of exercise types) and the instruction to paste alongside
the course text. Types:

| Prompt file | Type | Purpose |
|---|---|---|
| `prompts/practice-quiz.md` | **practice-quiz** | N questions from a unit's vocab/grammar |
| `prompts/practice-exam.md` | **practice-exam** | full exam (rubric + blank + key) over a part or level |
| `prompts/gap-fill.md` | **gap-fill** | cloze from biblical verses for a unit |
| `prompts/translation-drill.md` | **translation-drill** | Hebrew→English / English→Hebrew batches |
| `prompts/explain-verse.md` | **explain-verse** | walk through a unit's reading verse |
| `prompts/recap.md` | **recap** | regenerate a unit summary from its vocab + grammar points |
| `prompts/study-guide.md` | **study-guide** | a curriculum map / study plan from unit metadata |

Each template fills `{{PLACEHOLDER}}` inputs from `courses/<c>/content/` (chapters +
`vocab.csv`); paste the template + the filled course text into a free AI.

## 5. Grounding material

Prompts reference the plaintext content from P5 Theme A (chapters, word lists,
exercises). The AI is instructed to draw only from the provided material (which is the
student's own course content + OER), never to invent glosses or grammar — this is the
copyright/accuracy guardrail, mirroring ADR-004.

## 6. More ideas in this vein

- Anki/CSV export of word lists; Obsidian vault; EPUB/PDF of chapters.
- Strong's-number / frequency keying for Bible-software interop.
- TTS/audio prompts for pronunciation.
- Socratic "study companion" (interactive quiz, not a static exam).
- Rubric-guided feedback templates per exercise type (transliteration, translation,
  paradigm-tag, …).
- Human-readable `progress.md` export (alongside `progress.json`).
- Difficulty/type-mix parameters on the practice-exam prompt.
- "Explain this verse" prompts for reading units.
- Grammar reference authored as `.md` (portable, not slide-locked).
- Repeatable generation (same seed/parameters) so the student can retake an exam
  without a scheduler — consistent with the non-SRS constraint (ADR-005).