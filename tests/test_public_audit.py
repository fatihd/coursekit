import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "public-audit"
PRIVATE_ID = "he" + "-a-" + "v0001"
TOKEN = "gh" + "p_" + "A" * 36


class PublicAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "tree"
        self.root.mkdir()
        self.allow = Path(self.tmp.name) / "allow.txt"
        self.allow.write_text(
            "LICENSE\nREADME.md\ncourses/open/\n!courses/open/private/\nrequire: LICENSE\n",
            encoding="utf-8",
        )
        self.write("LICENSE", "MIT License\n\nCopyright (c) 2026\n")
        self.write("README.md", "# Open course\n")
        self.write("courses/open/vocab.csv", "id,word\nop-1,בָּרָא\n")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text=None, data=None):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if data is not None:
            p.write_bytes(data)
        else:
            p.write_text(text, encoding="utf-8")

    def run_audit(self, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root), "--allowlist", str(self.allow), *extra],
            capture_output=True, text=True,
        )

    def assertFails(self, category, *extra):
        r = self.run_audit(*extra)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn(category, r.stdout)

    def test_clean_tree_passes(self):
        r = self.run_audit()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PUBLIC-AUDIT PASS", r.stdout)

    def test_private_id_fails(self):
        self.write("courses/open/unit.json", f'{{"id": "{PRIVATE_ID}"}}\n')
        self.assertFails("mention")

    def test_pdf_fails(self):
        self.write("courses/open/scan.pdf", data=b"%PDF-1.4\n")
        self.assertFails("type")

    def test_large_file_fails(self):
        self.write("courses/open/big.json", "x" * 2000)
        self.assertFails("size", "--max-bytes", "1000")

    def test_font_is_exempt_from_size(self):
        self.write("courses/open/font.woff2", data=b"\x00" * 2000)
        r = self.run_audit("--max-bytes", "1000")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_secret_fails(self):
        self.write("courses/open/config.js", f'const t = "{TOKEN}";\n')
        self.assertFails("secret")

    def test_path_outside_allowlist_fails(self):
        self.write("notes/todo.md", "x\n")
        self.assertFails("not in allowlist")

    def test_denied_path_fails(self):
        self.write("courses/open/private/a.md", "x\n")
        self.assertFails("denied by allowlist")

    def test_fingerprint_fails(self):
        private = Path(self.tmp.name) / "private"
        private.mkdir()
        line = "A sentence that only the private course contains, long enough."
        (private / "lesson.md").write_text(line + "\n", encoding="utf-8")
        fp = Path(self.tmp.name) / "fp.txt"
        subprocess.run(
            [sys.executable, str(SCRIPT), "--make-fingerprints", str(fp), "--private", str(private)],
            check=True, capture_output=True,
        )
        self.write("courses/open/lesson.md", "  " + line.upper() + "\n")
        self.assertFails("fingerprint", "--fingerprints", str(fp))

    def test_open_lines_are_not_fingerprinted(self):
        private, opened = Path(self.tmp.name) / "private", Path(self.tmp.name) / "open"
        private.mkdir()
        opened.mkdir()
        shared = "In the beginning God created the heavens and the earth."
        (private / "a.md").write_text(shared + "\n", encoding="utf-8")
        (opened / "b.md").write_text(shared + "\n", encoding="utf-8")
        fp = Path(self.tmp.name) / "fp.txt"
        subprocess.run(
            [sys.executable, str(SCRIPT), "--make-fingerprints", str(fp),
             "--private", str(private), "--open", str(opened)],
            check=True, capture_output=True,
        )
        self.write("courses/open/lesson.md", shared + "\n")
        r = self.run_audit("--fingerprints", str(fp))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_missing_or_wrong_license_fails(self):
        (self.root / "LICENSE").write_text("Apache License 2.0\n", encoding="utf-8")
        self.assertFails("not the MIT License")
        (self.root / "LICENSE").unlink()
        self.assertFails("required file missing")


    def test_private_block_is_skipped_and_public_block_scanned(self):
        self.write(
            "README.md",
            f"# Open\n<!-- private -->\n{PRIVATE_ID}\n<!-- /private -->\n<!-- public\nfine\n-->\n",
        )
        r = self.run_audit()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.write("README.md", f"# Open\n<!-- public\n{PRIVATE_ID}\n-->\n")
        self.assertFails("mention")

    def test_unbalanced_marker_fails(self):
        self.write("README.md", "# Open\n<!-- private -->\nsecret plan\n")
        self.assertFails("unclosed private block")

    def test_secret_in_private_block_still_fails(self):
        self.write("README.md", f"<!-- private -->\n{TOKEN}\n<!-- /private -->\n")
        self.assertFails("secret")


if __name__ == "__main__":
    unittest.main()
