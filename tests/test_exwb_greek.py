import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "exwb"))

from exwb import detect, script  # noqa: E402

TEXT = ("1. ἀδελφὸς βλέπει ἄνθρωπον. 2. δοῦλος γράφει λόγους. ὃ. ἀπόστολοι λύουσι δούλους. "
        "4. δοῦλος λαμβάνει δῶρα. ὅ. υἱοὶ οἴκους λαμβάνουσιν. 6. ἔχομεν ἀδελφούς. Ἴ. βλέπομεν ἱερά. "
        "8. γινώσκουσι νόμον. 9. λέγει λόγον. 10. ἔχεις δῶρα. 1]. λύω δούλους. 12. γράφει νόμον. "
        "18. διδάσκει ἄνθρωπον.")


class GreekNumberingTests(unittest.TestCase):
    def tearDown(self):
        script.apply({})

    def test_greek_lookalike_numbers_split_items(self):
        script.apply({"script": "greek"})
        items = detect.split_numbered(TEXT, tolerant=True)
        self.assertEqual([n for n, _ in items], [str(i) for i in range(1, 14)])
        self.assertEqual(items[2][1], "ἀπόστολοι λύουσι δούλους.")
        self.assertEqual(items[12][1], "διδάσκει ἄνθρωπον.")

    def test_hebrew_mode_is_unchanged(self):
        script.apply({})
        items = detect.split_numbered(TEXT, tolerant=True)
        self.assertNotIn("3", [n for n, _ in items])
        self.assertFalse(detect.NUM_LOOKALIKES)
        self.assertTrue(detect.SCRIPT_RTL)

    def test_greek_words_are_not_numbers(self):
        script.apply({"script": "greek"})
        self.assertEqual(detect.lookalike_values("δῶρα."), [])
        self.assertEqual(detect.lookalike_values("ὃ."), [3, 5])


if __name__ == "__main__":
    unittest.main()
