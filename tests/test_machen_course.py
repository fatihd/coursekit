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

    def test_top_rung_asks_for_accents(self):
        items = json.loads((COURSE / "authored" / "04.json").read_text(encoding="utf-8"))["items"]
        top = [it for it in items if it["rung"] == 5]
        self.assertTrue(top)
        self.assertTrue(all(it["pointing"] == "required" and it["rungLabel"] == "Translate with accents" for it in top))


if __name__ == "__main__":
    unittest.main()
