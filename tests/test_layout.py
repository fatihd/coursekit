import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS_IMPORT = re.compile(r"""(?:\bfrom\s*|\bimport\s*\(\s*|\bimport\s+)["']([^"']+)["']""")
EXWB_ENGINE_FILES = {"keyboard.js", "dom.js", "keyboards/he_IL.js"}


def py_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


class LayoutBoundaryTests(unittest.TestCase):
    def test_each_part_has_a_readme(self):
        for part in ("engine", "build", "exwb", "scripts"):
            self.assertTrue((ROOT / part / "README.md").is_file(), part)

    def test_engine_imports_stay_inside_engine(self):
        engine = (ROOT / "engine").resolve()
        for js in engine.rglob("*.js"):
            for spec in JS_IMPORT.findall(js.read_text(encoding="utf-8")):
                if not spec.startswith("."):
                    self.fail(f"{js.relative_to(ROOT)} imports a non-relative module {spec!r}")
                target = (js.parent / spec).resolve()
                self.assertTrue(
                    target == engine or engine in target.parents,
                    f"{js.relative_to(ROOT)} imports {spec!r} outside engine/",
                )
                self.assertTrue(target.is_file(), f"{js.relative_to(ROOT)}: missing {spec!r}")

    def test_exwb_uses_only_stdlib_and_itself(self):
        local = {p.stem for p in (ROOT / "exwb" / "exwb").glob("*.py")} | {"exwb"}
        forbidden = {"build", "scripts", "engine", "tests"}
        for py in (ROOT / "exwb" / "exwb").glob("*.py"):
            bad = py_imports(py) & forbidden
            self.assertFalse(bad, f"{py.relative_to(ROOT)} imports {bad}")
            for name in py_imports(py) - local:
                self.assertNotIn(name, {"requests", "numpy", "PIL", "pypdf"}, py.name)

    def test_exwb_reads_only_the_shared_keyboard_files_from_engine(self):
        for f in EXWB_ENGINE_FILES:
            self.assertTrue((ROOT / "engine" / f).is_file(), f)
        html = (ROOT / "exwb" / "exwb" / "static" / "index.html").read_text(encoding="utf-8")
        used = set(re.findall(r"/engine/([\w./-]+\.js)", html))
        self.assertTrue(used <= EXWB_ENGINE_FILES, f"exwb UI loads extra engine files: {used - EXWB_ENGINE_FILES}")

    def test_unread_scan_extras_are_not_tracked(self):
        import subprocess

        r = subprocess.run(["git", "ls-files", "build/_sources"], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest("not a git checkout")
        extras = re.compile(r"(_hocr|_page_numbers\.json|-djvu\.txt|\.gz$|/grammar\.txt$)")
        tracked = [f for f in r.stdout.splitlines() if extras.search(f)]
        self.assertEqual(tracked, [], "unread archive.org extras are tracked (P9-T10)")

    def test_build_and_engine_do_not_use_exwb(self):
        for py in (ROOT / "build").glob("*.py"):
            self.assertNotIn("exwb", py_imports(py), py.name)
        for js in (ROOT / "engine").rglob("*.js"):
            self.assertNotIn("exwb", js.read_text(encoding="utf-8"), js.name)


if __name__ == "__main__":
    unittest.main()
