# engine/

> Reusable, language-agnostic course engine. Vanilla JS + ES modules, no build step.
> See `docs/ARCHITECTURE.md` for the module map. See `docs/EXERCISE-TYPES.md` for the
> plugin contract.

## Implemented (P3-T1)

- `main.js` — bootstrap: load `course.json`, route to views.
- `store.js` — progress in `localStorage`, Export/Import with merge (ADR-019), unit-state
  computation.
- `views/roadmap.js` — visible unit map in 3 parts; node states.

## Implemented runtime pieces

- `views/lesson.js` — paged teaching; typed blocks; "Mark lesson read → start drills" gate.
- `views/drill.js` — one item, immediate feedback, score → unlock next.
- `views/review.js` — optional Warm-up mixed set from known set.
- `exercise-types/` — plugin registry (`{id, generate, render, grade}`).
- `keyboard.js` + `keyboards/he_IL.js` — on-screen keyboard (Hebrew; Greek is planned, ROADMAP P11).
- `session.js` — builds a drill session (authored items first, then generated fill, spiral review).
- `knowledge.js` — known set and recap from completed units.
- Not yet present: bundled fonts (the course's `fontFile` falls back to system fonts), other
  keyboards, transliteration schemes.

Part 1 of the three-part split (AGENTS.md §2): engine code imports only engine files; it must not
read `build/` or `exwb/`.

## Running

```bash
python scripts/run courses/biblical-hebrew-davidson   # serves over HTTP + opens browser
```

The course `app/` shell imports the engine via a dev symlink (`courses/*/engine`),
created by `scripts/run`. At release, `scripts/release-course` vendors a pinned copy.
