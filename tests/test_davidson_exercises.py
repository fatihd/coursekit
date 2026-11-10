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
AUTHORED = COURSE / "authored"


class DavidsonExercisesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = sorted(AUTHORED.glob("*.json"))

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
            for item in json.loads(path.read_text(encoding="utf-8"))["items"]:
                refs.append(item["source"]["exwb"])
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
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data["items"]:
                with self.subTest(file=path.name):
                    source = item.get("source", {})
                    self.assertIn("promptUrl", source)
                    self.assertIn("answerUrl", source)
                    self.assertTrue(source["promptUrl"].startswith("https://archive.org/details/"))
                    self.assertTrue(source["answerUrl"].startswith("https://archive.org/details/"))
                    self.assertIn("/page/n", source["promptUrl"])
                    self.assertIn("/page/n", source["answerUrl"])

    def test_items_use_supported_pairing_types(self):
        for path in self.files:
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data["items"]:
                with self.subTest(file=path.name):
                    self.assertIn(
                        item["type"],
                        ("translate-phrase", "mcq", "translit-normalize", "parse-form"),
                    )
                    if item["type"] == "translate-phrase":
                        self.assertTrue(item["accepted"])
                    elif item["type"] == "mcq":
                        self.assertGreaterEqual(len(item["options"]), 2)
                    elif item["type"] == "parse-form":
                        self.assertTrue(item["readings"])
                        options = {f["key"]: f["options"] for f in item["fields"]}
                        for reading in item["readings"]:
                            for key, value in reading.items():
                                self.assertIn(value, options.get(key, []), key)
                    else:
                        self.assertTrue(item["answer"])

    def test_items_sit_in_their_mapped_unit(self):
        blocks = json.loads(UNIT_MAP.read_text(encoding="utf-8"))["blocks"]
        for path in self.files:
            unit = int(path.stem)
            for item in json.loads(path.read_text(encoding="utf-8"))["items"]:
                stem = item["source"]["exwb"].split("#")[0]
                with self.subTest(file=path.name, block=stem):
                    self.assertEqual(blocks[stem]["unit"], unit)

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
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data["items"]:
                answer_leaf = re.search(r"/page/n(\d+)/", item["source"]["answerUrl"])
                prompt_leaf = re.search(r"/page/n(\d+)/", item["source"]["promptUrl"])
                with self.subTest(file=path.name, stimulus=item["stimulus"]):
                    self.assertIsNotNone(answer_leaf)
                    self.assertIsNotNone(prompt_leaf)
                    self.assertGreater(int(answer_leaf.group(1)), 0)


if __name__ == "__main__":
    unittest.main()
