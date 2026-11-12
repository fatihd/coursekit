"""Provenance and shape checks for the Davidson exercises.

The OCR inventories (grammar, Key, pairs) are best-effort build artifacts; the
course drills come from the hand-checked exwb set (`exwb/curated/`) through
`build/exwb_to_authored.py` (ROADMAP P9-T6), mapped to units by
`build/_sources/davidson/exwb-units.json`.
"""

import json
import unittest
from pathlib import Path

COURSE = Path("courses/biblical-hebrew-davidson")
CURATED = Path("exwb/curated")
UNIT_MAP = Path("build/_sources/davidson/exwb-units.json")
GRAMMAR = Path("build/_sources/davidson/grammar-units.json")
TAGS = Path("build/_sources/davidson/sentence-grammar.json")
PHRASES = Path("build/_sources/davidson/indefinite-phrases.json")
RECOGNITION = Path("build/_sources/davidson/recognition.json")
AUTHORED = COURSE / "authored"
RUNG_KEYS = {"tf", "choice", "fill", "translate", "pointed", "parse", "form", "point"}


def items_of(path):
    """A unit file's items with each item's source resolved from the file's `sources`."""
    data = json.loads(path.read_text(encoding="utf-8"))
    sources = data.get("sources", {})
    return [{**it, "source": sources.get(it.get("src"), it.get("source", {}))} for it in data["items"]]


class DavidsonExercisesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = sorted(AUTHORED.glob("[0-9][0-9].json"))

    def test_has_recovered_exercises(self):
        self.assertGreater(len(self.files), 10)

    def test_emitted_items_are_the_unheld_curated_items(self):
        unit_map = json.loads(UNIT_MAP.read_text(encoding="utf-8"))
        held = set(unit_map["held"])
        curated = {
            p.stem: len(json.loads(p.read_text(encoding="utf-8"))["items"])
            for p in CURATED.glob("davidson-*.json")
        }
        refs = []
        for path in self.files:
            refs += [s["exwb"] for s in json.loads(path.read_text(encoding="utf-8"))["sources"].values() if "exwb" in s]
        self.assertEqual(len(refs), len(set(refs)))
        self.assertEqual(len(refs), sum(n for stem, n in curated.items() if stem not in held))
        self.assertFalse({r.split("#")[0] for r in refs} & held)

    def test_generated_files_are_up_to_date(self):
        import subprocess
        import sys

        r = subprocess.run(
            [sys.executable, "build/exwb_to_authored.py", "--course", str(COURSE), "--check"],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_each_item_has_scan_provenance(self):
        for path in self.files:
            for item in items_of(path):
                with self.subTest(file=path.name):
                    source = item.get("source", {})
                    self.assertIn("promptUrl", source)
                    self.assertTrue(source["promptUrl"].startswith("https://archive.org/details/"))
                    self.assertIn("/page/n", source["promptUrl"])
                    if item.get("shape") == "recognition":
                        continue
                    self.assertIn("answerUrl", source)
                    self.assertTrue(source["answerUrl"].startswith("https://archive.org/details/"))
                    self.assertIn("/page/n", source["answerUrl"])

    def test_items_use_supported_pairing_types(self):
        for path in self.files:
            for item in items_of(path):
                with self.subTest(file=path.name):
                    self.assertIn(
                        item["type"],
                        ("translate-phrase", "mcq", "translit-normalize", "parse-form", "true-false"),
                    )
                    self.assertIn(item["id"].rsplit(".", 1)[1], RUNG_KEYS)
                    self.assertIn(item["rung"], range(1, 6))
                    if item["type"] == "translate-phrase":
                        self.assertTrue(item["accepted"])
                    elif item["type"] == "true-false":
                        self.assertIsInstance(item["answer"], bool)
                        self.assertTrue(item["statement"])
                    elif item["type"] == "mcq":
                        self.assertGreaterEqual(len(item["options"]), 2)
                        self.assertIn(item["answer"], item["options"])
                        self.assertEqual(len(item["options"]), len(set(item["options"])))
                    elif item["type"] == "parse-form":
                        self.assertTrue(item["readings"])
                        options = {f["key"]: f["options"] for f in item["fields"]}
                        for reading in item["readings"]:
                            for key, value in reading.items():
                                self.assertIn(value, options.get(key, []), key)
                    else:
                        self.assertTrue(item["answer"])

    def test_every_sentence_has_the_ladder(self):
        rungs = {}
        for path in self.files:
            for item in items_of(path):
                if item["shape"] in ("en-he", "he-en"):
                    rungs.setdefault(item["src"], set()).add(item["rung"])
        for src, got in rungs.items():
            with self.subTest(sentence=src):
                self.assertTrue({1, 2, 4} <= got, sorted(got))

    def test_ladder_index_matches_the_units(self):
        index = json.loads((AUTHORED / "ladder.json").read_text(encoding="utf-8"))["units"]
        for path in self.files:
            counts = {}
            for item in items_of(path):
                counts[str(item["rung"])] = counts.get(str(item["rung"]), 0) + 1
            with self.subTest(file=path.name):
                self.assertEqual(index[str(int(path.stem))], dict(sorted(counts.items())))

    def test_phrases_without_the_article_come_before_it(self):
        """Article-less copies sit in units 14-15; the exercise with the article stays in its own unit."""
        by_unit = {int(p.stem): list(items_of(p)) for p in self.files}
        tf = [i for i in by_unit[14] if i["id"] == "s11-B9i.choice"][0]
        self.assertEqual(tf["answer"], "A good man")
        self.assertIn("The good man", tf["options"])
        self.assertIn("(Some) good men", tf["options"])
        self.assertTrue(any(i["src"] == "s11-B9" for i in by_unit[17]))
        self.assertTrue(any(i["src"] == "s12-B5i" for i in by_unit[15]))

    def test_items_sit_in_their_unit(self):
        """Sentences sit in the first unit that teaches all their grammar; other items in their block's unit."""
        blocks = json.loads(UNIT_MAP.read_text(encoding="utf-8"))["blocks"]
        grammar = json.loads(GRAMMAR.read_text(encoding="utf-8"))
        units = {k: v["unit"] for k, v in grammar["features"].items()}
        tags = json.loads(TAGS.read_text(encoding="utf-8"))["sentences"]
        phrases = {p["from"]: p["unit"] for p in json.loads(PHRASES.read_text(encoding="utf-8"))["phrases"]}
        recognition = json.loads(RECOGNITION.read_text(encoding="utf-8"))["units"]
        for path in self.files:
            unit = int(path.stem)
            for item in items_of(path):
                if item["shape"] == "phrase":
                    with self.subTest(file=path.name, item=item["id"]):
                        self.assertEqual(phrases[item["source"]["adaptedFrom"]], unit)
                    continue
                if item["shape"] == "recognition":
                    with self.subTest(file=path.name, item=item["id"]):
                        self.assertIn(str(unit), recognition)
                    continue
                ref = item["source"]["exwb"]
                with self.subTest(file=path.name, item=ref):
                    if item["shape"] in ("en-he", "he-en"):
                        self.assertIn(ref, tags)
                        self.assertEqual(unit, max([grammar["floor"]] + [units[f] for f in tags[ref]]))
                    else:
                        self.assertEqual(blocks[ref.split("#")[0]]["unit"], unit)

    def test_sentences_start_early_and_none_wait_for_the_review_units(self):
        placed = {}
        for path in self.files:
            for item in items_of(path):
                if item["shape"] in ("en-he", "he-en"):
                    placed[item["source"]["exwb"]] = int(path.stem)
        grammar = json.loads(GRAMMAR.read_text(encoding="utf-8"))
        units = {u["title"]: u["n"] for u in json.loads((COURSE / "units.json").read_text(encoding="utf-8"))["units"]}
        self.assertEqual(min(placed.values()), grammar["floor"])
        self.assertLess(max(placed.values()), units["Complete Parsing"])

    def test_full_grammar_inventory_has_every_detected_exercise_block(self):
        inventory = json.loads(
            (Path("build/_sources/davidson") / "grammar-exercise-inventory.json").read_text(
                encoding="utf-8"
            )
        )
        blocks = inventory["blocks"]
        self.assertEqual(len(blocks), 48)
        coverage = inventory["coverage"]
        self.assertGreater(coverage["totalItems"], 800)
        self.assertEqual(coverage["unrecoverableItems"], 0)
        self.assertEqual(
            coverage["recoverableItems"] + coverage["unrecoverableItems"],
            coverage["totalItems"],
        )
        for block in blocks:
            with self.subTest(block=block["id"]):
                self.assertTrue(block["headingOCR"])
                self.assertTrue(block["promptUrl"].startswith("https://archive.org/details/"))
                self.assertIn("visionRegionLines", block)
                self.assertIn("djvuRegionLines", block)
                self.assertIn("hebrewItems", block)
                self.assertIn("englishItems", block)
                self.assertNotIn("answerUrl", block)

    @unittest.skipUnless(
        Path("build/_sources/davidson/key-1924-djvu.xml").exists(),
        "scan input not fetched: python scripts/fetch-sources davidson",
    )
    def test_coordinate_key_parser_uses_printed_numbers_for_early_items(self):
        import sys

        sys.path.insert(0, "build")
        try:
            import recover_davidson_exercises as recovery

            pages = recovery.load_djvu(
                recovery.SOURCES / "key-1924-djvu.xml"
            )
            answers = recovery.parse_key(pages)
        finally:
            sys.path.pop(0)

        section_11 = next(
            answer for answer in answers if answer.section == 11 and answer.part == "B"
        )
        by_number = dict(zip(section_11.numbers, section_11.hebrew))
        self.assertGreaterEqual(len(by_number), 6)
        for number in by_number:
            self.assertIn(number, range(1, 13))
        self.assertTrue(any("אור" in text for text in by_number.values()))

        section_14 = next(
            answer for answer in answers if answer.section == 14 and answer.part == "B"
        )
        self.assertGreaterEqual(len(section_14.numbers), 6)
        self.assertIn(1, section_14.numbers)

    def test_answer_inventory_mirrors_grammar_inventory(self):
        answers = json.loads(
            (Path("build/_sources/davidson") / "key-answer-inventory.json").read_text(
                encoding="utf-8"
            )
        )
        items = answers["items"]
        self.assertGreater(len(items), 800)
        sections = {item["section"] for item in items}
        self.assertIn(11, sections)
        self.assertIn(48, sections)
        for item in items:
            with self.subTest(section=item["section"], number=item["number"]):
                self.assertIn(item["script"], ("en", "he"))
                self.assertTrue(item["text"])
                self.assertGreater(item["leaf"], 0)
                self.assertTrue(item["scanUrl"].startswith("https://archive.org/details/"))
                self.assertIn("/page/n", item["scanUrl"])
        # §11 B's Hebrew answers are numbered in the key, per the coordinate
        # parse asserted by the recover-side test.
        section_11_b = [
            item for item in items if item["section"] == 11 and item["script"] == "he"
        ]
        numbers = sorted(item["number"] for item in section_11_b)
        self.assertGreaterEqual(len(numbers), 6)
        self.assertTrue(all(1 <= number <= 12 for number in numbers))

    def test_pair_inventory_records_are_well_formed(self):
        pairs = json.loads(
            (Path("build/_sources/davidson") / "pair-inventory.json").read_text(
                encoding="utf-8"
            )
        )
        records = pairs["pairs"]
        self.assertGreater(len(records), 300)
        for record in records:
            with self.subTest(section=record["section"], direction=record["direction"]):
                self.assertIn(record["direction"], ("en->he", "he->en", "translit"))
                self.assertGreaterEqual(record["score"], 0.0)
                self.assertLessEqual(record["score"], 1.0)
                self.assertIn(record["sanity"], ("ok", "weak", "suspect"))
                self.assertGreater(record["promptLeaf"], 0)
                self.assertGreater(record["answerLeaf"], 0)

    def test_answer_source_url_uses_the_item_leaf(self):
        import re

        for path in self.files:
            for item in items_of(path):
                if item["shape"] == "recognition":
                    continue
                answer_leaf = re.search(r"/page/n(\d+)/", item["source"]["answerUrl"])
                prompt_leaf = re.search(r"/page/n(\d+)/", item["source"]["promptUrl"])
                with self.subTest(file=path.name, stimulus=item["stimulus"]):
                    self.assertIsNotNone(answer_leaf)
                    self.assertIsNotNone(prompt_leaf)
                    self.assertGreater(int(answer_leaf.group(1)), 0)

    def test_script_units_have_recognition_ladders(self):
        for unit in (6, 9, 10, 11, 12):
            with self.subTest(unit=unit):
                items = items_of(COURSE / "authored" / f"{unit:02d}.json")
                self.assertTrue(items and all(i["shape"] == "recognition" for i in items))
                self.assertEqual({i["rung"] for i in items}, {1, 2, 3})
                for item in items:
                    if item["type"] == "mcq":
                        self.assertIn(item["answer"], item["options"])
                        self.assertGreaterEqual(len(item["options"]), 2)


if __name__ == "__main__":
    unittest.main()
