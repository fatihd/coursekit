import csv
import unittest
from pathlib import Path

COURSE = Path("courses/biblical-hebrew-davidson")


class DavidsonContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (COURSE / "content" / "vocab.csv").open(
            newline="", encoding="utf-8",
        ) as vocab_file:
            cls.items = list(csv.DictReader(vocab_file))

    def test_weak_noun_examples_are_taught_after_their_verb_units(self):
        expected = {
            11: {"מֶלֶךְ", "סֵפֶר", "דָּבָר", "כֹּהֵן"},
            41: {"עַיִן", "קוֹל", "אוֹר", "מָוֶת", "מָקוֹם", "תָּוֶךְ"},
            43: {"עָם", "הַר", "חֹק", "גַּן"},
            45: {"שָׂדֶה", "מַחֲנֶה", "פָּנִים", "מַיִם", "בַּת", "בַּיִת", "אָח", "בֵּן"},
        }
        for unit, forms in expected.items():
            with self.subTest(unit=unit):
                rows = [item for item in self.items if int(item["unit"]) == unit]
                self.assertTrue(forms.issubset({row["scriptForm"] for row in rows}))
                self.assertGreaterEqual(sum(bool(row["plural"]) for row in rows), 2)

    def test_numerals_cover_gendered_11_to_19_and_feminine_ordinals(self):
        numerals = [
            item for item in self.items
            if int(item["unit"]) == 19 and item["category"] == "numeral"
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
