import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

import davidson_ladder as L  # noqa: E402


class EnglishVariantTests(unittest.TestCase):
    def test_supplied_words_are_optional_and_notes_dropped(self):
        v = L.english_variants("Thou (fem.) hast eaten of the tree.")
        self.assertIn("Thou hast eaten of the tree.", v)
        self.assertIn("You have eaten of the tree.", v)
        self.assertNotIn("fem", " ".join(v))
        self.assertIn("The light is good.", L.english_variants("The light (is) good."))

    def test_alternative_word_in_brackets(self):
        v = L.english_variants("The blessing of Yahweh (be) upon thy children (sons).")
        self.assertTrue(any("thy sons" in x or "your sons" in x for x in v), v)

    def test_archaic_verbs_are_modernized(self):
        self.assertEqual(L.modernize("God knoweth that ye shall be as gods"), "God knows that you shall be as gods")
        self.assertEqual(L.modernize("He that sheddeth man's blood"), "He that sheds man's blood")
        self.assertEqual(L.modernize("Thou rememberest him"), "You remember him")
        self.assertEqual(L.modernize("the forest and teeth"), "the forest and teeth")


class DistractorTests(unittest.TestCase):
    def test_each_distractor_changes_one_point(self):
        kinds = {k for k, _ in L.mutations("Let me hide my face from this evil people")}
        self.assertTrue({"possessive", "demonstrative", "preposition", "object"} <= kinds, kinds)

    def test_distractors_differ_from_the_key(self):
        key = "We rested on the seventh day."
        picked = L.pick_distractors(key, random.Random(1), [])
        self.assertEqual(len(picked), 3)
        self.assertNotIn(key, picked)
        self.assertEqual(len(set(picked)), 3)

    def test_infinitive_to_is_not_swapped(self):
        self.assertFalse([c for k, c in L.mutations("He came to shed blood.") if k == "preposition"])


class PhraseDistractorTests(unittest.TestCase):
    def test_subject_change_keeps_the_verb_agreeing(self):
        cands = [c for _, c in L.mutations("I (am) a man.")]
        self.assertIn("You (are) a man.", cands)
        self.assertNotIn("We (are) a man.", cands)
        self.assertNotIn("They (am) a man.", cands)
        self.assertIn("She is a woman.", [c for _, c in L.mutations("Thou (fem.) art a woman.")])

    def test_number_and_article_change_for_bare_phrases(self):
        self.assertEqual({c for _, c in L.mutations("A good man")}, {"The good man", "(Some) good men"})
        self.assertEqual({c for _, c in L.mutations("(Some) wolves")}, {"A wolf", "(Two) wolves", "The wolves"})
        self.assertEqual({c for _, c in L.mutations("(Two) hands")}, {"A hand", "(Some) hands", "The hands"})
        self.assertEqual({c for _, c in L.mutations("(Some) bitter water")}, {"The bitter water"})


class PausalTests(unittest.TestCase):
    def test_pause_lengthens_one_vowel(self):
        self.assertTrue(L.pausal_pair("הַמָּיִם", "הַמַּיִם"))
        self.assertTrue(L.pausal_pair("בָּעָרֶב", "בָּעֶרֶב"))

    def test_other_differences_are_not_pause(self):
        self.assertFalse(L.pausal_pair("לָאִשָּׁה", "לְאִשָּׁה"))
        self.assertFalse(L.pausal_pair("דְּבָרָי", "דִּבְרֵי"))


if __name__ == "__main__":
    unittest.main()
