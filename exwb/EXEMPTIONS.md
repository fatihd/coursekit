# Exemptions — blocks deliberately out of scope

An exercise missing from the export must always be either a known gap (in `CLAUDE.md`) or an
exemption listed here. Exemptions are user decisions, not agent choices; each one names the
block, what it contains, and why it is excluded.

| Section | Block | Exercise | Decision | Date |
|---|---|---|---|---|
| §1, §2, §3, §4, §5, §7, §9 | blocks 1, 2, 3, 4, 5, 7, 9 | Transliteration, syllable-division and reading drills (alphabet, vowel letters, Massoretic points, syllables, daghesh, quiescents) | **Held by user decision**: transcribed and kept in the workbench (curated files `curated/davidson-s01..s09.json`) as raw material for future reading exercises, but not exported for the foreseeable future. Stored as a `hold` override (`python3 -m exwb hold`), so `build`/`reset` keep them held. Release with `python3 -m exwb hold myproject <id…> --release`. | 2026-11-06 |

Earlier (2026-11-06) §1 was ignored outright; that was replaced the same day by the hold above.
Do not treat the absence of these sections from the export as a recovery failure.
