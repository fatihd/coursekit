import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

import ladder_greek as LG  # noqa: E402


class GreekLadderTests(unittest.TestCase):
    def test_greek_to_english_sentence_gets_five_rungs(self):
        items = LG.ladder("m04.1.1", ["ἀδελφὸς βλέπει ἄνθρωπον."], "A brother sees a man.",
                          ["A servant writes a law."], "gr-en", random.Random(1), {})
        self.assertEqual([it["rung"] for it in items], [1, 2, 3, 4, 5])
        self.assertEqual(items[3]["prompt"], "Translate into English")
        self.assertEqual(items[4]["rungLabel"], "Translate with accents")
        self.assertEqual(items[4]["prompt"], "Translate into Greek with full accents")
        self.assertEqual(items[4]["pointing"], "required")
        self.assertIn("＿＿＿", items[2]["stimulus"])

    def test_english_to_greek_typed_rung(self):
        items = LG.ladder("m04.2.1", ["δοῦλος γράφει νόμον."], "A servant is writing a law.", [], "en-gr",
                          random.Random(2), {})
        rung4 = next(it for it in items if it["rung"] == 4)
        self.assertEqual(rung4["prompt"], "Translate into Greek (accents not checked)")
        self.assertTrue(rung4["answerIsScript"])


if __name__ == "__main__":
    unittest.main()
