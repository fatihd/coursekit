import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

COURSE = Path("courses/biblical-hebrew-davidson")
UNITS = {u["title"]: u["n"] for u in json.loads((COURSE / "units.json").read_text(encoding="utf-8"))["units"]}


class DavidsonContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (COURSE / "content" / "vocab.csv").open(
            newline="", encoding="utf-8",
        ) as vocab_file:
            cls.items = list(csv.DictReader(vocab_file))

    def test_noun_examples_sit_in_their_noun_units(self):
        expected = {
            "Strong Nouns (First Declension)": {"דָּבָר"},
            "Segholate Nouns (Second Declension)": {"מֶלֶךְ", "סֵפֶר"},
            "Participial Nouns (Third Declension)": {"כֹּהֵן"},
            "Nouns from Hollow Roots": {"עַיִן", "קוֹל", "אוֹר", "מָוֶת", "מָקוֹם", "תָּוֶךְ"},
            "Nouns from Double-Ayin Roots": {"עָם", "הַר", "חֹק", "גַּן"},
            "Nouns from Lamed-He Roots": {"שָׂדֶה", "מַחֲנֶה", "פָּנִים", "מַיִם", "בַּת", "בַּיִת", "אָח", "בֵּן"},
        }
        for title, forms in expected.items():
            with self.subTest(unit=title):
                rows = [item for item in self.items if int(item["unit"]) == UNITS[title]]
                self.assertTrue(forms.issubset({row["scriptForm"] for row in rows}))

    def test_numerals_unit_teaches_the_core_numerals(self):
        core = {item["gloss"] for item in self.items
                if int(item["unit"]) == UNITS["Numbers One to Ten"] and item["category"] == "numeral"}
        for gloss in ("one", "two", "three", "four", "five", "six", "seven", "eight",
                      "nine", "ten", "hundred", "thousand"):
            with self.subTest(gloss=gloss):
                self.assertIn(gloss, core)

    def test_vocabulary_is_spread_evenly(self):
        counts = {}
        for item in self.items:
            counts[int(item["unit"])] = counts.get(int(item["unit"]), 0) + 1
        for unit in range(UNITS["Roots and Patterns"], max(UNITS.values()) + 1):
            with self.subTest(unit=unit):
                self.assertTrue(4 <= counts.get(unit, 0) <= 18, counts.get(unit, 0))

    def test_vocabulary_layout_is_up_to_date(self):
        result = subprocess.run(
            [sys.executable, "build/rebalance_vocab.py", "--course", str(COURSE),
             "--layout", "build/_sources/davidson/vocab-layout.json", "--check"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_numerals_cover_gendered_11_to_19_and_feminine_ordinals(self):
        numerals = [
            item for item in self.items
            if UNITS["Numbers One to Ten"] <= int(item["unit"]) <= UNITS["Numbers One to Ten"] + 20
            and item["category"] == "numeral"
        ]
        gloss_gender = {(item["gloss"], item["gender"]) for item in numerals}
        numbers = {
            11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
            15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
            19: "nineteen",
        }
        for n, name in numbers.items():
            with self.subTest(number=n):
                self.assertIn((f"{name} (m)", "m"), gloss_gender)
                self.assertIn((f"{name} (f)", "f"), gloss_gender)
        for ordinal in (
            "first", "second", "third", "fourth", "fifth", "sixth", "seventh",
            "eighth", "ninth", "tenth",
        ):
            with self.subTest(ordinal=ordinal):
                self.assertIn((f"{ordinal} (f)", "f"), gloss_gender)
        hundreds = {
            300: "three", 400: "four", 500: "five", 600: "six", 700: "seven",
            800: "eight", 900: "nine",
        }
        for n, name in hundreds.items():
            with self.subTest(hundred=n):
                self.assertIn((f"{name} hundred", ""), gloss_gender)

    def test_vocab_has_unique_display_forms_and_transliterations(self):
        for field in ("scriptForm", "gloss", "transliteration"):
            values = [item[field] for item in self.items if item[field]]
            with self.subTest(field=field):
                self.assertEqual(len(values), len(set(values)))


if __name__ == "__main__":
    unittest.main()
