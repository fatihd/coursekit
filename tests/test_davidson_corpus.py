"""Corpus expansion for Davidson (ROADMAP P12-T5): new sentences and Bible verses.

Every new sentence sits in the first unit whose words and grammar it needs, and every Hebrew word
form in it is attested (Hebrew Bible, Davidson's exercises or the course word list).
"""

import json
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path("build").resolve()))
import davidson_corpus as dc  # noqa: E402

COURSE = Path("courses/biblical-hebrew-davidson")
CACHED = dc.OSHB.is_dir() and dc.WEB.is_file()


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(dc.CORPUS.read_text(encoding="utf-8"))["sentences"]
        cls.forms = json.loads(dc.FORMS.read_text(encoding="utf-8"))["forms"]
        cls.bible = json.loads(dc.BIBLE.read_text(encoding="utf-8"))["verses"]

    def test_sentences_sit_in_the_first_unit_that_teaches_them(self):
        for s in self.corpus:
            unit, problems = dc.sentence_unit(s["hebrew"][0], self.forms, s.get("tags", []), s.get("plain"))
            with self.subTest(sentence=s["id"]):
                self.assertEqual(problems, [])
                self.assertEqual(unit, s["unit"])
                for alt in s["hebrew"][1:]:
                    u2, p2 = dc.sentence_unit(alt, self.forms, s.get("tags", []), s.get("plain"))
                    self.assertEqual(p2, [])
                    self.assertLessEqual(u2, s["unit"])

    def test_every_word_is_attested(self):
        for s in self.corpus:
            for h in s["hebrew"]:
                for w in dc.words_of(h):
                    with self.subTest(sentence=s["id"], word=w):
                        self.assertTrue(self.forms[w]["attested"])

    def test_ids_and_shapes(self):
        ids = [s["id"] for s in self.corpus]
        self.assertEqual(len(ids), len(set(ids)))
        for s in self.corpus:
            with self.subTest(sentence=s["id"]):
                self.assertTrue(s["id"].startswith(f"c{s['unit']:02d}-"))
                self.assertIn(s["direction"], ("he-en", "en-he"))
                self.assertTrue(s["english"][:1].isupper())
                self.assertEqual(len(s["hebrew"]), len(set(s["hebrew"])))
        self.assertEqual(len({dc.norm(s["hebrew"][0]) for s in self.corpus}), len(self.corpus))

    def test_bible_verses_have_text_translation_and_place(self):
        floor = dc.grammar()["floor"]
        refs = [v["ref"] for v in self.bible]
        self.assertEqual(len(refs), len(set(refs)))
        for v in self.bible:
            with self.subTest(ref=v["ref"]):
                self.assertGreaterEqual(v["unit"], floor)
                self.assertTrue(dc.words_of(v["hebrew"]))
                self.assertTrue(v["english"][:1].isupper() and v["english"][-1] in ".!?")

    def test_every_new_item_is_in_the_course(self):
        units = Counter()
        for path in sorted((COURSE / "authored").glob("[0-9][0-9].json")):
            for it in json.loads(path.read_text(encoding="utf-8"))["items"]:
                if it.get("extra") and it["rung"] == 1:
                    units[it["src"]] += 1
        self.assertEqual(set(units), {s["id"] for s in self.corpus} | {"b-" + v["ref"].replace(".", "-") for v in self.bible})

    @unittest.skipUnless(CACHED, "OSHB/WEB cache missing (build/fetch_oer.py)")
    def test_forms_and_verses_are_up_to_date(self):
        for cmd in ("forms", "bible"):
            r = subprocess.run([sys.executable, "build/davidson_corpus.py", cmd, "--check"], capture_output=True, text=True)
            with self.subTest(cmd=cmd):
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class AnalysisTests(unittest.TestCase):
    def test_morphology_features(self):
        cases = {
            ("d/776", "HTd/Ncbsa"): {"article"},
            ("b/7225", "HR/Ncfsa"): {"prefix-prep"},
            ("c/1961", "HC/Vqw3ms"): {"waw", "wayyiqtol"},
            ("1697", "HNcmsc/Sp3ms"): {"construct", "suffix"},
            ("413", "HR/Sp3mp"): {"prep-suffix"},
            ("853", "HTo/Sp3ms"): {"object-marker", "prep-suffix"},
            ("8104", "HVNp3ms"): {"niphal"},
            ("8104", "HVqp1cs"): {"qatal"},
        }
        for (lemma, morph), feats in cases.items():
            with self.subTest(morph=morph):
                self.assertTrue(feats <= set(dc.analyse(lemma, morph)["features"]))

    def test_weak_verbs_only_beyond_the_dictionary_form(self):
        self.assertEqual(dc.weak_classes("נתן", True), [])
        self.assertIn("pe-nun", dc.weak_classes("נתן", False))
        self.assertIn("lamed-he", dc.weak_classes("בנה", False))
        self.assertIn("hollow", dc.weak_classes("קום", False))
        self.assertIn("pe-aleph", dc.weak_classes("אמר", False))
        self.assertEqual(dc.weak_classes("שרף", False), [])
        self.assertIn("ayin-guttural", dc.weak_classes("ברך", False, "p"))
        self.assertNotIn("hollow", dc.weak_classes("היה", False))


if __name__ == "__main__":
    unittest.main()
