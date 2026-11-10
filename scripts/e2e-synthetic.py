#!/usr/bin/env python3
"""scripts/e2e-synthetic.py — generic-engine acceptance test on a synthetic course.

Builds a tiny two-unit, non-Hebrew course in a temp dir, validates it, serves it with
the engine, and drives the browser: roadmap → keyboard navigation → lesson → drill →
unlock → authored item → progress export → import into a fresh browser (and merge).

This proves the engine is course-agnostic (no Hebrew-specific assumptions) and that
progress moves between browsers via Export/Import (ADR-019).

Usage:
    python scripts/e2e-synthetic.py [--port 8155]
"""

import argparse
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

COURSE_ID = "synthetic-test-a"

VOCAB = [
    {"id": "sy-a-01-001", "unit": 1, "category": "noun", "scriptForm": "bikka",
     "transliteration": "BIKKA", "gloss": "book"},
    {"id": "sy-a-01-002", "unit": 1, "category": "noun", "scriptForm": "mara",
     "transliteration": "MARA", "gloss": "water"},
    {"id": "sy-a-01-003", "unit": 1, "category": "noun", "scriptForm": "dumma",
     "transliteration": "DUMMA", "gloss": "stone"},
    {"id": "sy-a-01-004", "unit": 1, "category": "noun", "scriptForm": "kara",
     "transliteration": "KARA", "gloss": "bread"},
    {"id": "sy-a-02-001", "unit": 2, "category": "verb", "scriptForm": "katal",
     "transliteration": "KATAL", "gloss": "he wrote"},
    {"id": "sy-a-02-002", "unit": 2, "category": "verb", "scriptForm": "saraf",
     "transliteration": "SARAF", "gloss": "he burned"},
    {"id": "sy-a-02-003", "unit": 2, "category": "verb", "scriptForm": "lamad",
     "transliteration": "LAMAD", "gloss": "he learned"},
]

COURSE = {
    "id": COURSE_ID,
    "title": "Synthetic Test Course",
    "language": "xx",
    "level": "A",
    "script": {"direction": "ltr", "font": "sans", "fontFile": "fonts/sans.woff2",
               "keyboard": "none", "translitScheme": "none"},
    "units": [
        {"id": "u01", "n": 1, "title": "Nouns", "part": 1, "textbookPage": 1},
        {"id": "u02", "n": 2, "title": "Verbs", "part": 1, "textbookPage": 2},
    ],
    "parts": [{"n": 1, "title": "Basics", "units": [1, 2]}],
    "prerequisites": [],
    "knowledgeGraph": "prerequisites/knowledge.json",
}

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Synthetic</title>
  <link rel="stylesheet" href="../app/styles.css">
</head>
<body data-course-base="../">
  <div id="app"></div>
  <script type="module" src="../engine/main.js"></script>
</body>
</html>
"""

STYLES_CSS = ":root{--bg:#faf7f2;--ink:#2b2620;--muted:#8a8377;--accent:#b4552d;--done:#3f7d4e;--available:#2d6a9f;--locked:#c9c2b6;--card:#fff}*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:var(--bg);color:var(--ink)}#app{max-width:900px;margin:0 auto;padding:2rem 1.25rem}.unit{display:flex;align-items:center;gap:.75rem;background:var(--card);border:1px solid #e6e0d6;border-radius:8px;padding:.6rem .75rem;font:inherit;color:inherit;text-align:left}.roadmap{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.6rem}.unit-n{width:2rem;height:2rem;border-radius:50%;display:grid;place-items:center;font-weight:700;background:var(--locked);color:#fff}.unit--done .unit-n{background:var(--done)}.unit--available .unit-n{background:var(--available)}.unit--available{border-color:var(--available)}.unit--locked{opacity:.55}.lesson-title{margin:0 0 .25rem;font-size:1.6rem}.gate-btn{background:var(--accent);color:#fff;border:none;border-radius:8px;padding:.7rem 1.2rem;cursor:pointer}.ex-option{display:block;width:100%;text-align:left;margin:.2rem 0;padding:.5rem .8rem;border:1px solid #e6e0d6;border-radius:8px;background:var(--card);cursor:pointer}.ex-option--selected{border-color:var(--available)}.ex-select{min-width:10rem}.drill-result{font-size:1.4rem}.keyboard{display:none}"

LESSON_1 = {
    "schema": "unit-lesson-v1.json",
    "unit": 1,
    "title": "Nouns",
    "description": "Four common nouns.",
    "teaches": ["sy-a-01-001", "sy-a-01-002", "sy-a-01-003", "sy-a-01-004"],
    "assumes": [],
    "blocks": [
        {"type": "prose", "html": "<p>This unit teaches four common nouns.</p>"},
        {"type": "vocab", "refs": ["sy-a-01-001", "sy-a-01-002", "sy-a-01-003", "sy-a-01-004"]},
    ],
}

LESSON_2 = {
    "schema": "unit-lesson-v1.json",
    "unit": 2,
    "title": "Verbs",
    "description": "Three verbs.",
    "teaches": ["sy-a-02-001", "sy-a-02-002", "sy-a-02-003"],
    "assumes": ["sy-a-01-001", "sy-a-01-002", "sy-a-01-003", "sy-a-01-004"],
    "blocks": [
        {"type": "prose", "html": "<p>This unit teaches three verbs.</p>"},
        {"type": "vocab", "refs": ["sy-a-02-001", "sy-a-02-002", "sy-a-02-003"]},
    ],
}

AUTHORED_1 = {
    "schema": "authored-exercises-v1.json",
    "unit": 1,
    "items": [
        {"type": "mcq", "stimulus": "bikka", "stimulusIsScript": False,
         "options": ["book", "water", "stone", "bread"], "answer": "book", "optionIsScript": False},
    ],
}


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def build_course(root):
    course = root / COURSE_ID
    write(course / "course.json", COURSE)
    write(course / "vocab.json", {"schema": "vocab-v1.json", "items": VOCAB})
    write(course / "units/01.json", LESSON_1)
    write(course / "units/02.json", LESSON_2)
    write(course / "authored/01.json", AUTHORED_1)
    write(course / "prerequisites/knowledge.json", {"schema": "knowledge-v1.json", "items": []})
    (course / "app").mkdir(parents=True, exist_ok=True)
    (course / "app/index.html").write_text(INDEX_HTML, encoding="utf-8")
    (course / "app/styles.css").write_text(STYLES_CSS, encoding="utf-8")
    return course


def load_vocab(course):
    items = json.loads((course / "vocab.json").read_text(encoding="utf-8"))["items"]
    by_unit = {}
    script = {}
    gloss = {}
    translit = {}
    for x in items:
        by_unit.setdefault(x["unit"], {})[x["scriptForm"]] = x
        script.setdefault(x["scriptForm"], x)
        gloss.setdefault(x["gloss"], x)
        translit.setdefault(x["transliteration"], x)
    return {"by_unit": by_unit, "script": script, "gloss": gloss, "translit": translit}


def answer(page, vocab, unit_n):
    unit_map = vocab["by_unit"].get(unit_n, {})
    script = vocab["script"]
    gloss = vocab["gloss"]
    translit = vocab["translit"]

    if page.query_selector(".ex--mcq"):
        stim = page.text_content(".ex--mcq .ex-stimulus").strip()
        if stim in script:
            correct = script[stim]["gloss"]
        else:
            it = gloss.get(stim) or translit.get(stim)
            if it is None:
                raise RuntimeError(f"mcq stimulus not found: {stim!r}")
            correct = it["scriptForm"]
        for opt in page.query_selector_all(".ex--mcq .ex-option"):
            if opt.get_attribute("data-value") == correct:
                opt.click()
                return
        raise RuntimeError(f"mcq option not found: correct={correct!r} stim={stim!r}")

    if page.query_selector(".ex--match"):
        for row in page.query_selector_all(".ex-match-row"):
            word = row.query_selector(".script").text_content().strip()
            row.query_selector("select").select_option(value=unit_map[word]["gloss"])
        return

    if page.query_selector(".ex--categorize"):
        for row in page.query_selector_all(".ex-cat-row"):
            word = row.query_selector(".script").text_content().strip()
            row.query_selector("select").select_option(value=unit_map[word]["category"])
        return

    if page.query_selector(".ex--translate"):
        stim = page.text_content(".ex--translate .ex-stimulus").strip()
        page.fill(".ex--translate .ex-text", script[stim]["gloss"])
        return

    if page.query_selector(".ex--dictation"):
        stim = page.text_content(".ex--dictation .ex-stimulus").strip()
        page.fill(".ex--dictation .hebrew-input", gloss[stim]["scriptForm"])
        return

    raise RuntimeError("unknown question type")


def start_server(course, port):
    proc = subprocess.Popen(
        [sys.executable, "scripts/run", str(course), "--no-browser", f"--port={port}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}/app/index.html"
    for _ in range(50):
        try:
            urllib.request.urlopen(url, timeout=1)
            return proc, url
        except Exception:
            time.sleep(0.2)
    proc.terminate()
    raise RuntimeError("server did not start")


def check(cond, msg, failures):
    print(f"  {'PASS' if cond else 'FAIL'}: {msg}")
    if not cond:
        failures.append(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8155)
    args = ap.parse_args()

    base = Path(tempfile.mkdtemp(prefix="synthetic-course-"))
    course = build_course(base)
    failures = []

    try:
        validation = subprocess.run([sys.executable, "scripts/validate", str(course)],
                                    capture_output=True, text=True)
        check(validation.returncode == 0, "synthetic course validates clean", failures)
        if validation.returncode != 0:
            print(validation.stdout)
            print(validation.stderr)

        vocab = load_vocab(course)
        proc, url = start_server(course, args.port)

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url)
                page.wait_for_selector(".roadmap")

                units = page.query_selector_all(".unit")
                check(len(units) == 2, f"roadmap shows 2 units (got {len(units)})", failures)

                check("unit--available" in (page.get_attribute(".unit[data-unit='1']", "class") or ""), "unit 1 available", failures)
                check("unit--locked" in (page.get_attribute(".unit[data-unit='2']", "class") or ""), "unit 2 locked", failures)

                # Keyboard-only navigation: focus unit 1 and press Enter.
                page.focus(".unit[data-unit='1']")
                page.keyboard.press("Enter")
                page.wait_for_selector(".lesson-title")
                check(page.text_content(".lesson-title").strip().startswith("Unit 1"), "keyboard Enter opens unit 1 lesson", failures)

                page.click(".gate-btn")
                page.wait_for_selector(".drill-stage")

                # First question must be the authored item.
                first_stim = page.text_content(".ex-stimulus").strip()
                check(first_stim == "bikka", f"first drill question is the authored item (got {first_stim!r})", failures)

                qcount = 0
                while not page.query_selector(".drill-result"):
                    qcount += 1
                    answer(page, vocab, 1)
                    page.click(".drill-feedback .gate-btn")
                    page.wait_for_selector(".drill-feedback .gate-btn")
                    page.click(".drill-feedback .gate-btn")
                    page.wait_for_selector(".drill-stage, .drill-result")

                result = page.text_content(".drill-result").strip()
                print(f"  synthetic unit 1 drill: {qcount} questions, {result}")
                check("100%" in result, f"unit 1 drill passed (got {result!r})", failures)

                page.click(".gate-btn")
                page.wait_for_selector(".roadmap")
                check("unit--done" in (page.get_attribute(".unit[data-unit='1']", "class") or ""), "unit 1 done", failures)
                check("unit--available" in (page.get_attribute(".unit[data-unit='2']", "class") or ""), "unit 2 unlocked", failures)

                # Export progress → download a JSON file.
                with page.expect_download() as dl:
                    page.click("button:has-text('Export progress')")
                export_path = base / "export.json"
                dl.value.save_as(export_path)
                exported = json.loads(export_path.read_text(encoding="utf-8"))
                check(exported.get("units", {}).get("1", {}).get("state") == "done", "export contains unit 1 done", failures)
                check(bool(exported.get("lastExportedAt")), "export records lastExportedAt", failures)
                browser.close()

                # Fresh browser (empty localStorage): nothing done until the file is imported.
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url)
                page.wait_for_selector(".roadmap")
                check("unit--done" not in (page.get_attribute(".unit[data-unit='1']", "class") or ""), "fresh browser starts empty", failures)
                page.set_input_files(".sync input[type=file]", str(export_path))
                page.wait_for_selector(".unit--done")
                check("unit--done" in (page.get_attribute(".unit[data-unit='1']", "class") or ""), "import restores unit 1 done", failures)
                check("unit--available" in (page.get_attribute(".unit[data-unit='2']", "class") or ""), "import restores currentUnit 2", failures)

                # Merge: a second export with only unit 2 done keeps unit 1 too.
                other = dict(exported, units={"2": {"state": "done", "lessonRead": True, "bestScore": 90}}, currentUnit=3)
                page.set_input_files(".sync input[type=file]", files=[{"name": "other.json", "mimeType": "application/json",
                                                                        "buffer": json.dumps(other).encode("utf-8")}])
                page.wait_for_selector(".unit[data-unit='2'].unit--done")
                check("unit--done" in (page.get_attribute(".unit[data-unit='1']", "class") or ""), "merge keeps unit 1 done", failures)
                check("unit--done" in (page.get_attribute(".unit[data-unit='2']", "class") or ""), "merge adds unit 2 done", failures)

                # Wrong course file → clear error, nothing changes.
                wrong = dict(exported, courseId="some-other-course")
                page.set_input_files(".sync input[type=file]", files=[{"name": "w.json", "mimeType": "application/json",
                                                                        "buffer": json.dumps(wrong).encode("utf-8")}])
                page.wait_for_timeout(300)
                check("another course" in page.text_content(".sync-status"), "import of another course's file is rejected", failures)
                browser.close()

        except ImportError:
            print("playwright not installed — run: .venv/bin/pip install playwright && "
                  ".venv/bin/python -m playwright install chromium")
            sys.exit(2)
        finally:
            proc.terminate()
            proc.wait()

    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("E2E-SYNTHETIC PASS — generic 2-unit course: launch, keyboard nav, drill, unlock, authored, progress export/import + merge")
    return 0


if __name__ == "__main__":
    sys.exit(main())
