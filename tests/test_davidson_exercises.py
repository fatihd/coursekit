"""Provenance and shape checks for Davidson OCR exercise inventories.

These exercises are OCR-derived from the 1924 *Key to the Exercises*; the test
guards the structural guarantees we can promise (all detected exercise blocks,
scan provenance, and answer-number order) rather than the OCR text itself, which
is best-effort and links back to the original scans.
"""

import json
import unittest
from pathlib import Path

COURSE = Path("courses/biblical-hebrew-davidson")
AUTHORED = COURSE / "authored"
CHAPTERS = COURSE / "content" / "chapters"


def _chapter_sections(unit: int) -> set[int]:
    text = (CHAPTERS / f"{unit:02d}.md").read_text(encoding="utf-8")
    import re

    return {int(n) for n in re.findall(r"\u00a7+\s*(\d{1,2})", text)}


class DavidsonExercisesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = sorted(AUTHORED.glob("*.json"))

    def test_has_recovered_exercises(self):
        self.assertGreater(len(self.files), 10)

    def test_inventory_record_count_matches_emitted_items(self):
        emitted = sum(
            len(json.loads(path.read_text(encoding="utf-8"))["items"])
            for path in self.files
        )
        inventory = json.loads(
            (Path("build/_sources/davidson") / "exercise-inventory.json").read_text(
                encoding="utf-8"
            )
        )
        pairs = json.loads(
            (Path("build/_sources/davidson") / "pair-inventory.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(inventory["stats"]["candidateRecords"], inventory["stats"]["records"])
        self.assertGreaterEqual(inventory["stats"]["records"], 80)
        # The emitted authored items are the ok/weak pair placements.
        emitted_pairs = sum(
            1 for record in pairs["pairs"] if record["sanity"] != "suspect"
        )
        self.assertGreaterEqual(emitted, emitted_pairs)
        self.assertGreater(emitted, 100)

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
                        ("translate-phrase", "mcq", "translit-normalize"),
                    )
                    if item["type"] == "translate-phrase":
                        self.assertTrue(item["accepted"])
                    elif item["type"] == "mcq":
                        self.assertGreaterEqual(len(item["options"]), 2)
                    else:
                        self.assertTrue(item["answer"])

    def test_unit_maps_to_a_cited_section(self):
        # Every unit that carries recovered items must cite a Davidson § whose
        # exercise produced them. (Sections were matched, so a unit's section
        # must appear in its chapter's Source block.)
        for path in self.files:
            unit = int(path.stem)
            data = json.loads(path.read_text(encoding="utf-8"))
            cited = _chapter_sections(unit)
            for item in data["items"]:
                section = _section_of(item)
                with self.subTest(file=path.name, section=section):
                    self.assertIn(section, cited, f"§{section} not cited by unit {unit}")

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

    def test_pairing_sanity_gates_emission(self):
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
        emitted = 0
        for path in self.files:
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data["items"]:
                source = item["source"]
                self.assertIn(source["sanity"], ("ok", "weak"), path.name)
                self.assertIn("sanityScore", source)
                self.assertTrue(source["promptUrl"].startswith("https://archive.org/details/"))
                self.assertTrue(source["answerUrl"].startswith("https://archive.org/details/"))
                emitted += 1
        self.assertGreater(emitted, 100)

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


def _section_of(item: dict) -> int:
    import re

    citation = item["source"]["citation"]
    match = re.search(r"exercise on \u00a7(\d{1,2})", citation)
    assert match, citation
    return int(match.group(1))


if __name__ == "__main__":
    unittest.main()
