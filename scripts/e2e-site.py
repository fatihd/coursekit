#!/usr/bin/env python3
"""scripts/e2e-site.py — browser test of the hosted static site (ROADMAP P10-T8).

Builds the site with `scripts/build-site` into a temp dir and serves it under
`/coursekit/` (the GitHub Pages project path), or tests a live site with `--url`.
Checks: the landing page lists every course in `site/site.json`; each link opens that
course's roadmap with the right unit count; the first course's unit 1 drill completes;
Export progress downloads a file that Import restores in a fresh browser; and progress
stays separate per course.

Usage:
    python scripts/e2e-site.py [--port 8160]
    python scripts/e2e-site.py --url https://fatihd.github.io/coursekit/
"""

import argparse
import functools
import http.server
import json
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import e2e as hub_e2e  # noqa: E402


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def run_checks(base_url, cfg, work, failures):
    from playwright.sync_api import sync_playwright

    courses = [c["id"] for c in cfg["courses"]]
    first = courses[0]
    vocab_dir = work / "vocab" / first
    vocab_dir.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{base_url}{first}/vocab.json", timeout=30) as r:
        (vocab_dir / "vocab.json").write_bytes(r.read())
    authored = {}
    manifest = fetch_json(f"{base_url}{first}/course.json")
    for u in manifest["units"][:1]:
        try:
            data = fetch_json(f"{base_url}{first}/authored/{u['n']:02d}.json")
            authored[data.get("unit")] = data.get("items", [])
        except Exception:
            pass
    vocab = hub_e2e.load_vocab(str(vocab_dir))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        links = page.eval_on_selector_all("a.course", "els => els.map(e => e.getAttribute('href'))")
        print(f"landing links: {links}")
        for cid in courses:
            if f"{cid}/app/index.html" not in links:
                failures.append(f"landing page has no link to {cid}")

        for cid in courses:
            page.goto(base_url)
            page.click(f"a.course[href='{cid}/app/index.html']")
            page.wait_for_selector(".roadmap")
            want = len(fetch_json(f"{base_url}{cid}/course.json")["units"])
            got = len(page.query_selector_all(".unit"))
            print(f"{cid}: roadmap shows {got} of {want} units")
            if got != want:
                failures.append(f"{cid}: roadmap shows {got} units, expected {want}")

        page.goto(f"{base_url}{first}/")
        page.wait_for_selector(".roadmap")
        qcount, result = hub_e2e.run_drill(page, vocab, 1, authored)
        print(f"{first} unit 1 drill: {qcount} questions, {result}")
        if "unit--done" not in (page.get_attribute(".unit[data-unit='1']", "class") or ""):
            failures.append(f"{first}: unit 1 not done after the drill")

        for cid in courses[1:]:
            page.goto(f"{base_url}{cid}/app/index.html")
            page.wait_for_selector(".roadmap")
            if "unit--done" in (page.get_attribute(".unit[data-unit='1']", "class") or ""):
                failures.append(f"{cid}: shows {first}'s progress (progress not separate per course)")

        page.goto(f"{base_url}{first}/app/index.html")
        page.wait_for_selector(".roadmap")
        with page.expect_download() as dl:
            page.click("button:has-text('Export progress')")
        export_path = work / "progress-export.json"
        dl.value.save_as(export_path)
        browser.close()

        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"{base_url}{first}/app/index.html")
        page.wait_for_selector(".roadmap")
        page.set_input_files(".sync input[type=file]", str(export_path))
        page.wait_for_timeout(500)
        status = page.text_content(".sync-status").strip()
        print(f"import status: {status}")
        if "unit--done" not in (page.get_attribute(".unit[data-unit='1']", "class") or ""):
            failures.append(f"import did not restore unit 1 (status {status!r})")

        page.goto(f"{base_url}no-such-page")
        if "Not found" not in (page.text_content("body") or "") and base_url.startswith("https://"):
            failures.append("404 page not served")
        browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="test a deployed site (base URL ending in /)")
    ap.add_argument("--port", type=int, default=8160)
    args = ap.parse_args()

    cfg = json.loads((ROOT / "site" / "site.json").read_text(encoding="utf-8"))
    work = Path(tempfile.mkdtemp(prefix="e2e-site-"))
    failures = []
    server = None
    try:
        if args.url:
            base_url = args.url if args.url.endswith("/") else args.url + "/"
        else:
            serve_root = work / "www"
            r = subprocess.run(
                [sys.executable, "scripts/build-site", "--out", str(serve_root / "coursekit")],
                cwd=ROOT, capture_output=True, text=True,
            )
            if r.returncode != 0:
                sys.stderr.write(r.stdout + r.stderr)
                sys.exit("build-site failed")
            handler = functools.partial(QuietHandler, directory=str(serve_root))
            socketserver.TCPServer.allow_reuse_address = True
            server = socketserver.TCPServer(("127.0.0.1", args.port), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base_url = f"http://127.0.0.1:{args.port}/coursekit/"
        run_checks(base_url, cfg, work, failures)
    finally:
        if server:
            server.shutdown()
            server.server_close()
        shutil.rmtree(work, ignore_errors=True)

    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print(f"E2E-SITE PASS — landing page, {len(cfg['courses'])} courses, drill, export/import, "
          f"per-course progress ({base_url})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
