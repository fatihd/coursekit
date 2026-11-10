import json
import tempfile
import unittest
from pathlib import Path

from build.materialize import read_chapter
from build.textify import write_chapter


class LessonSectionRoundTripTests(unittest.TestCase):
    def test_materialize_preserves_prose_section_captions(self):
        with tempfile.TemporaryDirectory() as temp:
            chapter = Path(temp) / "01.md"
            chapter.write_text(
                "# Unit 1 — Test\n\nDescription.\n\n"
                "## Summary\n\nSummary text.\n\n"
                "## Metheg\n\nMetheg text.\n\n"
                "## Source\n\nDavidson §10.\n",
                encoding="utf-8",
            )

            lesson = read_chapter(chapter)

        prose_captions = [b["caption"] for b in lesson["blocks"] if b["type"] == "prose"]
        self.assertEqual(prose_captions, ["Summary", "Metheg", "Source"])

    def test_textify_restores_prose_section_headings(self):
        with tempfile.TemporaryDirectory() as temp:
            course_dir = Path(temp)
            (course_dir / "units").mkdir()
            (course_dir / "content" / "chapters").mkdir(parents=True)
            lesson = {
                "title": "Test",
                "description": "Description.",
                "blocks": [
                    {"type": "prose", "caption": "Summary", "html": "<p>Summary text.</p>"},
                    {"type": "prose", "caption": "Metheg", "html": "<p>Metheg text.</p>"},
                    {"type": "prose", "caption": "Source", "html": "<p>Davidson §10.</p>"},
                ],
            }
            (course_dir / "units" / "01.json").write_text(
                json.dumps(lesson), encoding="utf-8",
            )

            write_chapter(course_dir, course_dir / "content", 1)
            chapter = (course_dir / "content" / "chapters" / "01.md").read_text(encoding="utf-8")

        self.assertIn("## Summary\n\nSummary text.", chapter)
        self.assertIn("## Metheg\n\nMetheg text.", chapter)
        self.assertIn("## Source\n\nDavidson §10.", chapter)


if __name__ == "__main__":
    unittest.main()
