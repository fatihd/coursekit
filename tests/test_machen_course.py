import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COURSE = ROOT / "courses" / "biblical-greek-machen"


@unittest.skipUnless(COURSE.exists(), "course not in this tree")
class MachenCourseTests(unittest.TestCase):
    def test_course_data_is_current(self):
        r = subprocess.run([sys.executable, "build/machen_course.py", "--course", str(COURSE), "--check"],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_greek_profile_and_license(self):
        course = json.loads((COURSE / "course.json").read_text(encoding="utf-8"))
        self.assertEqual(course["script"]["profile"], "greek")
        self.assertEqual(course["script"]["keyboard"], "el_GR")
        self.assertIn("CC BY-SA 4.0", (COURSE / "content" / "ATTRIBUTION.md").read_text(encoding="utf-8"))

    def test_sentences_start_with_lesson_three(self):
        ladder = json.loads((COURSE / "authored" / "ladder.json").read_text(encoding="utf-8"))["units"]
        self.assertEqual(sorted(ladder["1"]), ["1", "2", "3"])
        for unit in range(3, 9):
            self.assertEqual(sorted(ladder[str(unit)]), ["1", "2", "3", "4", "5"], unit)

    def test_every_common_nt_lemma_is_taught(self):
        counts = json.loads((ROOT / "build/_sources/machen/lemma-counts.json").read_text(encoding="utf-8"))["counts"]
        layers = json.loads((ROOT / "build/_sources/machen/frequency-layers.json").read_text(encoding="utf-8"))
        cmap = json.loads((ROOT / "build/_sources/machen/course-map.json").read_text(encoding="utf-8"))
        machen = {w[4] if len(w) > 4 and w[4] else w[0] for u in cmap["units"] for w in u["vocab"]}
        core = {e["lemma"] for e in layers["core"]}
        missing = [lem for lem, n in counts.items() if n >= 50 and lem not in machen | core]
        self.assertEqual(missing, [])
        self.assertEqual(sum(1 for n in counts.values() if n >= 50), 309)
        last = max(u["n"] for u in cmap["units"])
        self.assertTrue(all(3 <= e["unit"] <= last and e["count"] >= 50 for e in layers["core"]))

    def test_reading_vocabulary_is_an_optional_words_only_part(self):
        course = json.loads((COURSE / "course.json").read_text(encoding="utf-8"))
        ladder = json.loads((COURSE / "authored" / "ladder.json").read_text(encoding="utf-8"))["units"]
        part = course["parts"][-1]
        self.assertIn("optional", part["title"].lower())
        reading = [u["n"] for u in course["units"] if u["part"] == part["n"]]
        self.assertTrue(reading)
        self.assertEqual(reading, list(range(part["units"][0], part["units"][1] + 1)))
        self.assertTrue(all(str(n) not in ladder for n in reading))
        self.assertGreater(min(reading), max(int(n) for n in ladder))
        words = [v for v in json.loads((COURSE / "vocab.json").read_text(encoding="utf-8"))["items"]
                 if v["unit"] in reading]
        self.assertGreater(len(words), 600)
        self.assertTrue(all(v["gloss"] and v["scriptForm"] for v in words))

    def test_top_rung_asks_for_accents(self):
        items = json.loads((COURSE / "authored" / "04.json").read_text(encoding="utf-8"))["items"]
        top = [it for it in items if it["rung"] == 5]
        self.assertTrue(top)
        self.assertTrue(all(it["pointing"] == "required" and it["rungLabel"] == "Translate with accents" for it in top))


if __name__ == "__main__":
    unittest.main()
