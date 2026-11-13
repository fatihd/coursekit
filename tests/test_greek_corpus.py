import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))

import greek_corpus as GC  # noqa: E402
import greek_text as G  # noqa: E402

ARCHAIC = re.compile(r"\b(thou|thee|thy|thine|ye|art|hast|hath|wast|wilt|shalt|dost|doth)\b|\b\w+(?:est|eth)\b", re.I)
NOT_ARCHAIC = {"rest", "priest", "best", "west", "least", "honest", "nest", "test", "guest", "lest", "forest",
               "harvest", "beth", "seth"}


class MachenCuratedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = GC.curated_files()

    @unittest.skipUnless((ROOT / "courses" / "biblical-greek-machen").exists(), "course word list not in this tree")
    def test_every_greek_word_is_attested(self):
        self.assertEqual(GC.check(), 0)

    def test_items_are_complete(self):
        self.assertTrue(self.files)
        for path in self.files:
            data = json.loads(path.read_text(encoding="utf-8"))
            for it in data["items"]:
                with self.subTest(file=path.name, item=f"{it['part']}.{it['num']}"):
                    self.assertIn(it["part"], ("I", "II"))
                    self.assertTrue(it["prompt"].strip() and it["answer"].strip())
                    greek, english = (it["prompt"], it["answer"]) if it["part"] == "I" else (it["answer"], it["prompt"])
                    self.assertTrue(G.greek_words(greek), "Greek side has Greek")
                    self.assertFalse(G.greek_words(english.replace("(", " ").replace(")", " ")) and it["part"] == "I")

    def test_english_prompts_use_modern_you(self):
        for path in self.files:
            for it in json.loads(path.read_text(encoding="utf-8"))["items"]:
                if it["part"] != "II":
                    continue
                bad = [m.group(0) for m in ARCHAIC.finditer(it["prompt"]) if m.group(0).lower() not in NOT_ARCHAIC]
                with self.subTest(file=path.name, item=it["num"]):
                    self.assertEqual(bad, [], it["prompt"])


if __name__ == "__main__":
    unittest.main()
