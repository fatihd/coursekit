#!/usr/bin/env python3
"""scripts/e2e-fork.py — end-to-end fork flow regression test.

release-course -> push to a bare "GitHub" remote -> clone the "fork" -> run the
clone's OWN vendored engine (no hub dependency) -> complete a drill -> click
"Export progress" -> import the file into a fresh browser -> unit 1 is done again.

This is the full P4-T5 acceptance. Requires Playwright (like scripts/e2e.py).

Usage:
    python scripts/e2e-fork.py biblical-hebrew-davidson [--port 8150]
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2e as hub_e2e  # noqa: E402


def sh(cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("course", help="course name, e.g. biblical-hebrew-davidson")
    ap.add_argument("--port", type=int, default=8150)
    args = ap.parse_args()

    base = Path(tempfile.mkdtemp(prefix="forkflow-"))
    remote = base / "remote.git"
    released = base / "released"
    fork = base / "fork"
    failures = []

    try:
        sh([sys.executable, "scripts/release-course", args.course, "--out", str(released)])

        for author_only in ("exercises", "answer-key", "source", "build"):
            if (released / author_only).exists():
                failures.append(f"author-only {author_only}/ leaked into student release")
        if list((released / "units").glob("*.summary.md")):
            failures.append("author-only workbook summaries leaked into student release")
        if (released / "units.json").exists():
            failures.append("author-side units.json leaked into student release")
        released_course = json.loads((released / "course.json").read_text(encoding="utf-8"))
        oer_ui = released_course.get("id") == "biblical-hebrew-oer"
        if any("textbookPage" in unit for unit in released_course.get("units", [])):
            failures.append("textbook page references leaked into student course.json")
        attribution = released / "content" / "ATTRIBUTION.md"
        attribution_text = attribution.read_text(encoding="utf-8") if attribution.is_file() else ""
        if "CC BY-SA 3.0" not in attribution_text:
            failures.append("lesson attribution/license notice missing from student release")

        remote.mkdir()
        sh(["git", "init", "--bare"], cwd=remote)
        sh(["git", "config", "user.name", "Test"], cwd=released)
        sh(["git", "config", "user.email", "test@example.com"], cwd=released)
        sh(["git", "remote", "add", "origin", str(remote)], cwd=released)
        sh(["git", "add", "."], cwd=released)
        sh(["git", "commit", "-m", "initial"], cwd=released)
        sh(["git", "push", "-u", "origin", "main"], cwd=released)

        sh(["git", "clone", str(remote), str(fork)])
        sh(["git", "config", "user.name", "Test"], cwd=fork)
        sh(["git", "config", "user.email", "test@example.com"], cwd=fork)

        proc = subprocess.Popen(
            [sys.executable, str(fork / "scripts" / "run"), ".", "--no-browser", f"--port={args.port}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(fork),
        )
        try:
            url = f"http://127.0.0.1:{args.port}/app/index.html"
            for _ in range(50):
                try:
                    urllib.request.urlopen(url, timeout=1)
                    break
                except Exception:
                    time.sleep(0.2)

            vocab = hub_e2e.load_vocab(str(fork))
            authored = hub_e2e.load_authored(str(fork))
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url)
                page.wait_for_selector(".roadmap")

                units_shown = len(page.query_selector_all(".unit"))
                expected_units = len(json.loads((fork / "course.json").read_text(encoding="utf-8"))["units"])
                print(f"fork roadmap units: {units_shown}")
                if units_shown != expected_units:
                    failures.append(f"expected {expected_units} units, got {units_shown}")

                page.click(".unit[data-unit='1']")
                page.wait_for_selector(".lesson-title")
                page.click(".gate .gate-btn")
                page.wait_for_selector(".drill-stage")
                qcount = 0
                while not page.query_selector(".drill-result"):
                    qcount += 1
                    hub_e2e.answer_current(page, vocab, 1, authored)
                    if oer_ui and page.query_selector(".ex--mcq"):
                        selected = page.locator(".ex-option--selected")
                        if selected.count() != 1:
                            failures.append("MCQ answer selection is not visually marked")
                        else:
                            selected_bg = selected.evaluate("el => getComputedStyle(el).backgroundColor")
                            if selected_bg in ("rgba(0, 0, 0, 0)", "rgb(255, 255, 255)"):
                                failures.append("selected MCQ option has no distinct background")

                    is_typing = page.query_selector(".ex--translate .ex-text, .ex--dictation .hebrew-input")
                    before_box = None
                    if oer_ui:
                        before_box = page.locator(".drill-feedback .gate-btn").bounding_box()
                    if oer_ui and is_typing:
                        if page.query_selector(".ex--dictation"):
                            keyboard = page.locator(".keyboard")
                            bounds = keyboard.bounding_box()
                            viewport_width = page.viewport_size["width"]
                            if not bounds or abs((bounds["x"] + bounds["width"] / 2) - viewport_width / 2) > 3:
                                failures.append("on-screen keyboard is not centered")
                            row_alignment = keyboard.locator(".kb-row").first.evaluate(
                                "el => getComputedStyle(el).justifyContent",
                            )
                            if row_alignment != "center":
                                failures.append("on-screen keyboard row is not centered")
                        page.keyboard.press("Enter")
                    else:
                        page.click(".drill-feedback .gate-btn")
                    page.wait_for_selector(".drill-feedback .drill-ok, .drill-feedback .drill-no, .drill-retry")
                    if page.query_selector(".drill-retry"):
                        page.click(".drill-giveup")
                        page.wait_for_selector(".drill-feedback .drill-ok, .drill-feedback .drill-no")
                    page.wait_for_selector(".drill-feedback .gate-btn")
                    if oer_ui and before_box:
                        after_box = page.locator(".drill-feedback .gate-btn").bounding_box()
                        if after_box and abs(
                            (before_box["x"] + before_box["width"])
                            - (after_box["x"] + after_box["width"])
                        ) > 3:
                            failures.append("feedback shifted the action button horizontally")
                    page.click(".drill-feedback .gate-btn")
                    page.wait_for_selector(".drill-stage, .drill-result")
                result = page.text_content(".drill-result").strip()
                print(f"fork unit 1 drill: {qcount} questions, {result}")
                page.click(".gate-btn")
                page.wait_for_selector(".roadmap")

                with page.expect_download() as dl:
                    page.click("button:has-text('Export progress')")
                export_path = base / "progress-export.json"
                dl.value.save_as(export_path)
                browser.close()

                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url)
                page.wait_for_selector(".roadmap")
                page.set_input_files(".sync input[type=file]", str(export_path))
                page.wait_for_timeout(500)
                classes = page.get_attribute(".unit[data-unit='1']", "class") or ""
                status = page.text_content(".sync-status").strip()
                print(f"import status: {status}")
                if "unit--done" not in classes:
                    failures.append(f"import did not restore unit 1 (status {status!r})")
                browser.close()
        finally:
            proc.terminate()
            proc.wait()

    finally:
        shutil.rmtree(base, ignore_errors=True)

    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("E2E-FORK PASS — release -> clone -> drill -> export -> import in a fresh browser")
    return 0


if __name__ == "__main__":
    sys.exit(main())
