import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))

import greek_text as G  # noqa: E402

spec = importlib.util.spec_from_file_location("e2e_greek", ROOT / "scripts" / "e2e-greek.py")
E2E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E2E)

OPTION_NAMES = {"movableNu": "movable_nu", "elision": "elision", "clitics": "clitics"}


class EngineParityTests(unittest.TestCase):
    def test_same_cases_as_the_engine(self):
        for fn, args, want, msg in E2E.UNIT_CASES:
            with self.subTest(msg=msg):
                if fn == "composeGreek":
                    self.assertEqual(G.compose(args[0]), want)
                elif fn == "hasAccents":
                    self.assertEqual(G.has_accents(args[0]), want)
                elif fn == "wordOrderOk":
                    self.assertEqual(G.order_ok(args[0]), want)
                elif fn == "sameWordsAnyOrder":
                    level = args[2] if len(args) > 2 else "full"
                    self.assertEqual(G.same_any_order(args[0], args[1], level), want)
                elif fn == "sameGreek":
                    level = args[2] if len(args) > 2 else "full"
                    opts = {OPTION_NAMES[k]: v for k, v in (args[3] if len(args) > 3 else {}).items()}
                    self.assertEqual(G.key(args[0], level, **opts) == G.key(args[1], level, **opts), want)


class GreekWordTests(unittest.TestCase):
    def test_words_and_bare(self):
        self.assertEqual(G.greek_words("1. ὁ λόγος, καὶ (the word)."), ["ὁ", "λόγος", "καὶ"])
        self.assertEqual(G.bare("Ἰησοῦς"), "ιησουσ")


if __name__ == "__main__":
    unittest.main()
