#!/usr/bin/env python3
"""Turn the curated exwb Davidson exercises into course drills (ROADMAP P9-T6).

Reads `exwb/curated/davidson-*.json` (the hand-checked transcriptions) and the
block-to-unit map `build/_sources/davidson/exwb-units.json`, and writes
`authored/NN.json` (engine items) plus `exercises/NN.json` (raw scaffolds) for
every mapped unit. Held blocks are skipped. Output is deterministic.

Translation sentences are placed one by one (P12-T1): each goes to the first unit
that teaches all the grammar it uses, from `sentence-grammar.json` (tags per
sentence) and `grammar-units.json` (feature -> unit). Other items stay in their
block's unit.

    python build/exwb_to_authored.py --course courses/biblical-hebrew-davidson
    python build/exwb_to_authored.py --course courses/biblical-hebrew-davidson --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from davidson_ladder import RUNG_KEYS, RUNG_NAMES, PausalForms, clean_display, ladder

ROOT = Path(__file__).resolve().parent.parent
CURATED = ROOT / "exwb" / "curated"
MAP = ROOT / "build" / "_sources" / "davidson" / "exwb-units.json"
GRAMMAR = ROOT / "build" / "_sources" / "davidson" / "grammar-units.json"
TAGS = ROOT / "build" / "_sources" / "davidson" / "sentence-grammar.json"
PHRASES = ROOT / "build" / "_sources" / "davidson" / "indefinite-phrases.json"
RECOGNITION = ROOT / "build" / "_sources" / "davidson" / "recognition.json"
SENTENCE_SHAPES = ("en-he", "he-en")
GRAMMAR_ID = "introductoryhebr0000davi_w1b2"
KEY_ID = "keytoexercisesin0000mcfa"
NOTE = "Transcribed by hand from the scans and checked against the Key."

HEB = re.compile(r"[א-ת]")
LAT = re.compile(r"[A-Za-z]")
PAREN = re.compile(r"\(([^()]*)\)")


def is_english(text: str) -> bool:
    return len(LAT.findall(text)) > len(HEB.findall(text))


def clean_hebrew(text: str) -> str:
    text = PAREN.sub(lambda m: m.group(0) if HEB.search(m.group(1)) and not LAT.search(m.group(1)) else " ", text)
    text = LAT.sub("", text)
    text = re.sub(r"[.,]+(?=\s|$)", " ", text)
    return re.sub(r"\s+", " ", text).strip(" ;")


def hebrew_variants(answer: str) -> list[str]:
    out: list[str] = []

    def add(s: str) -> None:
        s = clean_hebrew(s)
        if s and HEB.search(s) and s not in out:
            out.append(s)

    sub = re.search(r"\(or ([^()]*?) for ([^()]*?)\)", answer)
    if sub:
        base = answer[: sub.start()] + answer[sub.end():]
        add(base)
        add(base.replace(sub.group(2).strip(), sub.group(1).strip()))
        return out
    inline = re.search(r"\(or,?([^()]*(?:\([^()]*\)[^()]*)*)\)", answer)
    if inline:
        base = (answer[: inline.start()] + answer[inline.end():]).strip()
        add(base)
        alt = "" if inline.group(1).startswith(",") else clean_hebrew(inline.group(1))
        if alt and HEB.search(alt):
            words = answer[: inline.start()].split()
            if " " in alt or not words:
                add(alt)
            else:
                add(" ".join(words[:-1] + [alt]) + " " + answer[inline.end():])
        return out
    pause = re.search(r"\(in pause ([^()]*)\)", answer)
    if pause:
        add(answer[: pause.start()])
        add(pause.group(1))
        return out
    if " or " in answer:
        for part in answer.split(" or "):
            add(part)
        return out
    add(answer)
    return out


def leaf_links(note: str, grammar_offset: int, key_offset: int) -> dict:
    links = {}
    g = re.search(r"grammar pp?\. (\d+)", note)
    k = re.search(r"key pp?\. (\d+)", note)
    if g:
        n = int(g.group(1)) + grammar_offset
        links["promptUrl"] = f"https://archive.org/details/{GRAMMAR_ID}/page/n{n}/mode/1up"
        links["promptImageUrl"] = f"https://archive.org/download/{GRAMMAR_ID}/page/n{n}.jpg"
    if k:
        n = int(k.group(1)) + key_offset
        links["answerUrl"] = f"https://archive.org/details/{KEY_ID}/page/n{n}/mode/1up"
        links["answerImageUrl"] = f"https://archive.org/download/{KEY_ID}/page/n{n}.jpg"
    return links


def section_label(stem: str) -> str:
    m = re.match(r"davidson-s(\d+)([ab]?)$", stem)
    return f"§{int(m.group(1))}{m.group(2)}" if m else stem


def rng_for(*parts: str) -> random.Random:
    return random.Random(int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:12], 16))


def pick_options(answer: str, pool: list[str], rng: random.Random, first: list[str] | None = None) -> list[str]:
    options = [answer]
    for d in first or []:
        if d and d not in options:
            options.append(d)
    rest = [p for p in dict.fromkeys(pool) if p not in options]
    rng.shuffle(rest)
    options += rest[: max(0, 4 - len(options))]
    rng.shuffle(options)
    return options


FORM_RE = re.compile(r"^(?P<word>\S+) \((?P<gloss>.*)\) → (?P<form>.+)$")
FORM_WORDS = {"cstr.": "construct", "abs.": "absolute", "sing.": "singular", "plur.": "plural",
              "dual": "dual"}


def split_form_prompt(prompt: str) -> tuple[str, str, str] | None:
    m = FORM_RE.match(prompt.strip())
    if not m:
        return None
    form = " ".join(FORM_WORDS.get(w, w) for w in m.group("form").split())
    return m.group("word"), m.group("gloss"), form


PARSE_FIELDS = [
    ("stem", "Stem", ["Qal", "Niph'al", "Pi'el", "Pu'al", "Hithpa'el", "Hiph'il", "Hoph'al", "Po'lel"]),
    ("form", "Form", ["perfect", "imperfect", "imperative", "jussive", "cohortative", "participle",
                      "infinitive construct", "infinitive absolute"]),
    ("person", "Person", ["1", "2", "3"]),
    ("gender", "Gender", ["masc.", "fem."]),
    ("number", "Number", ["sing.", "plur.", "dual"]),
    ("state", "State", ["absolute", "construct"]),
]
STEM_TOKENS = [("Hithpa", "Hithpa'el"), ("Hoph", "Hoph'al"), ("Hiph", "Hiph'il"), ("Niph", "Niph'al"),
               ("Po'lel", "Po'lel"), ("Pu", "Pu'al"), ("Pi", "Pi'el"), ("Qal", "Qal")]
FORM_TOKENS = [(r"\binf\.? cstr\b|\bcstr\. inf\b", "infinitive construct"),
               (r"\binf\.? abs\b", "infinitive absolute"), (r"\bimpf\b", "imperfect"),
               (r"\bpf\b", "perfect"), (r"\bptc\b", "participle"), (r"\bimper(?:at)?\b", "imperative"),
               (r"\bjussive\b", "jussive"), (r"\bcohortative\b", "cohortative")]


def parse_tokens(text: str) -> dict:
    out: dict = {}
    m = re.search(r"\bof [\u05d0-\u05ea]", text)
    if m:
        text = text[: m.start()]
    t = f" {text} "
    persons = re.findall(r"(?<![§\d])\b([123])\b(?: or ([123])\b)?(?=\s*(?:sing|s\.|plur|pl\.|masc|fem|m\.|f\.|c\.))", t)
    if persons:
        a, b = persons[0]
        out["person"] = [a] + ([b] if b else [])
    if re.search(r"\b(masc|m)\.", t):
        out["gender"] = "masc."
    if re.search(r"\b(fem|f)\.", t):
        out["gender"] = "fem."
    if re.search(r"\b(sing|s)\.", t):
        out["number"] = "sing."
    if re.search(r"\b(plur|pl)\b", t):
        out["number"] = "plur."
    if re.search(r"\bdual\b", t):
        out["number"] = "dual"
    for pat, name in FORM_TOKENS:
        if re.search(pat, t):
            out["form"] = name
            break
    if re.search(r"\bcstr\b", t) and out.get("form") != "infinitive construct":
        out["state"] = "construct"
    for token, name in STEM_TOKENS:
        if re.search(r"(?<![A-Za-z'])" + re.escape(token) + r"(?![a-z])", t):
            out["stem"] = name
            break
    return out


def expand_person(reading: dict) -> list[dict]:
    persons = reading.pop("person", None)
    if not persons:
        return [reading]
    return [{**reading, "person": p} for p in persons]


def parse_readings(item: dict) -> list[dict]:
    data = dict(item["data"]["parse"])
    alt = data.pop("alt", None)
    closed = {k for k, _, _ in PARSE_FIELDS} | {"root"}
    primary = {k: v for k, v in data.items() if k in closed}
    from_text = parse_tokens(item["answer"])
    for key in ("person", "gender", "number"):
        if key not in primary and key in from_text:
            primary[key] = from_text[key]
    if isinstance(primary.get("person"), str):
        primary["person"] = [primary["person"]]
    readings = expand_person(primary)
    if alt:
        other = parse_tokens(alt)
        if other:
            inherit = ["root", "stem"]
            if other.get("form") == primary.get("form"):
                inherit += ["gender", "number", "state"]
            for key in inherit:
                if key not in other and key in primary:
                    other[key] = primary[key]
            readings += expand_person(other)
    unique = []
    for r in readings:
        if r not in unique:
            unique.append(r)
    return unique


def parse_form_item(item: dict, block_roots: list[str], rng: random.Random) -> dict | None:
    readings = parse_readings(item)
    keys = {k for r in readings for k in r}
    fields = []
    for key, label, options in PARSE_FIELDS:
        if key in keys:
            fields.append({"key": key, "label": label, "options": options})
    if "root" in keys:
        root = readings[0].get("root")
        if root:
            others = [r for r in dict.fromkeys(block_roots) if r != root]
            rng.shuffle(others)
            options = [root] + others[:3]
            rng.shuffle(options)
            fields.append({"key": "root", "label": "Root", "options": options, "isScript": True})
    if not fields:
        return None
    return {
        "type": "parse-form",
        "prompt": "Parse this form",
        "stimulus": item["prompt"],
        "stimulusIsScript": True,
        "fields": fields,
        "readings": readings,
    }


def classify(item: dict, correction: bool) -> str:
    if "→" in item["prompt"] and not is_english(item["answer"]):
        return "he-form"
    if is_english(item["prompt"]):
        return "en-he"
    if is_english(item["answer"]):
        return "parse" if "parse" in (item.get("data") or {}) else "he-en"
    return "correct-pointing" if correction else "he-form"


PROMPTS = {
    "en-he": "Translate into Hebrew (pointing optional)",
    "he-en": "Choose the translation",
    "parse": "Parse this form",
    "correct-pointing": "This word is mispointed. Choose the correct form",
    "he-form": "Choose the form asked for",
}


OTHER_RUNGS = {"parse": (3, "parse", "Parse"), "he-form": (2, "form", "Choose the form"),
               "correct-pointing": (2, "point", "Correct the pointing")}


def sentence_pair(it: dict, shape: str) -> tuple[list[str], str, str | None, str | None]:
    """(accepted Hebrew forms, English, Hebrew to translate at rung 4, hint) for a sentence."""
    if shape == "en-he":
        return hebrew_variants(it["answer"]), clean_display(it["prompt"]), None, None
    pointed = (it.get("data") or {}).get("pointed")
    shown = pointed or it["prompt"]
    forms = [clean_hebrew(f) for f in re.split(r"\s*;\s*", shown) if clean_hebrew(f)]
    hint = f"With vowel points: {pointed}" if pointed else None
    return forms, clean_display(it["answer"]), (it["prompt"] if pointed else None), hint


def build_block(stem: str, data: dict, cfg: dict, pausal: PausalForms) -> list[dict]:
    correction = stem in cfg.get("correctionBlocks", [])
    label = section_label(stem)
    links = leaf_links(data.get("note", ""), cfg["grammarLeafOffset"], cfg["keyLeafOffset"])
    items = data["items"]
    shapes = [classify(it, correction) for it in items]
    pools: dict[tuple[str, str], list[str]] = defaultdict(list)
    for it, shape in zip(items, shapes):
        pools[(it["part"], shape)].append(it["answer"])
        pools[("*", shape)].append(it["answer"])

    block_roots = [(it.get("data") or {}).get("parse", {}).get("root") for it in items]
    block_roots = [r for r in block_roots if r]
    english_pool: dict[str, list[str]] = defaultdict(list)
    for it, shape in zip(items, shapes):
        if shape == "en-he":
            english_pool[it["part"]].append(clean_display(it["prompt"]))
        elif shape == "he-en":
            english_pool[it["part"]].append(clean_display(it["answer"]))
    block = stem.removeprefix("davidson-")
    block_label = "Davidson §" + str(int(re.sub(r"[a-z]$", "", stem.removeprefix("davidson-s"))))
    out_items = []
    for it, shape in zip(items, shapes):
        ref = f"{label} {it['part']} {it['num']}"
        base = f"{block}-{it['part']}{it['num']}"
        source = {
            "citation": f"Davidson, An Introductory Hebrew Grammar (22nd ed., 1923), exercise {ref}; "
                        "McFadyen, Key to the Exercises (1924)",
            **links,
            "exwb": f"{stem}#{it['part']}{it['num']}",
            "note": NOTE,
        }
        rng = rng_for(stem, it["part"], it["num"])
        common = {"block": block, "blockLabel": block_label, "shape": shape, "src": base}
        if it.get("explain"):
            common["explain"] = it["explain"]
        if shape in ("en-he", "he-en"):
            hebrew, english, reading, hint = sentence_pair(it, shape)
            if not hebrew:
                continue
            pool = english_pool[it["part"]] + [e for p, es in english_pool.items() if p != it["part"] for e in es]
            made = ladder(base, hebrew, english, pool, shape, rng, pausal, common, reading, hint or it.get("hint"))
        else:
            made = []
            parsed = parse_form_item(it, block_roots, rng) if shape == "parse" else None
            if parsed:
                out = parsed
            else:
                pool = pools[(it["part"], shape)]
                if len(set(pool)) < 4:
                    pool = pool + pools[("*", shape)]
                prompt, stimulus, first = PROMPTS[shape], it["prompt"], None
                if shape == "correct-pointing":
                    first = [it["prompt"]]
                form = split_form_prompt(it["prompt"]) if shape == "he-form" else None
                if form:
                    word, gloss, wanted = form
                    prompt = f"Choose the {wanted} of this word ({gloss})"
                    stimulus = word
                    siblings = [o["answer"] for o in items
                                if o is not it and (split_form_prompt(o["prompt"]) or ("",))[0] == word]
                    first = siblings + [word]
                options = pick_options(it["answer"], pool, rng, first)
                if len(options) < 2:
                    continue
                out = {
                    "type": "mcq",
                    "prompt": prompt,
                    "stimulus": stimulus,
                    "stimulusIsScript": True,
                    "options": options,
                    "answer": it["answer"],
                    "optionIsScript": shape in ("correct-pointing", "he-form"),
                }
            rung, key, rung_label = OTHER_RUNGS[shape]
            out = {"id": f"{base}.{key}", "rung": rung, "rungLabel": rung_label, **out, **common}
            if it.get("hint"):
                out["hint"] = it["hint"]
            if out["type"] == "parse-form" and "explain" not in out:
                out["explain"] = f"Key: {it['answer']}"
            pointed = (it.get("data") or {}).get("pointed")
            if pointed and "hint" not in out:
                out["hint"] = f"With vowel points: {pointed}"
            if it.get("data"):
                out["data"] = it["data"]
            made = [out]
        out_items.append({
            "ref": source["exwb"], "base": base, "shape": shape, "source": source, "items": made,
            "raw": {"typeGuess": made[0]["type"], "confidence": 1.0, "prompt": made[0]["prompt"],
                    "body_raw": it["prompt"], "answer_raw": it["answer"]},
        })
    return out_items


def dump(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def sentence_units() -> dict[str, int]:
    grammar = json.loads(GRAMMAR.read_text(encoding="utf-8"))
    units = {k: v["unit"] for k, v in grammar["features"].items()}
    tags = json.loads(TAGS.read_text(encoding="utf-8"))["sentences"]
    out = {}
    for ref, feats in tags.items():
        unknown = [f for f in feats if f not in units]
        if unknown:
            sys.exit(f"{ref}: unknown grammar feature(s) {unknown} in {TAGS.relative_to(ROOT)}")
        out[ref] = max([grammar["floor"]] + [units[f] for f in feats])
    return out


def load_blocks(cfg: dict) -> list[tuple[str, dict]]:
    held = set(cfg.get("held", []))
    blocks = []
    for path in sorted(CURATED.glob("davidson-*.json")):
        stem = path.stem
        if stem in held:
            continue
        if stem not in cfg["blocks"]:
            sys.exit(f"{stem}: not held and not mapped in {MAP.relative_to(ROOT)}")
        blocks.append((stem, json.loads(path.read_text(encoding="utf-8"))))
    missing = set(cfg["blocks"]) - {p.stem for p in CURATED.glob("davidson-*.json")}
    if missing:
        sys.exit(f"mapped blocks with no curated file: {sorted(missing)}")
    return blocks


def pausal_forms(cfg: dict, blocks: list[tuple[str, dict]]) -> PausalForms:
    sentences = []
    for stem, data in blocks:
        correction = stem in cfg.get("correctionBlocks", [])
        for it in data["items"]:
            shape = classify(it, correction)
            if shape in SENTENCE_SHAPES:
                sentences += sentence_pair(it, shape)[0]
    return PausalForms(sentences)


def build(cfg: dict) -> tuple[dict[int, dict], Counter]:
    units: dict[int, dict] = defaultdict(lambda: {"items": [], "sources": {}, "raw": []})
    shapes: Counter = Counter()
    placed = sentence_units()
    blocks = load_blocks(cfg)
    pausal = pausal_forms(cfg, blocks)
    for stem, data in blocks:
        unit = cfg["blocks"][stem]["unit"]
        for entry in build_block(stem, data, cfg, pausal):
            target = unit
            if entry["shape"] in SENTENCE_SHAPES:
                if entry["ref"] not in placed:
                    sys.exit(f"{entry['ref']}: sentence has no grammar tags in {TAGS.relative_to(ROOT)}")
                target = placed[entry["ref"]]
            u = units[target]
            u["items"] += entry["items"]
            u["sources"][entry["base"]] = entry["source"]
            u["raw"].append(entry["raw"])
            shapes[entry["shape"]] += 1
    for unit, entry in phrase_entries(cfg, dict(blocks), pausal):
        u = units[unit]
        u["items"] += entry["items"]
        u["sources"][entry["base"]] = entry["source"]
        u["raw"].append(entry["raw"])
        shapes["phrase"] += 1
    for unit, entry in recognition_entries(cfg):
        u = units[unit]
        u["items"] += entry["items"]
        u["sources"][entry["base"]] = entry["source"]
        u["raw"].append(entry["raw"])
        shapes["recognition"] += 1
    return units, shapes


def phrase_entries(cfg: dict, blocks: dict[str, dict], pausal: PausalForms) -> list[tuple[int, dict]]:
    """Article-less phrases (indefinite-phrases.json) as ladder items in the units before the article."""
    phrases = json.loads(PHRASES.read_text(encoding="utf-8"))["phrases"]
    by_stem: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for ph in phrases:
        stem, pn = ph["from"].split("#")
        if stem not in blocks or not any(f"{i['part']}{i['num']}" == pn for i in blocks[stem]["items"]):
            sys.exit(f"{ph['from']}: no such exercise ({PHRASES.relative_to(ROOT)})")
        by_stem[(stem, ph["unit"])].append({**ph, "part": pn[0], "num": pn[1:] + "i"})
    out = []
    for (stem, _), group in by_stem.items():
        synth = {"note": blocks[stem].get("note", ""),
                 "items": [{"part": g["part"], "num": g["num"], "prompt": "; ".join(g["hebrew"]),
                            "answer": g["english"]} for g in group]}
        units = {f"{g['part']}{g['num']}": g["unit"] for g in group}
        for entry in build_block(stem, synth, cfg, pausal):
            ref = entry["source"]["exwb"].removesuffix("i")
            entry["source"]["citation"] = entry["source"]["citation"].replace(
                "exercise ", "adapted (article removed) from exercise ").replace(f"{entry['base'][-1]};", ";", 1)
            del entry["source"]["exwb"]
            entry["source"]["adaptedFrom"] = ref
            for item in entry["items"]:
                item["shape"] = "phrase"
            out.append((units[entry["base"].split("-", 1)[1]], entry))
    return out


def rung_item(base: str, common: dict, rung: int, body: dict) -> dict:
    return {"id": f"{base}.{RUNG_KEYS[rung]}", "rung": rung, "rungLabel": RUNG_NAMES[rung], **body, **common}


def recognition_entries(cfg: dict) -> list[tuple[int, dict]]:
    """Recognition questions (recognition.json) for the script units: true/false, choose, and a typed answer."""
    data = json.loads(RECOGNITION.read_text(encoding="utf-8"))["units"]
    out = []
    for unit_key, spec in sorted(data.items(), key=lambda kv: int(kv[0])):
        unit = int(unit_key)
        for n, q in enumerate(spec["questions"], start=1):
            base = f"r{unit:02d}-{n}"
            rng = random.Random(base)
            script = q.get("script", False)
            common = {"block": f"r{unit:02d}", "blockLabel": "Recognition", "shape": "recognition", "src": base}

            truth = rng.random() < 0.5
            options = [q["answer"]] + q["wrong"]
            rng.shuffle(options)
            items = [
                rung_item(base, common, 1, {"type": "true-false", "prompt": "True or false?", "stimulus": q["stimulus"],
                         "stimulusIsScript": True, "statement": q["claim"].format(x=q["answer"] if truth else q["wrong"][0]),
                         "answer": truth, "expected": q["claim"].format(x=q["answer"])}),
                rung_item(base, common, 2, {"type": "mcq", "prompt": q["prompt"], "stimulus": q["stimulus"], "stimulusIsScript": True,
                         "options": options, "answer": q["answer"], "optionIsScript": script}),
            ]
            if q.get("typed"):
                body = {"type": "translate-phrase", "prompt": q["typed"]["prompt"], "stimulus": q["stimulus"],
                        "stimulusIsScript": True, "accepted": q["typed"]["accepted"], "answerIsScript": True}
                if q["typed"].get("pointing"):
                    body["pointing"] = "required"
                items.append(rung_item(base, common, 3, body))
            source = {"citation": "Written for this course on Davidson, An Introductory Hebrew Grammar "
                                  f"(22nd ed., 1923), §{spec['section']}",
                      **leaf_links(f"grammar p. {spec['page']}", cfg["grammarLeafOffset"], 0)}
            out.append((unit, {"base": base, "source": source, "items": items,
                               "raw": {"typeGuess": "mcq", "confidence": 1.0, "prompt": q["prompt"],
                                       "body_raw": q["stimulus"], "answer_raw": q["answer"]}}))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--course", required=True)
    ap.add_argument("--check", action="store_true", help="fail if the course files are out of date")
    args = ap.parse_args()
    course = Path(args.course)
    cfg = json.loads(MAP.read_text(encoding="utf-8"))
    units, shapes = build(cfg)

    wanted: dict[Path, str] = {}
    ladder_index = {}
    for unit, u in sorted(units.items()):
        name = f"{unit:02d}.json"
        wanted[course / "authored" / name] = dump(
            {"schema": "authored-exercises-v1.json", "unit": unit, "sources": u["sources"], "items": u["items"]})
        raw = [{"unit": unit, "n": i, **r} for i, r in enumerate(u["raw"], start=1)]
        wanted[course / "exercises" / name] = dump(
            {"schema": "workbook-exercises-v1.json", "unit": unit, "items": raw})
        rungs = Counter(str(it["rung"]) for it in u["items"] if "rung" in it)
        ladder_index[str(unit)] = dict(sorted(rungs.items()))
    wanted[course / "authored" / "ladder.json"] = dump(
        {"note": "Items per ladder rung per unit (rung 1 true/false … 5 translate with vowel points); "
                 "written by build/exwb_to_authored.py.", "units": ladder_index})
    existing = {p for d in ("authored", "exercises") for p in (course / d).glob("[0-9][0-9].json")}
    existing |= {p for p in [course / "authored" / "ladder.json"] if p.exists()}
    stale = sorted(existing - set(wanted))
    changed = sorted(p for p, text in wanted.items()
                     if not p.is_file() or p.read_text(encoding="utf-8") != text)

    total = sum(len(u["items"]) for u in units.values())
    rung_total = Counter(str(it.get("rung")) for u in units.values() for it in u["items"])
    summary = (f"{sum(shapes.values())} exercises -> {total} items in {len(units)} units from {len(cfg['blocks'])} blocks; "
               f"shapes: {dict(sorted(shapes.items()))}; rungs: {dict(sorted(rung_total.items()))}")
    if args.check:
        if stale or changed:
            for p in changed + stale:
                print(f"out of date: {p.relative_to(course)}")
            return 1
        print(f"up to date: {summary}")
        return 0
    for p in stale:
        p.unlink()
    for p in changed:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(wanted[p], encoding="utf-8")
    print(f"wrote {len(changed)} file(s), removed {len(stale)}: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
