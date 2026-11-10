# engine/

> Reusable, language-agnostic course engine. Vanilla JS + ES modules, no build step.
> See `docs/ARCHITECTURE.md` for the module map. See `docs/EXERCISE-TYPES.md` for the
> plugin contract.

## Implemented (P3-T1)

- `main.js` — bootstrap: load `course.json`, route to views.
- `store.js` — progress state (course-file load, localStorage cache/fallback, save +
  unit-state computation).
- `views/roadmap.js` — visible unit map in 3 parts; node states.

## Implemented runtime pieces

- `views/lesson.js` — paged teaching; typed blocks; "Mark lesson read → start drills" gate.
- `views/drill.js` — one item, immediate feedback, score → unlock next.
- `views/review.js` — optional Warm-up mixed set from known set.
- `exercise-types/` — plugin registry (`{id, generate, render, grade}`).
- `keyboards/` — on-screen keyboards (`he_IL`, `el_GR`, `arc`).
- `translit/` — per-language transliteration schemes.
- `fonts/` — bundled OFL fonts (Ezra SIL, SBL Hebrew/Greek, GFS Didot).
- `config/` — runtime config loaded from `course.json.script`.

## Running

```bash
python scripts/run courses/biblical-hebrew-davidson   # serves over HTTP + opens browser
```

The course `app/` shell imports the engine via a dev symlink (`courses/*/engine`),
created by `scripts/run`. At release, `scripts/release-course` vendors a pinned copy.
