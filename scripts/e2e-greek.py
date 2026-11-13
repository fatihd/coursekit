#!/usr/bin/env python3
"""scripts/e2e-greek.py — Greek script support check (ROADMAP P11-T2 groundwork).

Serves the hub `engine/` with a one-page harness and drives it headlessly:
  * `engine/greek.js`: polytonic composition (mark order, NFC, final sigma), grading keys at three
    strictness levels (letters / breathings / full accents), punctuation and movable-nu tolerance,
    and the per-letter accent diff;
  * `engine/keyboard.js` with the `el_GR` layout: typing ἄνθρωπος and ᾠδῇ with the on-screen keys;
  * the `translate-phrase` grader under the Greek script profile (`engine/script.js`): a typed rung grades
    letters + breathings + iota subscript, the top rung full accents; the Hebrew profile is unchanged.

No course is needed and no progress is touched.

Usage:
    python scripts/e2e-greek.py [--port 8157]
"""

import argparse
import http.server
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HARNESS = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Greek harness</title></head>
<body>
<input class="ex-text hebrew-input" id="answer" type="text" lang="grc">
<script type="module">
import * as greek from "/engine/greek.js";
import { initKeyboard } from "/engine/keyboard.js";
import { setScript } from "/engine/script.js";
import translatePhrase from "/engine/exercise-types/translate-phrase.js";
window.greek = greek;
window.setScript = setScript;
window.tp = translatePhrase;
await initKeyboard(document.body, "el_GR");
window.ready = true;
</script>
</body></html>
"""

UNIT_CASES = [
    ("composeGreek", ["ά̓νθρωπος"], "ἄνθρωπος", "breathing and accent typed in either order compose to ἄ"),
    ("composeGreek", ["ᾣ"], "ᾣ", "iota subscript, rough breathing and grave compose to one letter"),
    ("composeGreek", ["λογοσ και"], "λογος και", "word-final σ becomes ς"),
    ("composeGreek", ["ςα"], "σα", "ς inside a word becomes σ"),
    ("composeGreek", ["ά"], "ά", "oxia and tonos are the same letter after NFC"),
    ("sameGreek", ["λογος", "λόγος", "letters"], True, "letters mode: λογος = λόγος"),
    ("sameGreek", ["λογος", "λόγος", "full"], False, "full mode: λογος ≠ λόγος"),
    ("sameGreek", ["λογός", "λόγος", "full"], False, "full mode: wrong accent position is wrong"),
    ("sameGreek", ["ανθρωπος", "ἄνθρωπος", "breathings"], False, "breathings mode: a missing breathing is wrong"),
    ("sameGreek", ["ἀνθρωπος", "ἄνθρωπος", "breathings"], True, "breathings mode: accents are not required"),
    ("sameGreek", ["ἀλλὰ καὶ", "ἀλλά καί", "full"], True, "grave and acute count as the same accent"),
    ("sameGreek", ["τί λέγεις;", "τί λέγεις;", "full"], True, "Greek question mark = semicolon; punctuation ignored"),
    ("sameGreek", ["ἀλλ’ οὐ", "ἀλλ᾽ οὐ", "full"], True, "elision mark variants are equal"),
    ("sameGreek", ["Ἰησοῦς", "ἰησοῦς", "full"], True, "capitals are ignored"),
    ("sameGreek", ["ἐστιν", "ἐστι", "full"], True, "movable nu is optional (ἐστι = ἐστιν)"),
    ("sameGreek", ["λέγουσιν αὐτῷ", "λέγουσι αὐτῷ", "full"], True, "movable nu is optional (-σι/-σιν)"),
    ("sameGreek", ["ἐστιν", "ἐστι", "full", {"movableNu": False}], False, "movable nu can be made strict"),
    ("sameGreek", ["ἐν", "ἐ", "full"], False, "short words keep their final nu"),
    ("sameGreek", ["οὐδέν", "οὐδέ", "full"], False, "οὐδέν is not οὐδέ"),
    ("sameGreek", ["πίστιν", "πίστι", "full"], False, "a final nu that is not movable counts"),
    ("sameGreek", ["δι’ αὐτοῦ", "διὰ αὐτοῦ", "full"], True, "elided and full forms are equal (δι’ = διά)"),
    ("sameGreek", ["ἀλλ’ οὐ", "ἀλλὰ οὐ", "full"], True, "elided and full forms are equal (ἀλλ’ = ἀλλά)"),
    ("sameGreek", ["ἄνθρωπός τις", "ἄνθρωπος τις", "full"], True, "accent thrown back from an enclitic is not penalised"),
    ("sameGreek", ["λόγος ἐστίν", "λόγος ἐστιν", "full"], True, "an enclitic with or without its accent is accepted"),
    ("sameGreek", ["εἴ τις", "εἰ τις", "full"], True, "a proclitic with or without an accent is accepted"),
    ("sameGreek", ["ὁ λόγος", "ὅ λόγος", "full"], False, "the article ὁ and the relative ὅ stay distinct"),
    ("sameGreek", ["ἀγαπᾶν", "ἀγαπᾷν", "breathings"], False, "iota subscript is required even when accents are not"),
    ("sameGreek", ["\u1fbfΙησοῦς", "Ἰησοῦς", "full"], True, "a spacing breathing before a capital counts as its breathing"),
    ("sameWordsAnyOrder", ["βλέπει ἄνθρωπον ἀδελφός", "ἀδελφὸς βλέπει ἄνθρωπον"], True, "any order of the same words"),
    ("sameWordsAnyOrder", ["ὁ δὲ λόγος μένει", "ὁ λόγος δὲ μένει"], True, "postpositive in second place"),
    ("sameWordsAnyOrder", ["δὲ ὁ λόγος μένει", "ὁ δὲ λόγος μένει"], False, "a postpositive may not stand first"),
    ("sameWordsAnyOrder", ["λόγος μένει ὁ", "ὁ λόγος μένει"], False, "an article may not stand last"),
    ("sameWordsAnyOrder", ["βλέπει ἄνθρωπον", "ἀδελφὸς βλέπει ἄνθρωπον"], False, "the same words, not a subset"),
    ("sameWordsAnyOrder", ["ἄνθρωπον βλέπει. γάρ ἐστιν", "βλέπει ἄνθρωπον. ἐστιν γάρ"], False, "the rule holds in every clause"),
    ("wordOrderOk", ["οὐ γὰρ ἔχομεν"], True, "γάρ in second place is fine"),
    ("wordOrderOk", ["γὰρ οὐκ ἔχομεν"], False, "γάρ first is not Greek"),
    ("hasAccents", ["λογος"], False, "hasAccents false without accents"),
    ("hasAccents", ["λόγος"], True, "hasAccents true with accents"),
]


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def do_GET(self):
        if self.path.split("?")[0] == "/harness.html":
            body = HARNESS.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if not self.path.startswith("/engine/"):
            self.send_error(404)
            return
        super().do_GET()

    def guess_type(self, path):
        return "text/javascript" if str(path).endswith(".js") else super().guess_type(path)

    def log_message(self, *a):
        pass


def check(cond, msg, failures):
    print(f"  {'PASS' if cond else 'FAIL'}: {msg}")
    if not cond:
        failures.append(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8157)
    args = ap.parse_args()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    failures = []
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{args.port}/harness.html")
            page.wait_for_function("window.ready === true")

            print("engine/greek.js")
            for fn, fargs, want, msg in UNIT_CASES:
                got = page.evaluate(f"(a) => window.greek.{fn}(...a)", fargs)
                check(got == want, f"{msg} (got {json.dumps(got, ensure_ascii=False)})", failures)

            diff = page.evaluate("() => window.greek.accentDiff('λογός ἄγει', 'λόγος ἄγει')")
            marks = [[c["ok"] for c in w["clusters"]] for w in diff]
            check(marks == [[True, False, True, False, True], [True, True, True, True]],
                  f"accentDiff marks the misplaced and missing accents (got {marks})", failures)
            diff = page.evaluate("() => window.greek.accentDiff('ἐστιν', 'ἐστίν')")
            check(diff[0]["ok"], "accentDiff does not mark an enclitic's accent", failures)

            print("engine/keyboard.js + el_GR")
            page.focus("#answer")
            check(page.is_visible(".keyboard"), "on-screen keyboard shows on focus", failures)

            def press(key):
                page.dispatch_event(f".keyboard button[data-key='{key}']", "mousedown")

            for k in ["α", "̓́", "ν", "θ", "ρ", "ω", "π", "ο", "σ"]:
                press(k)
            got = page.input_value("#answer")
            check(got == "ἄνθρωπος", f"typing α + smooth acute + νθρωποσ gives ἄνθρωπος (got {got})", failures)
            check(page.evaluate("(s) => s === s.normalize('NFC')", got), "typed text is NFC", failures)

            page.fill("#answer", "")
            page.focus("#answer")
            for k in ["ω", "ͅ", "̔", "δ", "η", "͂", "ͅ"]:
                press(k)
            got = page.input_value("#answer")
            check(got == "ᾡδῇ", f"marks typed after the letter in any order give ᾡδῇ (got {got})", failures)

            glyph = page.text_content(".keyboard button[data-key='̔́'] .kb-glyph")
            check(glyph == "ἅ", f"mark key shows its mark on a carrier letter (got {glyph})", failures)
            print("translate-phrase under the Greek and Hebrew script profiles")
            greek_course = {"script": {"direction": "ltr", "keyboard": "el_GR", "profile": "greek", "code": "grc"}}
            page.evaluate("(c) => window.setScript(c)", greek_course)

            def grade(accepted, answer, pointed):
                item = {"type": "translate-phrase", "prompt": "p", "stimulus": "s", "accepted": [accepted], "answerIsScript": True}
                if pointed:
                    item["pointing"] = "required"
                return page.evaluate("([i, a]) => window.tp.grade(i, a)", [item, answer])

            for accepted, answer, pointed, want, msg in [
                ("λόγος", "λογος", False, True, "typed rung: λογος = λόγος (accents not checked)"),
                ("λόγος", "λογος", True, False, "top rung: λογος ≠ λόγος"),
                ("λόγος", "λόγος", True, True, "top rung: λόγος = λόγος"),
                ("ἄνθρωπος", "ανθρωπος", False, False, "typed rung: a missing breathing is wrong"),
                ("τῷ λόγῳ", "τῶ λόγω", False, False, "typed rung: the iota subscript is required"),
                ("ἀλλὰ ἐστίν", "ἀλλ’ ἐστι", True, True, "top rung: elision, movable nu and an enclitic's accent are tolerated"),
                ("ἄνθρωπός τις", "ἄνθρωπος τις", True, True, "top rung: an accent thrown back from an enclitic is optional"),
                ("ἀδελφὸς βλέπει ἄνθρωπον.", "βλέπει ἄνθρωπον ἀδελφός.", True, True, "top rung: another word order of the same words"),
                ("ἀδελφὸς βλέπει ἄνθρωπον.", "βλεπει ἀνθρωπον ἀδελφος.", False, True, "typed rung: another word order with breathings"),
                ("ἀδελφὸς βλέπει ἄνθρωπον.", "βλεπει ανθρωπον ἀδελφος.", False, False, "typed rung: another word order, a breathing missing"),
                ("ὁ δὲ λόγος μένει.", "δὲ ὁ λόγος μένει.", False, False, "a postpositive first is wrong"),
                ("ὁ λόγος μένει.", "λόγος μένει ὁ.", False, False, "an article last is wrong"),
            ]:
                got = grade(accepted, answer, pointed)
                check(got["correct"] == want, f"{msg} (got {got['correct']})", failures)
            got = grade("ἀδελφὸς βλέπει ἄνθρωπον.", "ἄνθρωπον βλέπει ἀδελφός.", True)
            check(got["correct"] and got.get("note") == "Our word order: ἀδελφὸς βλέπει ἄνθρωπον.",
                  f"a reordered answer is right and the feedback shows our order (got {got})", failures)
            got = grade("ἀδελφὸς βλέπει ἄνθρωπον.", "ἀδελφὸς βλέπει ἄνθρωπον.", True)
            check(got["correct"] and "note" not in got, f"our own order gets no order note (got {got})", failures)
            got = grade("λόγος", "λογος", True)
            check(got.get("message") == "Accents are required here.", f"top rung asks for accents (got {got.get('message')!r})", failures)

            page.evaluate("""(c) => {
              const item = { type: "translate-phrase", prompt: "Translate", stimulus: "word", accepted: ["λόγος"], answerIsScript: true, pointing: "required" };
              const node = window.tp.render(item, { course: c });
              node.id = "tp";
              document.body.appendChild(node);
            }""", greek_course)
            attrs = page.evaluate("() => { const i = document.querySelector('#tp .ex-text'); return [i.className, i.dir, i.lang]; }")
            check("hebrew-input" in attrs[0] and attrs[1] == "ltr" and attrs[2] == "grc",
                  f"Greek answer input opens the keyboard, LTR, lang grc (got {attrs})", failures)
            page.focus("#tp .ex-text")
            for k in ["λ", "ο", "\u0301", "γ", "ο", "σ"]:
                press(k)
            typed = page.input_value("#tp .ex-text")
            res = page.evaluate("() => { const n = document.querySelector('#tp'); const a = window.tp.collect(n); return [a, window.tp.grade({ accepted: ['λόγος'], answerIsScript: true, pointing: 'required' }, a).correct]; }")
            check(typed == "λόγος" and res[1], f"typing λόγος on the on-screen keyboard passes the top rung (typed {typed!r}, graded {res[1]})", failures)
            marks = page.evaluate("""() => {
              const item = { accepted: ['λόγος'], answerIsScript: true, pointing: 'required' };
              const node = document.querySelector('#tp');
              const result = window.tp.grade(item, 'λογός');
              window.tp.annotate(node, item, 'λογός', result);
              return [...node.querySelectorAll('.ex-pointing-words span span')].map((s) => s.className);
            }""")
            check(marks == ["pt-ok", "pt-no", "pt-ok", "pt-no", "pt-ok"], f"wrong accents are marked letter by letter (got {marks})", failures)

            page.evaluate("() => window.setScript({ script: { direction: 'rtl', keyboard: 'he_IL' } })")
            heb = [grade("דָּבָר", "דבר", False)["correct"], grade("דָּבָר", "דבר", True)["correct"],
                   grade("דָּבָר", "דבר", True).get("message")]
            check(heb == [True, False, "Vowel points are required here."], f"Hebrew profile unchanged (got {heb})", failures)
            heb_order = grade("אִישׁ טוֹב", "טוֹב אִישׁ", True)
            check(heb_order == {"correct": False, "expected": "אִישׁ טוֹב", "message": None},
                  f"Hebrew grading keeps word order and adds no note (got {heb_order})", failures)

            check(not errors, f"no page errors ({errors})", failures)
            browser.close()
    finally:
        server.shutdown()

    if failures:
        print(f"GREEK FAIL — {len(failures)} check(s) failed")
        return 1
    print("GREEK OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
