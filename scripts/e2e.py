#!/usr/bin/env python3
"""scripts/e2e.py — browser regression test for the course engine.

Drives the local course app in a headless Chromium browser (Playwright) and asserts
the core loop end to end: complete each unit's drill -> unit marked done -> the next
unit becomes available. Also verifies the progress stored in the browser (localStorage).

Answer correctness is determined from the course's own vocab.json (scriptForm<->gloss
<->transliteration), so the test exercises the real generated drills, not hardcoded
data.

Requirements (dev/test only; not needed to run the course):
    .venv/bin/pip install playwright
    .venv/bin/python -m playwright install chromium

Usage:
    python scripts/e2e.py courses/biblical-hebrew-davidson          # complete units 1..2
    python scripts/e2e.py courses/biblical-hebrew-davidson --units 3 --port 8146
    python scripts/e2e.py courses/biblical-hebrew-davidson --exercise-types  # plugin harness

Exit code 0 on success, 1 on any assertion failure.
"""

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HEBREW = re.compile(r"[\u0590-\u05FF]")

GENDER_WORDS = {"m": "masculine", "f": "feminine", "c": "common"}
NUMBER_WORDS = {"s": "singular", "p": "plural", "d": "dual"}


def noun_label(item):
    parts = []
    if item.get("gender") in GENDER_WORDS:
        parts.append(GENDER_WORDS[item["gender"]])
    if item.get("number") in NUMBER_WORDS:
        parts.append(NUMBER_WORDS[item["number"]])
    return " ".join(parts)


def load_vocab(course):
    with open(f"{course}/vocab.json", encoding="utf-8") as f:
        items = json.load(f)["items"]
    by_unit = {}
    script_map = {}
    gloss_map = {}
    translit_map = {}
    produce_map = {}
    parse_map = {}
    unit_gloss = {}
    unit_translit = {}
    for x in items:
        by_unit.setdefault(x["unit"], {})[x["scriptForm"]] = x
        script_map.setdefault(x["scriptForm"], x)
        gloss_map.setdefault(x["gloss"], x)
        translit_map.setdefault(x["transliteration"], x)
        unit_gloss.setdefault(x["unit"], {}).setdefault(x["gloss"], x)
        unit_translit.setdefault(x["unit"], {}).setdefault(x["transliteration"], x)
        if x["category"] == "verb":
            extra = x.get("extra") or {}
            if extra.get("parse"):
                parse_map.setdefault(x["scriptForm"], extra["parse"])
            if extra.get("parse") and x.get("root"):
                produce_map.setdefault(f"{extra['parse']} (root {x['root']})", x["scriptForm"])
            for f in extra.get("forms", []):
                if f.get("scriptForm") and f.get("parse"):
                    parse_map.setdefault(f["scriptForm"], f["parse"])
                if f.get("parse") and x.get("root"):
                    produce_map.setdefault(f"{f['parse']} (root {x['root']})", f["scriptForm"])
    return {
        "by_unit": by_unit,
        "script": script_map,
        "gloss": gloss_map,
        "translit": translit_map,
        "produce": produce_map,
        "parse": parse_map,
        "unit_gloss": unit_gloss,
        "unit_translit": unit_translit,
    }


def start_server(course, port):
    proc = subprocess.Popen(
        [sys.executable, "scripts/run", course, "--no-browser", f"--port={port}"],
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


def load_authored(course):
    authored = {}
    base = Path(course) / "authored"
    if not base.is_dir():
        return authored
    for p in sorted(base.glob("[0-9][0-9].json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        authored[data.get("unit")] = data.get("items", [])
    return authored


def answer_authored(page, items):
    code = page.text_content(".drill-item-code") if page.query_selector(".drill-item-code") else ""
    exact = [it for it in items if code == f"Item {it.get('id')}"]
    for it in exact or items:
        t = it.get("type")
        if t == "true-false":
            stim_el = page.query_selector(".ex--tf .ex-stimulus")
            st_el = page.query_selector(".ex--tf .ex-statement")
            if stim_el and st_el and stim_el.text_content().strip() == it.get("stimulus") \
                    and st_el.text_content().strip() == it.get("statement"):
                page.click(f".ex--tf .ex-option[data-value='{'true' if it['answer'] else 'false'}']")
                return True
            continue
        if t in ("mcq", "paradigm-tag", "root-pattern-compose", "spot-error", "flash-timed"):
            stim_el = page.query_selector(".ex--mcq .ex-stimulus")
            if stim_el and stim_el.text_content().strip() == it.get("stimulus"):
                for opt in page.query_selector_all(".ex--mcq .ex-option"):
                    if opt.get_attribute("data-value") == it["answer"]:
                        opt.click()
                        return True
        elif t == "translate-phrase":
            stim_el = page.query_selector(".ex--translate .ex-stimulus")
            prompt_el = page.query_selector(".ex--translate .ex-prompt")
            if stim_el and stim_el.text_content().strip() == it.get("stimulus") \
                    and (not prompt_el or prompt_el.text_content().strip() == it.get("prompt")):
                page.fill(".ex--translate .ex-text", it["accepted"][0])
                return True
        elif t == "translit-normalize":
            stim_el = page.query_selector(".ex--translit .ex-stimulus")
            if stim_el and stim_el.text_content().strip() == it.get("stimulus"):
                page.fill(".ex--translit .hebrew-input", it["answer"])
                return True
        elif t == "parse-form":
            stim_el = page.query_selector(".ex--parse-form .ex-stimulus")
            if stim_el and stim_el.text_content().strip() == it.get("stimulus"):
                for f in it["fields"]:
                    page.select_option(f".ex--parse-form .ex-select[data-field='{f['key']}']",
                                       value=it["readings"][0].get(f["key"], "—"))
                return True
        elif t == "paradigm-fill":
            el = page.query_selector(".ex--paradigm-fill")
            if el:
                for row in it.get("rows", []):
                    sel = el.query_selector(f".ex-select[data-label='{row['label']}']")
                    if sel:
                        sel.select_option(value=row["answer"])
                return True
        elif t == "fill-blank-verse":
            el = page.query_selector(".ex--blank")
            if el:
                for opt in page.query_selector_all(".ex--blank .ex-option"):
                    if opt.get_attribute("data-value") == it["answer"]:
                        opt.click()
                        return True
    return False


def click_option(page, selector, answer):
    for opt in page.query_selector_all(selector):
        if opt.get_attribute("data-value") == answer:
            opt.click()
            return True
    return False


def answer_current(page, vocab, unit_n, authored=None):
    if authored:
        code_el = page.query_selector(".drill-item-code")
        code = code_el.text_content().removeprefix("Item ") if code_el else None
        by_id = {it.get("id"): it for items in authored.values() for it in items if it.get("id")}
        if code in by_id and answer_authored(page, [by_id[code]]):
            return
        if answer_authored(page, authored.get(unit_n, [])):
            return

    unit_map = vocab["by_unit"].get(unit_n, {})
    unit_gloss = vocab["unit_gloss"].get(unit_n, {})
    unit_translit = vocab["unit_translit"].get(unit_n, {})

    if page.query_selector(".ex--parse-noun"):
        stim = page.text_content(".ex--parse-noun .ex-stimulus").strip()
        item = unit_map.get(stim) or vocab["script"].get(stim)
        if item is None:
            raise RuntimeError(f"parse-noun stimulus not found in vocab: {stim!r}")
        if click_option(page, ".ex--parse-noun .ex-option", noun_label(item)):
            return
        raise RuntimeError(f"parse-noun option not found: {noun_label(item)!r} stim={stim!r}")

    if page.query_selector(".ex--parse-verb"):
        stim = page.text_content(".ex--parse-verb .ex-stimulus").strip()
        answer = vocab["parse"].get(stim)
        if answer is None:
            raise RuntimeError(f"parse-verb stimulus not found in vocab: {stim!r}")
        if click_option(page, ".ex--parse-verb .ex-option", answer):
            return
        raise RuntimeError(f"parse-verb option not found: {answer!r}")

    if page.query_selector(".ex--produce"):
        stim = page.text_content(".ex--produce .ex-stimulus").strip()
        if "(root " in stim:
            answer = vocab["produce"].get(stim)
        else:
            item = unit_map.get(stim) or vocab["script"].get(stim)
            answer = item["plural"] if item is not None else None
        if answer is None:
            raise RuntimeError(f"produce stimulus not found in vocab: {stim!r}")
        if click_option(page, ".ex--produce .ex-option", answer):
            return
        raise RuntimeError(f"produce option not found: {answer!r} stim={stim!r}")

    if page.query_selector(".ex--mcq"):
        stim = page.text_content(".ex--mcq .ex-stimulus").strip()
        # Determine the direction from what the stimulus actually is, not from
        # whether it contains Hebrew: some glosses embed Hebrew text (e.g.
        # "he forgave (verb סָלַח...)"), so a gloss->script stimulus can match
        # the Hebrew regex and must still resolve via the gloss map. Prefer the
        # current unit's maps so cross-unit gloss collisions (e.g. "this") resolve
        # to the unit's own item.
        item = unit_map.get(stim) or vocab["script"].get(stim)
        if item is not None:
            correct = item["gloss"]
        else:
            item = (unit_gloss.get(stim) or unit_translit.get(stim)
                    or vocab["gloss"].get(stim) or vocab["translit"].get(stim))
            if item is None:
                raise RuntimeError(f"mcq stimulus not found in vocab: {stim!r}")
            correct = item["scriptForm"]
        for opt in page.query_selector_all(".ex--mcq .ex-option"):
            if opt.get_attribute("data-value") == correct:
                opt.click()
                return
        raise RuntimeError(f"mcq option not found: correct={correct!r} stim={stim!r}")

    if page.query_selector(".ex--match"):
        for row in page.query_selector_all(".ex-match-row"):
            hebrew = row.query_selector(".script").text_content().strip()
            gloss = unit_map[hebrew]["gloss"]
            row.query_selector("select").select_option(value=gloss)
        return

    if page.query_selector(".ex--categorize"):
        for row in page.query_selector_all(".ex-cat-row"):
            word = row.query_selector(".script").text_content().strip()
            cat = unit_map[word]["category"]
            row.query_selector("select").select_option(value=cat)
        return

    if page.query_selector(".ex--translate"):
        stim = page.text_content(".ex--translate .ex-stimulus").strip()
        gloss = unit_map[stim]["gloss"]
        page.fill(".ex--translate .ex-text", gloss)
        return

    if page.query_selector(".ex--dictation"):
        stim = page.text_content(".ex--dictation .ex-stimulus").strip()
        item = vocab["gloss"].get(stim)
        page.fill(".ex--dictation .hebrew-input", item["transliteration"])
        return

    raise RuntimeError("unknown question type")


def run_drill(page, vocab, unit_n, authored=None, max_sessions=80):
    """Play sessions of a unit until it is done (one session for vocabulary units, several for a ladder)."""
    qcount = 0
    result = ""
    for _ in range(max_sessions):
        page.click(f".unit[data-unit='{unit_n}']")
        page.wait_for_selector(".lesson-title")
        page.click(".gate .gate-btn")
        page.wait_for_selector(".drill-stage")
        while True:
            if page.query_selector(".drill-result"):
                break
            qcount += 1
            answer_current(page, vocab, unit_n, authored)
            page.click(".drill-feedback .gate-btn")
            page.wait_for_selector(".drill-feedback .gate-btn")
            page.click(".drill-feedback .gate-btn:not(.drill-selfcheck-no)")
            page.wait_for_selector(".drill-stage, .drill-result")
        result = page.text_content(".drill-result").strip()
        page.click(".gate-btn")
        page.wait_for_selector(".roadmap")
        if "unit--done" in (page.get_attribute(f".unit[data-unit='{unit_n}']", "class") or ""):
            break
    return qcount, result


def unit_classes(page, n):
    return page.get_attribute(f".unit[data-unit='{n}']", "class") or ""


def check(cond, msg, failures):
    print(f"  {'PASS' if cond else 'FAIL'}: {msg}")
    if not cond:
        failures.append(msg)


EXERCISE_TYPES = [
    "root-pattern-compose",
    "spot-error",
    "translit-normalize",
    "gap-fill-verse",
    "flash-timed",
    "identify-binyan",
    "build-construct-chain",
]

HARNESS_JS = r"""
async () => {
  const origin = window.location.origin;
  const { getType } = await import(origin + "/engine/exercise-types/index.js");
  const course = await (await fetch(origin + "/course.json")).json();
  const vocab = await (await fetch(origin + "/vocab.json")).json();
  const pool = vocab.items;
  const results = [];
  for (const id of %(type_ids)s) {
    const t = getType(id);
    if (!t) { results.push({ id, ok: false, error: "not registered" }); continue; }
    const items = t.generate({}, pool);
    const item = items && items[0];
    if (!item) { results.push({ id, ok: false, error: "generate returned nothing" }); continue; }
    const node = t.render(item, { course });
    document.body.appendChild(node);
    let answer = null;
    try {
      if (item.options) {
        const btn = Array.from(node.querySelectorAll(".ex-option")).find(
          (b) => b.dataset.value === item.answer,
        );
        if (btn) btn.click();
      } else if (item.blanks) {
        Array.from(node.querySelectorAll(".ex-gap-select")).forEach((sel, i) => {
          sel.value = item.blanks[i].word;
        });
      } else if (node.querySelector(".hebrew-input")) {
        node.querySelector(".hebrew-input").value = item.answer;
      }
      answer = t.collect ? t.collect(node, item) : null;
    } catch (e) {
      results.push({ id, ok: false, error: "render/collect threw: " + e.message });
      node.remove();
      continue;
    }
    const res = t.grade(item, answer);
    results.push({
      id,
      ok: res.correct === true && !!answer,
      answered: !!answer,
      correct: res.correct === true,
      error: res.correct ? "" : "grade expected correct with the right answer",
    });
    node.remove();
  }
  return results;
}
"""


DUPLICATE_MATCH_JS = r"""
() => import(location.origin + "/engine/exercise-types/index.js").then(async ({ getType }) => {
  const pool = (await (await fetch(location.origin + "/vocab.json")).json()).items;
  const grouped = new Map();
  for (const item of pool) {
    const group = grouped.get(item.scriptForm) || [];
    group.push(item);
    grouped.set(item.scriptForm, group);
  }
  let duplicateGroup = Array.from(grouped.values()).find((group) => group.length > 1);
  if (!duplicateGroup) {
    const [a, b, c, d] = pool;
    duplicateGroup = [a, { ...a, id: a.id + "-dup", gloss: b.gloss }, c, d];
  }
  const match = getType("match-by-line");
  const item = match.generate({}, duplicateGroup)[0];
  const uniqueLeft = new Set(item.left);
  const ok = uniqueLeft.size === item.left.length
    && Object.keys(item.answer).length === item.left.length
    && match.grade(item, item.answer).correct;
  return { found: true, ok };
})
"""


SINGLE_OPTION_JS = r"""
async () => {
  const origin = window.location.origin;
  const { buildSession } = await import(origin + "/engine/session.js");
  const course = await (await fetch(origin + "/course.json")).json();
  const vocab = await (await fetch(origin + "/vocab.json")).json();
  const features = course.features || {};
  const violations = [];
  for (let n = 1; n <= course.units.length; n++) {
    const progress = { units: {} };
    for (let u = 1; u < n; u++) progress.units[String(u)] = { state: "done" };
    const pool = vocab.items.filter((i) => i.unit === n);
    const items = buildSession(course, pool, {
      unitN: n, vocabList: vocab.items, progress, authored: [], features,
    });
    for (const it of items) {
      if (Array.isArray(it.options) && new Set(it.options).size < 2) {
        violations.push({ unit: n, type: it.type, options: it.options });
      }
    }
  }
  return { units: course.units.length, violations };
}
"""


LESSON_HEADINGS_JS = r"""
async (n) => {
  const origin = window.location.origin;
  const { renderLesson } = await import(origin + "/engine/views/lesson.js");
  const course = await (await fetch(origin + "/course.json")).json();
  const lesson = await (await fetch(origin + "/units/" + String(n).padStart(2, "0") + ".json")).json();
  const unit = course.units.find((u) => u.n === n);
  const root = document.createElement("div");
  renderLesson(root, { course, vocab: {}, progress: { units: {} }, navigate() {}, onStartDrills() {} }, unit, lesson);
  return Array.from(root.querySelectorAll(".block-prose-heading"), (h) => h.textContent.trim());
}
"""


AUTHORED_SAMPLES = [
    {"type": "mcq", "stimulus": "בָרַח", "stimulusIsScript": True,
     "options": ["he fled", "he fell", "he opened"], "answer": "he fled", "optionIsScript": False},
    {"type": "paradigm-tag", "stimulus": "קָטַלְתִּי", "stimulusIsScript": True,
     "options": ["1cs", "2ms", "3ms"], "answer": "1cs", "optionIsScript": False},
    {"type": "match-by-line", "prompt": "Match", "left": ["בָרַח", "נָפַל"],
     "right": ["he fell", "he fled"], "answer": {"בָרַח": "he fled", "נָפַל": "he fell"}, "leftIsScript": True},
    {"type": "categorize", "prompt": "Sort", "columns": ["verb", "noun"],
     "words": [{"text": "בָרַח", "cat": "verb"}, {"text": "אֵש", "cat": "noun"}], "isScript": True},
    {"type": "translate-phrase", "prompt": "Translate", "stimulus": "בָרַח",
     "stimulusIsScript": True, "accepted": ["he fled"]},
    {"type": "dictation", "prompt": "Type", "stimulus": "he fled", "stimulusIsScript": False,
     "answer": "בָרַח", "transliteration": "bāraḥ"},
    {"type": "paradigm-fill", "prompt": "Complete", "isScript": True,
     "rows": [
         {"label": "1cs", "answer": "קָטַלְתִּי", "options": ["קָטַלְתִּי", "קָטַלְתָּ", "קָטְלָה"]},
         {"label": "3fs", "answer": "קָטְלָה", "options": ["קָטַלְתִּי", "קָטַלְתָּ", "קָטְלָה"]},
     ]},
    {"type": "fill-blank-verse", "prompt": "Fill", "before": "וַיִּשְׁמַע", "after": "אֶת־קוֹלוֹ",
     "options": ["קוֹל", "קוֹלוֹ", "קָל"], "answer": "קוֹלוֹ", "isScript": True},
    {"type": "translit-normalize", "direction": "translit->script", "stimulus": "bāraḥ",
     "stimulusIsScript": False, "answer": "בָרַח", "answerIsScript": True},
]

AUTHORED_HARNESS_JS = r"""
async () => {
  const origin = window.location.origin;
  const { getType } = await import(origin + "/engine/exercise-types/index.js");
  const course = await (await fetch(origin + "/course.json")).json();
  const samples = %(samples)s;
  const results = [];
  for (const item of samples) {
    const t = getType(item.type);
    if (!t) { results.push({ type: item.type, ok: false, error: "not registered" }); continue; }
    const node = t.render(item, { course });
    document.body.appendChild(node);
    let answer = null;
    try {
      if (item.type === "true-false") {
        node.querySelector(`.ex-option[data-value='${item.answer}']`).click();
      } else if (item.left) {
        node.querySelectorAll(".ex-select").forEach((sel) => { sel.value = item.answer[sel.dataset.left]; });
      } else if (item.words) {
        node.querySelectorAll(".ex-select").forEach((sel) => {
          const w = item.words.find((w) => w.text === sel.dataset.word);
          if (w) sel.value = w.cat;
        });
      } else if (item.fields) {
        node.querySelectorAll(".ex-select").forEach((sel) => { sel.value = item.readings[0][sel.dataset.field] || "—"; });
      } else if (item.rows) {
        node.querySelectorAll(".ex-select").forEach((sel) => {
          const r = item.rows.find((r) => r.label === sel.dataset.label);
          if (r) sel.value = r.answer;
        });
      } else if (item.accepted) {
        const input = node.querySelector(".ex-text");
        if (input) input.value = item.accepted[0];
      } else if (item.options) {
        const btn = Array.from(node.querySelectorAll(".ex-option")).find((b) => b.dataset.value === item.answer);
        if (btn) btn.click();
      } else {
        const input = node.querySelector(".hebrew-input") || node.querySelector(".ex-text");
        if (input) input.value = item.answer;
      }
      answer = t.collect ? t.collect(node, item) : null;
    } catch (e) {
      results.push({ type: item.type, ok: false, error: "answer threw: " + e.message });
      node.remove();
      continue;
    }
    const res = t.grade(item, answer);
    results.push({ type: item.type, ok: res.correct === true && answer !== null && answer !== undefined, error: res.correct ? "" : "expected correct" });
    node.remove();
  }
  return results;
}
"""

SESSION_MIX_HARNESS_JS = r"""
async () => {
  const origin = window.location.origin;
  const unit = %(unit)s;
  const { buildSession } = await import(origin + "/engine/session.js");
  const course = await (await fetch(origin + "/course.json")).json();
  const vocab = await (await fetch(origin + "/vocab.json")).json();
  const pool = vocab.items.filter((i) => i.unit === unit);
  let authored = [];
  try {
    const d = await (await fetch(origin + "/authored/" + String(unit).padStart(2, "0") + ".json")).json();
    authored = d.items || [];
  } catch (e) {
    return { unit, error: "authored/" + String(unit).padStart(2, "0") + ".json not loadable: " + e.message };
  }
  const items = buildSession(course, pool, { unitN: unit, vocabList: vocab.items, progress: { units: {} }, authored, features: course.features || {} });
  const authoredSet = new Set(authored);
  if (authored.some((i) => i.rung)) {
    const climb = items.filter((i) => authoredSet.has(i));
    const target = (course.features || {}).targetItems || 14;
    const lowest = Math.min(...authored.map((i) => i.rung));
    const ordered = climb.every((i, k) => k === 0 || climb[k - 1].rung <= i.rung);
    const filled = items.length === Math.min(target, items.length - climb.length + authored.length);
    return {
      unit, authoredCount: authored.length, sessionCount: items.length, ladder: true,
      inSession: climb.length > 0 && climb[0].rung === lowest && filled,
      beforeGenerated: ordered,
      types: items.map((i) => i.rung ? `${i.type}@${i.rung}` : i.type),
    };
  }
  const firstAuthored = items.findIndex((i) => authoredSet.has(i));
  const generatedStart = items.findIndex((i) => !i.spiral && !authoredSet.has(i));
  const cap = (course.features || {}).authoredPerSession || authored.length;
  const inSession = items.filter((i) => authoredSet.has(i)).length === Math.min(cap, authored.length);
  const beforeGenerated = authored.length === 0 || generatedStart === -1 || (firstAuthored >= 0 && firstAuthored < generatedStart);
  return {
    unit,
    authoredCount: authored.length,
    sessionCount: items.length,
    inSession,
    beforeGenerated,
    types: items.map((i) => i.type),
  };
}
"""

AUTHORED_BENCHMARK_UNITS = [20, 24]


def _authored_units(course):
    """Unit numbers that have an authored exercise file in this course."""
    import glob as _glob

    base = Path(course) / "authored"
    return sorted(int(Path(f).stem) for f in _glob.glob(str(base / "[0-9][0-9].json")))


def run_authored_harness(page, failures, benchmark_units=None):
    results = page.evaluate(AUTHORED_HARNESS_JS % {"samples": json.dumps(AUTHORED_SAMPLES, ensure_ascii=False)})
    for r in results:
        msg = f"authored {r['type']}: render->collect->grade correct with right answer"
        check(r.get("ok", False), msg, failures)
        if not r.get("ok"):
            print(f"      error: {r.get('error', '?')}")
    for unit in AUTHORED_BENCHMARK_UNITS if benchmark_units is None else benchmark_units:
        mix = page.evaluate(SESSION_MIX_HARNESS_JS % {"unit": unit})
        if "error" in mix:
            check(False, f"session mix loads authored/{unit:02d}.json ({mix['error']})", failures)
            continue
        if mix.get("ladder"):
            check(mix["inSession"], f"ladder session (unit {unit}) starts at the lowest rung and fills the session", failures)
            check(mix["beforeGenerated"], f"ladder session (unit {unit}) climbs in rung order", failures)
        else:
            check(mix["inSession"], f"session mix (unit {unit}) includes every authored item (or authoredPerSession of them)", failures)
            check(mix["beforeGenerated"], f"authored items (unit {unit}) precede generated fill", failures)
        print(f"  session mix unit {unit}: {mix['authoredCount']} authored items in a {mix['sessionCount']}-item session, types={mix['types']}")
    return len(results)


DRILL_TIP_JS = r"""
async (items) => {
  const origin = window.location.origin;
  const { renderDrill } = await import(origin + "/engine/views/drill.js");
  const course = await (await fetch(origin + "/course.json")).json();
  const out = [];
  for (const item of items) {
    const root = document.createElement("div");
    document.body.appendChild(root);
    renderDrill(root, { course, items: [item], unit: { n: 1 }, navigate() {}, onComplete() {}, features: {} });
    const r = { hint: !!item.hint, explain: !!item.explain };
    r.toggleBefore = !!root.querySelector(".drill-tip-toggle");
    r.explainBefore = !!root.querySelector(".drill-explain");
    const toggle = root.querySelector(".drill-tip-toggle");
    if (toggle) toggle.click();
    r.hintText = (root.querySelector(".drill-tip-text") || {}).textContent || "";
    const check = Array.from(root.querySelectorAll(".gate-btn")).find((b) => b.textContent === "Check");
    const input = root.querySelector(".ex-text");
    if (input) input.value = (item.accepted || [""])[0];
    const opt = Array.from(root.querySelectorAll(".ex-option")).find((b) => b.dataset.value === item.answer);
    if (opt) opt.click();
    check.click();
    r.correct = !!root.querySelector(".drill-ok");
    r.explainText = (root.querySelector(".drill-explain") || {}).textContent || "";
    root.remove();
    out.push(r);
  }
  return out;
}
"""


def run_drill_tips(page, authored, failures):
    """P9-T7: a hint opens on request before answering; an explanation appears with feedback."""
    flat = [it for unit in sorted(authored) for it in authored[unit]]
    picks = [next((it for it in flat if it.get("hint")), None), next((it for it in flat if it.get("explain")), None)]
    picks = [p for p in picks if p]
    if not picks:
        return 0
    for item, r in zip(picks, page.evaluate(DRILL_TIP_JS, picks)):
        if item.get("hint"):
            check(r["toggleBefore"] and r["hintText"] == item["hint"],
                  "hint: 'Show hint' button before answering opens the hint text", failures)
        if item.get("explain"):
            check(not r["explainBefore"] and r["explainText"] == item["explain"],
                  "explain: hidden before answering, shown with the feedback", failures)
        check(r["correct"], "drill with hint/explain still grades the right answer correct", failures)
    return len(picks)


PARSE_FIELDS_JS = r"""
async (item) => {
  const origin = window.location.origin;
  const { getType } = await import(origin + "/engine/exercise-types/index.js");
  const course = await (await fetch(origin + "/course.json")).json();
  const t = getType("parse-form");
  const run = (wrongKey) => {
    const node = t.render(item, { course });
    document.body.appendChild(node);
    node.querySelectorAll(".ex-select").forEach((sel) => {
      const key = sel.dataset.field;
      const right = item.readings[0][key] || "—";
      sel.value = key === wrongKey ? Array.from(sel.options).map((o) => o.value).find((v) => v && v !== right && !item.readings.some((r) => r[key] === v)) : right;
    });
    const answer = t.collect(node);
    const res = t.grade(item, answer);
    t.annotate(node, item, answer, res);
    const marked = node.querySelector(".ex-select[data-field='" + wrongKey + "']");
    const out = { correct: res.correct, fields: res.fields, expected: res.expected,
                  markedWrong: !!(marked && marked.classList.contains("ex-select--no")),
                  othersOk: Array.from(node.querySelectorAll(".ex-select")).filter((s) => s.dataset.field !== wrongKey).every((s) => s.classList.contains("ex-select--ok")) };
    node.remove();
    return out;
  };
  return { right: run(null), wrong: run(item.fields[0].key), wrongKey: item.fields[0].key };
}
"""


WRONG_FEEDBACK_JS = r"""
async (item) => {
  const origin = window.location.origin;
  const { renderDrill } = await import(origin + "/engine/views/drill.js");
  const course = await (await fetch(origin + "/course.json")).json();
  const root = document.createElement("div");
  document.body.appendChild(root);
  renderDrill(root, { course, items: [item], unit: { n: 1 }, navigate() {}, onComplete() {}, features: { diagnostics: true } });
  const opt = Array.from(root.querySelectorAll(".ex-option")).find((b) => b.dataset.value !== item.answer);
  opt.click();
  Array.from(root.querySelectorAll(".gate-btn")).find((b) => b.textContent === "Check").click();
  const boxes = Array.from(root.querySelectorAll(".drill-feedback > *")).map((n) => n.getBoundingClientRect());
  const hit = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
  let overlap = false;
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) if (hit(boxes[i], boxes[j])) overlap = true;
  const out = { wrong: !!root.querySelector(".drill-no"), review: !!root.querySelector(".drill-feedback .back"), overlap };
  root.remove();
  return out;
}
"""


def run_wrong_feedback_layout(page, authored, failures):
    """The red 'Not quite' line, the review link and Next never overlap (desktop and phone width)."""
    item = next((it for u in sorted(authored) for it in authored[u]
                 if it.get("type") == "mcq" and len(it.get("options", [])) >= 2), None)
    if not item:
        return 0
    size = page.viewport_size
    for width in (1000, 400):
        page.set_viewport_size({"width": width, "height": 800})
        r = page.evaluate(WRONG_FEEDBACK_JS, item)
        check(r["wrong"] and r["review"] and not r["overlap"],
              f"wrong-answer feedback at {width}px: message, review link and Next do not overlap", failures)
    page.set_viewport_size(size)
    return 1


NO_TRANSLIT_JS = r"""
async () => {
  const origin = window.location.origin;
  const { buildSession } = await import(origin + "/engine/session.js");
  const course = await (await fetch(origin + "/course.json")).json();
  const vocab = await (await fetch(origin + "/vocab.json")).json();
  const items = vocab.items;
  const features = course.features || {};
  let leaks = 0, total = 0;
  for (let unit = 9; unit <= 30; unit++) {
    const pool = items.filter((x) => x.unit === unit);
    if (!pool.length) continue;
    const session = buildSession(course, pool, { features, unitN: unit, vocabList: items });
    for (const it of session) {
      total += 1;
      if (it.direction === "translit->script" || it.transliteration || /translit/i.test(JSON.stringify(it.prompt || ""))) leaks += 1;
    }
  }
  return { off: features.transliteration === false, leaks, total };
}
"""


def run_no_translit(page, failures):
    """A course with features.transliteration false never shows transliteration in a drill."""
    r = page.evaluate(NO_TRANSLIT_JS)
    if not r["off"]:
        return 0
    check(r["total"] > 0 and r["leaks"] == 0,
          f"transliteration off: {r['total']} generated items, none uses transliteration", failures)
    return 1


def run_parse_fields(page, authored, failures):
    """P9-T8: a parse item grades field by field (right answer; one wrong field flagged alone)."""
    item = next((it for u in sorted(authored) for it in authored[u]
                 if it.get("type") == "parse-form" and len(it["fields"]) >= 4), None)
    if not item:
        return 0
    r = page.evaluate(PARSE_FIELDS_JS, item)
    check(r["right"]["correct"] and all(r["right"]["fields"].values()),
          f"parse-form {item['stimulus']}: all fields right -> correct", failures)
    wk = r["wrongKey"]
    check(not r["wrong"]["correct"] and r["wrong"]["fields"][wk] is False
          and all(v for k, v in r["wrong"]["fields"].items() if k != wk),
          f"parse-form: one wrong field ({wk}) -> incorrect, only that field marked wrong", failures)
    check(r["wrong"]["markedWrong"] and r["wrong"]["othersOk"],
          "parse-form: the drill marks the wrong select red and the others green", failures)
    print(f"  parse-form feedback: {r['wrong']['expected']}")
    return 1


def run_course_shapes(page, authored, failures):
    """One course item per exercise shape (e.g. the exwb shapes) through render->collect->grade."""
    picked = {}
    for unit in sorted(authored):
        for it in authored[unit]:
            shape = it.get("shape")
            key = f"{shape} rung {it['rung']}" if it.get("rung") else shape
            if shape and key not in picked:
                picked[key] = it
    if not picked:
        return 0
    results = page.evaluate(AUTHORED_HARNESS_JS % {"samples": json.dumps(list(picked.values()), ensure_ascii=False)})
    for shape, r in zip(picked, results):
        check(r.get("ok", False), f"course shape {shape} ({r['type']}): render->collect->grade correct", failures)
    return len(picked)


def run_progress_ops(page, url, authored, course_dir, failures):
    """Reset all / reset a unit / mark a unit done / mark an exercise done or not done."""
    course = json.loads((Path(course_dir) / "course.json").read_text(encoding="utf-8"))
    cid = course["id"]
    slug = {u["n"]: u.get("slug") or f"u{u['n']}" for u in course["units"]}
    base = url.split("#")[0]

    def stored():
        raw = page.evaluate("k => localStorage.getItem(k)", f"lang-research.progress.{cid}")
        return json.loads(raw) if raw else None

    page.goto(f"{base}#/{slug[3]}")
    page.wait_for_selector(".unit-mark-done")
    check(not page.query_selector(".unit-reset"), "an untouched unit offers no reset", failures)
    page.click(".unit-mark-done")
    page.wait_for_selector(".unit-ops-done")
    p = stored()
    check(p["units"]["3"]["state"] == "done", "Mark unit as done stores unit 3 as done", failures)
    check(p["currentUnit"] >= 4, f"marking unit 3 done unlocks unit 4 (currentUnit {p['currentUnit']})", failures)
    page.goto(f"{base}#/")
    page.wait_for_selector(".roadmap")
    check("unit--done" in unit_classes(page, 3), "unit 3 shows done on the roadmap", failures)
    check("unit--available" in unit_classes(page, 2), "skipped unit 2 shows available, not locked", failures)
    check("unit--available" in unit_classes(page, 4), "unit 4 is available", failures)

    n = next(u for u in sorted(authored) if any(it.get("rung") for it in authored[u]))
    item = next(it for it in authored[n] if it.get("rung") and it.get("type") == "mcq")
    page.goto(f"{base}#/{slug[n]}/item/{item['id']}")
    page.wait_for_selector(".item-mark")
    check(page.text_content(".item-mark") == "Mark as done", "an unanswered exercise offers Mark as done", failures)
    page.click(".item-mark")
    page.wait_for_selector(".item-mark--done")
    done = (stored()["units"].get(str(n)) or {}).get("done", {}).get(str(item["rung"]), [])
    check(item["id"] in done, f"Mark as done records {item['id']} as done", failures)
    page.click(".item-mark")
    page.wait_for_selector(".item-mark:not(.item-mark--done)")
    done = (stored()["units"].get(str(n)) or {}).get("done", {}).get(str(item["rung"]), [])
    check(item["id"] not in done, "Mark as not done removes it again", failures)
    page.click(".item-mark")
    page.wait_for_selector(".item-mark--done")
    page.click(".ex-option")
    page.click(".drill-feedback .gate-btn")
    page.wait_for_selector(".drill-ok, .drill-no")
    check(page.is_enabled(".item-mark"), "the done toggle stays usable after Check", failures)
    page.goto(f"{base}#/{slug[n]}")
    page.wait_for_selector(".ladder-row")
    count = page.text_content(f".ladder-row[data-rung='{item['rung']}'] .blocks-count")
    check(count.startswith("1 /"), f"the lesson ladder counts the marked exercise ({count})", failures)

    page.click(".unit-reset .confirm-start")
    page.click(".unit-reset .confirm-no")
    check(page.is_visible(".unit-reset .confirm-start"), "Cancel keeps the unit", failures)
    page.click(".unit-reset .confirm-start")
    page.click(".unit-reset .confirm-yes")
    page.wait_for_selector(".unit-reset", state="detached")
    check(str(n) not in stored()["units"], f"Reset this unit clears unit {n}", failures)
    check("3" in stored()["units"], "resetting one unit leaves the others", failures)

    page.goto(f"{base}#/")
    page.wait_for_selector(".progress-reset")
    page.click(".progress-reset .confirm-start")
    page.click(".progress-reset .confirm-yes")
    page.wait_for_selector(".roadmap")
    check(page.text_content(".roadmap-stats").startswith("0 of"), "Reset all progress shows 0 units complete", failures)
    check(stored() is None, "Reset all progress clears the browser's stored progress", failures)
    check("unit--available" in unit_classes(page, 1) and "unit--locked" in unit_classes(page, 2),
          "after a reset only unit 1 is open", failures)
    return 1


def run_routes(browser, page, url, vocab, authored, course_dir, failures):
    """P12-T7: hash URLs, seeded sessions that resume, item codes, per-block progress."""
    course = json.loads((Path(course_dir) / "course.json").read_text(encoding="utf-8"))
    units = [u for u in course["units"] if any(it.get("block") for it in authored.get(u["n"], []))]
    if not units:
        return 0
    unit = max(units, key=lambda u: len(authored[u["n"]]))
    n, slug = unit["n"], unit.get("slug") or f"u{unit['n']}"
    base = url.split("#")[0]

    page.goto(f"{base}#/{slug}")
    page.wait_for_selector(".lesson-title")
    check(page.text_content(".lesson-title").startswith(f"Unit {n} "), f"#/{slug} opens the lesson of unit {n}", failures)

    page.click(".gate .gate-btn")
    page.wait_for_selector(".drill-stage")
    m = re.match(rf"^#/{slug}/drill/([a-z0-9]+)/1$", page.evaluate("location.hash"))
    check(bool(m), f"starting drills puts a seed in the URL ({page.evaluate('location.hash')})", failures)
    seed = m.group(1) if m else ""
    check((page.text_content(".drill-item-code") or "").startswith("Item "), "each question shows its item code", failures)
    first = page.inner_text(".drill-stage")

    answer_current(page, vocab, n, authored)
    page.click(".drill-feedback .gate-btn")
    page.wait_for_selector(".drill-feedback .gate-btn")
    page.click(".drill-feedback .gate-btn")
    page.wait_for_selector(".drill-stage")
    check(page.evaluate("location.hash") == f"#/{slug}/drill/{seed}/2", "the URL follows the question number", failures)

    page.reload()
    page.wait_for_selector(".drill-progress")
    check(page.text_content(".drill-progress").startswith("Question 2 of"), "a reload resumes at question 2", failures)

    other = browser.new_context().new_page()
    other.goto(f"{base}#/{slug}/drill/{seed}/1")
    other.wait_for_selector(".drill-stage")
    check(other.inner_text(".drill-stage") == first, "the same seed gives the same first question in a fresh browser", failures)
    other.close()

    page.goto(f"{base}#/{slug}")
    page.wait_for_selector(".lesson-title")
    resume = page.query_selector(".gate-resume")
    check(bool(resume) and "question 2" in resume.text_content(), "the lesson offers to resume at question 2", failures)

    item = next(it for it in authored[n] if it.get("block") and it.get("type") == "mcq")
    page.goto(f"{base}#/{slug}/item/{item['id']}")
    page.wait_for_selector(".drill-item-code")
    check(page.text_content(".drill-item-code") == f"Item {item['id']}", f"#/{slug}/item/{item['id']} shows that item", failures)
    answer_authored(page, [item])
    page.click(".drill-feedback .gate-btn")
    page.wait_for_selector(".drill-ok, .drill-no")
    check(bool(page.query_selector(".drill-ok")), "the linked item grades its key answer correct", failures)

    page.goto(f"{base}#/{slug}")
    page.wait_for_selector(".blocks-row")
    count = page.text_content(f".blocks-row[data-block='{item['block']}'] .blocks-count") or ""
    check(int(count.split("/")[0]) >= 1, f"the lesson counts right answers per block ({item['blockLabel']}: {count})", failures)

    page.goto(f"{base}#/{slug}/block/{item['block']}")
    page.wait_for_selector(".drill-item-code")
    hash_ = page.evaluate("location.hash")
    check(re.match(rf"^#/{slug}/block/{item['block']}/[a-z0-9]+/1$", hash_) is not None, f"block practice gets its own seeded URL ({hash_})", failures)
    check(page.text_content(".drill-item-code").startswith(f"Item {item['block']}-"), "block practice shows only that block's items", failures)

    merged = page.evaluate("""async () => {
      const { mergeProgress } = await import(window.location.origin + "/engine/store.js");
      const p = (done) => ({ units: { 5: { state: "in-progress", done } }, currentUnit: 5, knownSet: [], xp: 0, student: {} });
      const m = mergeProgress(p({ 1: ["s1-A1.tf", "s1-A2.tf"] }), p({ 1: ["s1-A2.tf", "s1-A3.tf"], 2: ["s1-A1.choice"] }));
      return m.units[5].done;
    }""")
    check(sorted(merged["1"]) == ["s1-A1.tf", "s1-A2.tf", "s1-A3.tf"] and merged["2"] == ["s1-A1.choice"],
          "importing progress merges right answers per rung (union)", failures)
    return 1


GRADE_JS = r"""
async ([item, answers]) => {
  const origin = window.location.origin;
  const { getType } = await import(origin + "/engine/exercise-types/index.js");
  const course = await (await fetch(origin + "/course.json")).json();
  const t = getType(item.type);
  return answers.map((a) => {
    const node = t.render(item, { course });
    document.body.appendChild(node);
    const r = t.grade(item, a);
    if (t.annotate) t.annotate(node, item, a, r);
    const out = { correct: r.correct, selfCheck: !!r.selfCheck, message: r.message || "",
                  red: node.querySelectorAll(".pt-no").length };
    node.remove();
    return out;
  });
}
"""


def run_ladder(browser, page, url, vocab, authored, course_dir, failures):
    """P12-T2/T3/T4: rungs in order, pointed grading with red marks, typed English with self-check, unlock."""
    course = json.loads((Path(course_dir) / "course.json").read_text(encoding="utf-8"))
    base = url.split("#")[0]
    units = {u["n"]: u for u in course["units"]}
    n = max((u for u in authored if any(it.get("rung") for it in authored[u])), key=lambda u: len(authored[u]))
    slug = units[n].get("slug") or f"u{n}"
    items = authored[n]

    page.goto(f"{base}#/{slug}")
    page.wait_for_selector(".ladder-row")
    rungs = [r.get_attribute("data-rung") for r in page.query_selector_all(".ladder-row")]
    check(rungs == ["1", "2", "3", "4", "5"], f"unit {n} shows a five-rung ladder ({rungs})", failures)
    page.click(".gate .gate-btn")
    page.wait_for_selector(".drill-progress")
    labels, seen = [], 0
    while not page.query_selector(".drill-result") and seen < 40:
        if not page.query_selector(".drill-review-tag"):
            labels.append(page.text_content(".drill-progress"))
        answer_current(page, vocab, n, authored)
        page.click(".drill-feedback .gate-btn")
        page.wait_for_selector(".drill-feedback .gate-btn")
        page.click(".drill-feedback .gate-btn")
        page.wait_for_selector(".drill-stage, .drill-result")
        seen += 1
    ladder_labels = [x.split("· ")[1] for x in labels if "· " in x]
    check(ladder_labels and set(ladder_labels) == {"True or false"},
          f"a first session climbs from rung 1 ({sorted(set(ladder_labels))})", failures)

    pointed = next(it for it in items if it.get("pointing") == "required" and " " in it["accepted"][0]
                   and re.search("[\u05b7\u05b8]", it["accepted"][0]))
    key = pointed["accepted"][0]
    wrong = key.replace("\u05b8", "\u05b7", 1) if "\u05b8" in key else key.replace("\u05b7", "\u05b8", 1)
    bare = re.sub("[\u0591-\u05c7]", "", key)
    maqqef = key.replace(" ", "\u05be", 1)
    r = page.evaluate(GRADE_JS, [pointed, [key, wrong, bare, maqqef]])
    check(r[0]["correct"], "pointed rung: the Key's pointing is correct", failures)
    check(not r[1]["correct"] and r[1]["red"] >= 1, f"pointed rung: one wrong vowel is wrong and marked red ({r[1]['red']})", failures)
    check(not r[2]["correct"] and "required" in r[2]["message"], "pointed rung: an unpointed answer is wrong, with a message", failures)
    check(r[3]["correct"], "pointed rung: maqqef and space are interchangeable", failures)
    pausal = next((it for it in items if it.get("pointing") == "required" and len(it["accepted"]) > 1), None)
    if pausal:
        r = page.evaluate(GRADE_JS, [pausal, pausal["accepted"]])
        check(all(x["correct"] for x in r), f"pointed rung: every accepted form passes ({pausal['id']})", failures)

    english = next(it for it in items if it.get("selfCheck"))
    r = page.evaluate(GRADE_JS, [english, [english["accepted"][-1], "something quite different"]])
    check(r[0]["correct"] and not r[1]["correct"] and r[1]["selfCheck"],
          "typed English: a Key variant is right; anything else asks for self-check", failures)
    page.goto(f"{base}#/{slug}/item/{english['id']}")
    page.wait_for_selector(".ex--translate .ex-text")
    page.fill(".ex--translate .ex-text", "something quite different")
    page.click(".drill-feedback .gate-btn")
    page.wait_for_selector(".drill-selfcheck-yes")
    page.click(".drill-selfcheck-yes")
    page.wait_for_selector(".drill-ok")
    check("Marked right" in page.text_content(".drill-ok"), "self-check: 'I had it right' counts the answer right", failures)

    limit = (course.get("features") or {}).get("unlockRung", 3)
    small = min((u for u in authored if any(it.get("rung") for it in authored[u]) and u > 13),
                key=lambda u: len([it for it in authored[u] if it.get("rung", 9) <= limit]))
    need = [it for it in authored[small] if it.get("rung") and it["rung"] <= limit]
    done = {}
    for it in need[:-1]:
        done.setdefault(str(it["rung"]), []).append(it["id"])
    cid = course["id"]
    page.evaluate("""([cid, n, done]) => {
      const k = "lang-research.progress." + cid;
      const p = JSON.parse(localStorage.getItem(k));
      p.units[n] = { state: "in-progress", lessonRead: true, done };
      p.currentUnit = n;
      p.sessions = {};
      localStorage.setItem(k, JSON.stringify(p));
    }""", [cid, small, done])
    last = need[-1]
    page.goto(f"{base}#/{units[small].get('slug')}/item/{last['id']}")
    page.reload()
    page.wait_for_selector(".drill-stage")
    answer_authored(page, [last])
    page.click(".drill-feedback .gate-btn")
    page.wait_for_selector(".drill-ok, .drill-no")
    page.goto(f"{base}#/")
    page.wait_for_selector(".roadmap")
    cls = page.get_attribute(f".unit[data-unit='{small}']", "class") or ""
    nxt = page.get_attribute(f".unit[data-unit='{small + 1}']", "class") or ""
    check("unit--done" in cls and ("unit--available" in nxt or "unit--done" in nxt),
          f"unit {small} unlocks the next once rungs 1–{limit} are all right", failures)
    stars = page.text_content(f".unit[data-unit='{small}'] .unit-stars") or ""
    check(stars.startswith("★" * limit), f"unit {small} tile shows {limit} stars ({stars})", failures)
    return 1


REVIEW_JS = r"""
async () => {
  const origin = window.location.origin;
  const { reviewUnits, reviewPlanItems } = await import(origin + "/engine/knowledge.js");
  const { buildSession } = await import(origin + "/engine/session.js");
  const { withSeed } = await import(origin + "/engine/exercise-types/util.js");
  const course = await (await fetch(origin + "/course.json")).json();
  const vocab = (await (await fetch(origin + "/vocab.json")).json()).items;
  const skills = {};
  for (let n = 13; n < 30; n++) skills[n] = { correct: 9, attempts: 10 };
  skills[18] = { correct: 1, attempts: 5 };
  delete skills[20];
  const order = withSeed("r", () => reviewUnits({ units: {}, skills }, Array.from({ length: 17 }, (_, i) => i + 13), 3));
  const ladder = [1, 2, 3, 4].map((r) => ({ id: "x." + r, rung: r, type: "mcq" }));
  const plan = [{ unit: 5, vocab: [], ladder, mastered: new Set(["x.1", "x.2"]), done: { 1: ["x.1"], 2: ["x.2"] } }];
  const rung = reviewPlanItems(plan, 1)[0].item.rung;
  const word = vocab.find((v) => v.unit === 24);
  const sets = new Set();
  for (const seed of ["a", "b", "c", "d", "e", "f"]) {
    const items = withSeed(seed, () => buildSession(course, [], { unitN: 40, vocabList: vocab, authored: [], features: { ...course.features, reviewItems: 1 },
      reviewPlan: [{ unit: 24, vocab: [word], ladder: [], mastered: new Set(), done: {} }] }));
    sets.add(items[0].options.slice().sort().join("|"));
  }
  return { order, rung, optionSets: sets.size };
}
"""


def run_review(page, url, vocab, authored, course_dir, failures):
    """Review covers every earlier unit (gaps first), mixes sentences, varies wrong options, credits the source unit."""
    r = page.evaluate(REVIEW_JS)
    check(r["order"][:2] == [20, 18], f"review picks the unpractised unit, then the weakest ({r['order']})", failures)
    check(r["rung"] == 3, f"a practised unit's sentence review goes one rung above its best ({r['rung']})", failures)
    check(r["optionSets"] > 1, f"review wrong options vary between sessions ({r['optionSets']} sets)", failures)

    course = json.loads((Path(course_dir) / "course.json").read_text(encoding="utf-8"))
    later = next(u for u in course["units"] if u["n"] == 40)
    base = url.split("#")[0]
    page.goto(f"{base}#/")
    plain = [u["n"] for u in course["units"] if u["n"] < 40 and not any(it.get("rung") for it in authored.get(u["n"], []))]
    page.evaluate("""([cid, plain]) => {
      const skills = {};
      for (const n of plain) skills[n] = { correct: 10, attempts: 10 };
      localStorage.setItem("lang-research.progress." + cid, JSON.stringify({
        schema: "progress-v1.json", courseId: cid, student: { name: "", forkRemote: "" }, currentUnit: 1,
        units: {}, knownSet: [], xp: 0, skills, updatedAt: null }));
    }""", [course["id"], plain])
    page.goto(f"{base}#/{later['slug']}")
    page.reload()
    page.wait_for_selector(".lesson-title")
    check(bool(page.query_selector(".warmup-unit")), "skipping ahead: the lesson suggests earlier units to warm up on", failures)
    page.click(".gate .gate-btn")
    page.wait_for_selector(".drill-stage")
    tags, credited = [], []
    while page.query_selector(".drill-review-tag"):
        tags.append(page.text_content(".drill-review-tag"))
        code = (page.text_content(".drill-item-code") or "").removeprefix("Item ")
        answer_current(page, vocab, 40, authored)
        page.click(".drill-feedback .gate-btn")
        page.wait_for_selector(".drill-feedback .gate-btn")
        if page.query_selector(".drill-ok") and "." in code:
            credited.append(code)
        page.click(".drill-feedback .gate-btn")
        page.wait_for_selector(".drill-stage, .drill-result")
    units = [int(re.search(r"Unit (\d+)", t).group(1)) for t in tags if re.search(r"Unit (\d+)", t)]
    check(len(tags) == (course.get("features") or {}).get("reviewItems", 2) and units and all(u < 40 for u in units),
          f"skipping ahead: review questions come from earlier units ({units})", failures)
    check(bool(credited), "review mixes in sentence-ladder items from earlier units", failures)
    stored = json.loads(page.evaluate("cid => localStorage.getItem('lang-research.progress.' + cid)", course["id"]))
    owners = {str(u): set(sum((stored["units"].get(str(u), {}).get("done", {}) or {}).values(), [])) for u in set(units)}
    check(any(c in ids for c in credited for ids in owners.values()), "a right review answer counts toward its own unit's ladder", failures)
    return 1


def run_type_harness(page, failures):
    results = page.evaluate(HARNESS_JS % {"type_ids": json.dumps(EXERCISE_TYPES)})
    for r in results:
        msg = f"{r['id']}: render->grade correct with right answer"
        check(r.get("ok", False), msg, failures)
        if not r.get("ok"):
            print(f"      error: {r.get('error', '?')}")
    duplicate_match = page.evaluate(DUPLICATE_MATCH_JS)
    check(
        duplicate_match.get("found") and duplicate_match.get("ok"),
        "match-by-line removes duplicate script forms",
        failures,
    )
    return len(results)


ACCESSIBILITY_JS = r"""
() => {
  const input = document.createElement("input");
  input.className = "hebrew-input";
  input.type = "text";
  document.body.appendChild(input);
  input.focus();
  const overlay = document.querySelector(".keyboard");
  const shown = !!(overlay && overlay.style.display === "");
  const keys = document.querySelectorAll(".kb-key");
  let inserted = false;
  if (keys.length) {
    keys[0].dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    inserted = input.value.length > 0;
  }
  const press = (ch) => {
    const k = Array.from(keys).find((x) => x.dataset.key === ch);
    if (k) k.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    return !!k;
  };
  input.value = "";
  const marks = ["ש", "\u05C1", " ", "ש", "\u05C2", "\u05BE"].map(press).every(Boolean);
  const typed = input.value;
  const named = Array.from(document.querySelectorAll(".kb-key--niqqud .kb-name"), (n) => n.textContent);
  const value = input.value;
  input.remove();
  return { shown, keyCount: keys.length, inserted, value, marks, typed, named };
}
"""


def run_accessibility(page, failures):
    page.focus(".unit[data-unit='1']")
    page.keyboard.press("Enter")
    page.wait_for_selector(".lesson-title")
    check(page.text_content(".lesson-title").strip().startswith("Unit 1"), "keyboard Enter opens unit 1 lesson", failures)
    page.click(".back")
    page.wait_for_selector(".roadmap")

    kb = page.evaluate(ACCESSIBILITY_JS)
    check(kb.get("shown"), "on-screen keyboard shows when a Hebrew input is focused", failures)
    check(kb.get("keyCount", 0) > 0, "on-screen keyboard has keys", failures)
    check(kb.get("inserted"), "on-screen keyboard key inserts text", failures)
    check(kb.get("marks") and kb.get("typed") == "שׁ שׂ־", f"shin dot, sin dot and maqqef keys type their marks ({kb.get('typed')!r})", failures)
    check("shin dot" in kb.get("named", []) and "qamets" in kb.get("named", []), "vowel keys carry their names", failures)
    return kb


def run_single_option(page, failures):
    res = page.evaluate(SINGLE_OPTION_JS)
    violations = res.get("violations", []) if res else None
    check(
        res is not None and not violations,
        f"no single-option MCQ/choice across {res.get('units') if res else '?'} units",
        failures,
    )
    for v in violations or []:
        print(f"  single-option violation unit {v['unit']} type {v['type']}: options={v['options']}")
    return len(violations or [])


def run_lesson_heading_check(page, failures):
    for n, wanted in ((10, ("Pause",)), (11, ("Metheg", "Maqqeph")), (12, ("Qere and Kethib", "The divine name"))):
        headings = page.evaluate(LESSON_HEADINGS_JS, n)
        for heading in wanted:
            check(heading in headings, f"Davidson unit {n} renders the {heading} section heading", failures)


def run_drill_keyboard(page, vocab, failures, authored=None):
    page.click(".unit[data-unit='1']")
    page.wait_for_selector(".lesson-title")
    page.click(".gate-btn")
    page.wait_for_selector(".drill-stage")

    qcount = 0
    while True:
        if page.query_selector(".drill-result"):
            break
        qcount += 1
        answer_current(page, vocab, 1, authored)
        page.click(".drill-feedback .gate-btn")  # Check
        page.wait_for_selector(".drill-feedback .gate-btn")
        before = page.text_content(".drill-progress").strip()
        page.keyboard.press("Enter")  # advance via keyboard, not a click
        page.wait_for_selector(".drill-stage, .drill-result")
        if not page.query_selector(".drill-result"):
            after = page.text_content(".drill-progress").strip()
            check(after != before, "Enter advanced to the next question", failures)

    result = page.text_content(".drill-result").strip()
    page.click(".gate-btn")
    page.wait_for_selector(".roadmap")
    return qcount, result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("course", help="course dir, e.g. courses/biblical-hebrew-davidson")
    ap.add_argument("--units", type=int, default=2, help="how many units to complete (1..N)")
    ap.add_argument("--port", type=int, default=8146)
    ap.add_argument(
        "--exercise-types",
        action="store_true",
        help="drive every registered exercise type (generate/render/grade) instead of the unit drill loop",
    )
    ap.add_argument(
        "--authored",
        action="store_true",
        help="drive authored-exercise items (render/collect/grade) and the session-mix contract",
    )
    ap.add_argument(
        "--accessibility",
        action="store_true",
        help="keyboard navigation + on-screen Hebrew keyboard input",
    )
    ap.add_argument(
        "--ladder",
        action="store_true",
        help="exercise ladder: rung order, pointed grading, typed English with self-check, unlock and stars",
    )
    ap.add_argument(
        "--routes",
        action="store_true",
        help="hash URLs, seeded sessions that resume after reload, item codes, per-block progress",
    )
    ap.add_argument(
        "--progress-ops",
        action="store_true",
        help="reset all, reset a unit, mark a unit done, mark an exercise done / not done",
    )
    ap.add_argument(
        "--keyboard",
        action="store_true",
        help="assert no single-option MCQ/choice across all units, and that Enter advances after checking",
    )
    args = ap.parse_args()

    vocab = load_vocab(args.course)
    authored = load_authored(args.course)
    proc, url = start_server(args.course, args.port)
    failures = []

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)
            page.wait_for_selector(".roadmap")
            page.evaluate("localStorage.clear()")
            page.reload()
            page.wait_for_selector(".roadmap")

            if args.exercise_types:
                print(f"=== exercise-type harness ({len(EXERCISE_TYPES)} types) ===")
                n = run_type_harness(page, failures)
                check(n == len(EXERCISE_TYPES), "harness returned a result per type", failures)
                browser.close()
            elif args.ladder:
                print("=== exercise ladder ===")
                check(run_ladder(browser, page, url, vocab, authored, args.course, failures) == 1,
                      "course has ladder items", failures)
                run_review(page, url, vocab, authored, args.course, failures)
                browser.close()
            elif args.routes:
                print("=== routes / sessions / block progress ===")
                check(run_routes(browser, page, url, vocab, authored, args.course, failures) == 1,
                      "course has authored items with blocks to route to", failures)
                browser.close()
            elif args.progress_ops:
                print("=== progress operations ===")
                check(run_progress_ops(page, url, authored, args.course, failures) == 1,
                      "progress operations ran", failures)
                browser.close()
            elif args.authored:
                print("=== authored-exercise harness ===")
                n = run_authored_harness(page, failures, _authored_units(args.course))
                check(n == len(AUTHORED_SAMPLES), "authored harness returned a result per sample", failures)
                shapes = run_course_shapes(page, authored, failures)
                print(f"  course item shapes checked: {shapes}")
                tips = run_drill_tips(page, authored, failures)
                run_parse_fields(page, authored, failures)
                run_wrong_feedback_layout(page, authored, failures)
                run_no_translit(page, failures)
                print(f"  hint/explain drill items checked: {tips}")
                browser.close()
            elif args.accessibility:
                print("=== accessibility harness ===")
                run_accessibility(page, failures)
                browser.close()
            elif args.keyboard:
                print("=== keyboard / single-option harness ===")
                run_single_option(page, failures)
                if page.evaluate("async () => (await (await fetch('/course.json')).json()).id") == "biblical-hebrew-davidson":
                    run_lesson_heading_check(page, failures)
                qcount, result = run_drill_keyboard(page, vocab, failures, authored)
                print(f"  keyboard drill unit 1: {qcount} questions, {result}")
                browser.close()
            else:
                for unit_n in range(1, args.units + 1):
                    print(f"=== unit {unit_n} ===")
                    qcount, result = run_drill(page, vocab, unit_n, authored)
                    print(f"  questions: {qcount}, result: {result}")
                    check(qcount > 0, f"unit {unit_n} drill had >0 questions", failures)
                    check(
                        "unit--done" in unit_classes(page, unit_n),
                        f"unit {unit_n} marked done",
                        failures,
                    )
                    next_exists = page.query_selector(f".unit[data-unit='{unit_n + 1}']")
                    if next_exists:
                        check(
                            "unit--available" in unit_classes(page, unit_n + 1)
                            or "unit--done" in unit_classes(page, unit_n + 1),
                            f"unit {unit_n + 1} unlocked",
                            failures,
                        )

            stored = None
            if not (args.exercise_types or args.authored or args.accessibility or args.keyboard or args.routes or args.ladder or args.progress_ops):
                with open(f"{args.course}/course.json", encoding="utf-8") as f:
                    cid = json.load(f)["id"]
                stored = page.evaluate("k => localStorage.getItem(k)", f"lang-research.progress.{cid}")
            browser.close()

        if stored is not None or (not (args.exercise_types or args.authored or args.accessibility or args.keyboard or args.routes or args.ladder or args.progress_ops)):
            progress = json.loads(stored or "{}")
            for unit_n in range(1, args.units + 1):
                state = progress.get("units", {}).get(str(unit_n), {}).get("state")
                check(state == "done", f"stored progress unit {unit_n} state=done (got {state!r})", failures)
            check(
                progress.get("currentUnit") == args.units + 1,
                f"stored progress currentUnit={args.units + 1} (got {progress.get('currentUnit')!r})",
                failures,
            )

    except ImportError:
        print("playwright not installed — run: .venv/bin/pip install playwright && "
              ".venv/bin/python -m playwright install chromium")
        sys.exit(2)
    finally:
        proc.terminate()
        proc.wait()

    if failures:
        print(f"\n{len(failures)} failure(s):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    if args.exercise_types:
        print(f"\nE2E PASS — exercise-type harness: {len(EXERCISE_TYPES)} types render+grade correctly")
    elif args.authored:
        print(f"\nE2E PASS — authored-exercise harness: {len(AUTHORED_SAMPLES)} items render+grade, session mix verified")
    elif args.accessibility:
        print("\nE2E PASS — accessibility harness: keyboard navigation + on-screen Hebrew keyboard")
    elif args.keyboard:
        print("\nE2E PASS — keyboard/single-option harness: Enter advances after checking; no single-option choices")
    elif args.routes:
        print("\nE2E PASS — routes: seeded URLs resume after reload, item codes, per-block progress")
    elif args.progress_ops:
        print("\nE2E PASS — progress operations: reset all, reset a unit, mark a unit or an exercise done")
    elif args.ladder:
        print("\nE2E PASS — ladder: rungs in order, pointed grading, English self-check, unlock and stars")
    else:
        print(f"\nE2E PASS — lessons 1..{args.units} complete, unit {args.units + 1} unlocked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
