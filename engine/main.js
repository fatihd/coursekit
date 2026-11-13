import { loadProgress, saveProgress, exportProgress, importProgress, resetProgress } from "./store.js";
import { renderRoadmap } from "./views/roadmap.js";
import { renderLesson } from "./views/lesson.js";
import { renderDrill } from "./views/drill.js";
import { PASS_MARK, renderTest } from "./views/test.js";
import { buildSession } from "./session.js";
import { buildRecap, reviewUnits, weakUnits } from "./knowledge.js";
import { initKeyboard } from "./keyboard.js";
import { script, setScript } from "./script.js";
import { newSeed, shuffle, withSeed } from "./exercise-types/util.js";
import { WORD_RUNG_COUNT, openRung, warmupWords, wordItemsFor, wordSummary, wordsSession } from "./words.js";

const ctx = {
  base: "",
  course: null,
  vocab: {},
  vocabList: [],
  progress: null,
  root: null,
  ladder: {},
  ladderExtra: {},
};

const RUNG_NAMES = { 1: "True or false", 2: "Choose", 3: "Fill in", 4: "Translate", 5: "Translate with vowel points" };

function rungName(n) {
  return n === 5 ? `Translate with ${script().marks}` : RUNG_NAMES[n];
}

const authoredCache = new Map();

async function fetchJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`failed to load ${path}: ${res.status}`);
  return res.json();
}

function commit() {
  saveProgress(ctx.course.id, ctx.progress);
}

function slugOf(n) {
  const u = ctx.course.units.find((x) => x.n === n);
  return (u && u.slug) || `u${n}`;
}

function unitBySlug(slug) {
  return ctx.course.units.find((u) => u.slug === slug || `u${u.n}` === slug);
}

function routeFor(view, n, extra = {}) {
  if (view === "roadmap" || !n) return "#/";
  const base = `#/${slugOf(n)}`;
  if (view === "lesson") return base;
  if (view === "drill") return extra.seed ? `${base}/drill/${extra.seed}/${extra.pos || 1}` : `${base}/drill`;
  if (view === "block") return extra.seed ? `${base}/block/${extra.block}/${extra.seed}/${extra.pos || 1}` : `${base}/block/${extra.block}`;
  if (view === "rung") return extra.seed ? `${base}/rung/${extra.rung}/${extra.seed}/${extra.pos || 1}` : `${base}/rung/${extra.rung}`;
  if (view === "item") return `${base}/item/${extra.item}`;
  if (view === "test") return extra.seed ? `${base}/test/${extra.seed}` : `${base}/test`;
  if (view === "words") {
    const r = extra.rung || 0;
    return extra.seed ? `${base}/words/${r}/${extra.seed}/${extra.pos || 1}` : r ? `${base}/words/${r}` : `${base}/words`;
  }
  return base;
}

function navigate(view, n, extra) {
  const hash = routeFor(view, n, extra);
  if (location.hash === hash) route();
  else location.hash = hash;
}

function setHash(hash) {
  if (location.hash !== hash) history.replaceState(null, "", hash);
}

let routeSeq = 0;

function testRoute(scope, part, seed) {
  const base = scope === "part" ? `#/test/part/${part}` : "#/test/final";
  return seed ? `${base}/${seed}` : base;
}

function route() {
  routeSeq += 1;
  const [slug, kind, a, b, c] = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  if (slug === "test" && (kind === "part" || kind === "final")) {
    return loadTest(kind === "part" ? { scope: "part", part: Number(a), seed: b } : { scope: "final", seed: a });
  }
  const unit = slug ? unitBySlug(slug) : null;
  if (!unit) return showRoadmap();
  if (!kind) return loadLesson(unit.n);
  if (kind === "drill") return loadDrill(unit.n, { seed: a, pos: b });
  if (kind === "block") return loadDrill(unit.n, { block: a, seed: b, pos: c });
  if (kind === "rung") return loadDrill(unit.n, { rung: Number(a), seed: b, pos: c });
  if (kind === "item") return loadDrill(unit.n, { item: a });
  if (kind === "test") return loadTest({ scope: "unit", unit: unit.n, seed: a });
  if (kind === "words") return loadWords(unit.n, { rung: Number(a) || 0, seed: b, pos: c });
  return loadLesson(unit.n);
}

function showRoadmap() {
  renderRoadmap(ctx.root, ctx.course, ctx.progress, navigate, {
    stars: (n) => ladderStars(n),
    wordStar: (n) => wordStar(n),
    tests: ctx.features && ctx.features.tests
      ? { part: (n) => testRoute("part", n), final: testRoute("final"), last: (scope, key) => lastTest(scope, key) }
      : null,
    onExport: () => exportProgress(ctx.course.id, ctx.progress),
    onReset: () => {
      ctx.progress = resetProgress(ctx.course.id);
    },
    onImport: async (file) => {
      const r = await importProgress(ctx.course.id, ctx.progress, file);
      if (r.ok) {
        ctx.progress = r.progress;
        commit();
      }
      return r;
    },
  });
}

async function authoredFor(unitN) {
  if (!authoredCache.has(unitN)) {
    let items = [];
    try {
      const data = await fetchJSON(`${ctx.base}authored/${String(unitN).padStart(2, "0")}.json`);
      const sources = data.sources || {};
      items = (data.items || []).map((it) => (it.src && sources[it.src] && !it.source ? { ...it, source: sources[it.src] } : it));
    } catch {
      items = [];
    }
    authoredCache.set(unitN, items);
  }
  return authoredCache.get(unitN);
}

function doneIds(unitN) {
  return (ctx.progress.units[unitN] || {}).done || {};
}

function masteredIn(unitN) {
  return new Set(Object.values(doneIds(unitN)).flat());
}

function blockSummary(unitN, authored) {
  const mastered = masteredIn(unitN);
  const blocks = new Map();
  for (const it of authored) {
    if (!it.block) continue;
    const b = blocks.get(it.block) || { id: it.block, label: it.blockLabel || it.block, total: 0, done: 0 };
    b.total += 1;
    if (mastered.has(it.id)) b.done += 1;
    blocks.set(it.block, b);
  }
  return [...blocks.values()].map((b) => ({ ...b, href: routeFor("block", unitN, { block: b.id }) }));
}

function rungKey(item) {
  return `${item.extra ? "x" : ""}${item.rung || 0}`;
}

function extraNeeded(unitN, rung) {
  const core = (ctx.ladder[String(unitN)] || {})[String(rung)] || 0;
  const extra = (ctx.ladderExtra[String(unitN)] || {})[String(rung)] || 0;
  const target = ctx.features && ctx.features.ladderTarget;
  return target ? Math.min(extra, Math.max(0, target - core)) : extra;
}

function extraDone(unitN, rung) {
  return (doneIds(unitN)[`x${rung}`] || []).length;
}

function satisfiedIn(unitN, authored) {
  const out = masteredIn(unitN);
  for (const it of authored) {
    if (it.extra && it.rung && extraDone(unitN, it.rung) >= extraNeeded(unitN, it.rung)) out.add(it.id);
  }
  return out;
}

function ladderSummary(unitN, authored) {
  const mastered = masteredIn(unitN);
  const rungs = new Map();
  for (const it of authored) {
    if (!it.rung) continue;
    const r = rungs.get(it.rung) || { rung: it.rung, label: rungName(it.rung) || `Rung ${it.rung}`, total: 0, done: 0, pool: 0 };
    if (it.extra) r.pool += 1;
    else {
      r.total += 1;
      if (mastered.has(it.id)) r.done += 1;
    }
    rungs.set(it.rung, r);
  }
  return [...rungs.values()].sort((a, b) => a.rung - b.rung).map((r) => {
    const need = extraNeeded(unitN, r.rung);
    return {
      ...r,
      total: r.total + need,
      done: r.done + Math.min(need, extraDone(unitN, r.rung)),
      more: r.pool - need,
      href: routeFor("rung", unitN, { rung: r.rung }),
    };
  });
}

function ladderComplete(unitN, authored) {
  const limit = (ctx.features && ctx.features.unlockRung) || 99;
  const satisfied = satisfiedIn(unitN, authored);
  const needed = authored.filter((it) => it.rung && it.rung <= limit);
  return needed.length > 0 && needed.every((it) => satisfied.has(it.id));
}

function ladderStars(unitN) {
  const totals = ctx.ladder[String(unitN)];
  if (!totals) return null;
  const done = doneIds(unitN);
  return Object.keys(totals).sort().map((r) => (done[r] || []).length >= totals[r] && extraDone(unitN, r) >= extraNeeded(unitN, r));
}

function unitWords(unitN) {
  return ctx.vocabList.filter((v) => v.unit === unitN && v.scriptForm && v.gloss);
}

function wordDistractors(unitN) {
  return ctx.vocabList.filter((v) => v.unit <= unitN && v.unit >= unitN - 5 && v.unit !== unitN);
}

function wordsDone(unitN) {
  return (ctx.progress.units[unitN] || {}).words || {};
}

function wordStar(unitN) {
  if (!(ctx.features && ctx.features.wordLadder)) return null;
  const words = unitWords(unitN);
  if (!words.length) return null;
  return openRung(words, wordsDone(unitN)) === null;
}

function recordWords(unitN, item, res) {
  const ids = item.type === "match-by-line" ? res.words || [] : res.correct ? item.wordIds || [] : [];
  if (!ids.length) return;
  const u = ctx.progress.units[unitN] || {};
  const words = { ...(u.words || {}) };
  const key = String(item.wordRung);
  words[key] = [...new Set([...(words[key] || []), ...ids])];
  ctx.progress.units[unitN] = { ...u, words };
}

function reviewCandidates(unitN) {
  return ctx.course.units.map((u) => u.n)
    .filter((n) => n < unitN && (ctx.vocabList.some((v) => v.unit === n) || ctx.ladder[String(n)]));
}

async function buildReviewPlan(unitN, seed) {
  if (!(ctx.features && ctx.features.diagnostics)) return null;
  const units = withSeed(`${seed}:review`, () => reviewUnits(ctx.progress, reviewCandidates(unitN), 3));
  const plan = [];
  for (const n of units) {
    const authored = ctx.ladder[String(n)] ? await authoredFor(n) : [];
    plan.push({
      unit: n,
      vocab: ctx.vocabList.filter((v) => v.unit === n),
      ladder: authored.filter((it) => it.rung),
      mastered: masteredIn(n),
      done: doneIds(n),
    });
  }
  return plan;
}

function sessionKey(unitN, block) {
  return block ? `${unitN}:${block}` : String(unitN);
}

async function loadLesson(unitN) {
  const seq = routeSeq;
  const lesson = await fetchJSON(`${ctx.base}units/${String(unitN).padStart(2, "0")}.json`);
  const unit = ctx.course.units.find((u) => u.n === unitN);
  const authored = await authoredFor(unitN);
  if (seq !== routeSeq) return;
  const saved = (ctx.progress.sessions || {})[sessionKey(unitN)];

  renderLesson(ctx.root, {
    course: ctx.course,
    vocab: ctx.vocab,
    progress: ctx.progress,
    navigate,
    features: ctx.features,
    recap: buildRecap(ctx.course, ctx.progress, unitN),
    warmup: weakUnits(ctx.progress, unitN, 3, reviewCandidates(unitN)),
    blocks: blockSummary(unitN, authored),
    words: ctx.features && ctx.features.wordLadder && unitWords(unitN).length
      ? { rows: wordSummary(unitWords(unitN), wordsDone(unitN)).map((r) => ({ ...r, href: routeFor("words", unitN, { rung: r.rung }) })), href: routeFor("words", unitN) }
      : null,
    ladder: ladderSummary(unitN, authored),
    unlockRung: ctx.features && ctx.features.unlockRung,
    ladderTarget: ctx.features && ctx.features.ladderTarget,
    resume: saved ? { href: routeFor("drill", unitN, saved), pos: saved.pos, total: saved.total } : null,
    unitDone: (ctx.progress.units[unitN] || {}).state === "done",
    test: ctx.features && ctx.features.tests && (ctx.ladder[String(unitN)] || unitWords(unitN).length)
      ? { href: routeFor("test", unitN), last: lastTest("unit", unitN), passMark: PASS_MARK }
      : null,
    unitStarted: Boolean(ctx.progress.units[unitN] || saved),
    onMarkUnitDone: (n) => {
      markDone(n);
      commit();
      navigate("lesson", n);
    },
    onResetUnit: (n) => {
      resetUnit(n);
      commit();
      navigate("lesson", n);
    },
    onStartDrills: (n) => {
      const prev = ctx.progress.units[n] || {};
      ctx.progress.units[n] = { ...prev, state: prev.state === "done" ? "done" : "in-progress", lessonRead: true };
      if (ctx.progress.sessions) delete ctx.progress.sessions[sessionKey(n)];
      commit();
      navigate("drill", n);
    },
  }, unit, lesson);
}

function recordAnswer(unitN, item, correct) {
  if (!correct || !item.id || !(item.rung || item.block)) return;
  if (item.spiral && !item.rung) return;
  const u = ctx.progress.units[unitN] || {};
  const key = rungKey(item);
  const done = { ...(u.done || {}) };
  const list = done[key] || [];
  if (!list.includes(item.id)) done[key] = [...list, item.id];
  ctx.progress.units[unitN] = { ...u, done };
}

function markDone(unitN) {
  const prev = ctx.progress.units[unitN] || {};
  if (prev.state !== "done") {
    ctx.progress.units[unitN] = { ...prev, state: "done", lessonRead: true };
    ctx.progress.currentUnit = Math.max(ctx.progress.currentUnit, unitN + 1);
  }
}

function resetUnit(unitN) {
  delete ctx.progress.units[unitN];
  for (const key of Object.keys(ctx.progress.sessions || {})) {
    if (key === String(unitN) || key.startsWith(`${unitN}:`)) delete ctx.progress.sessions[key];
  }
  if (ctx.progress.skills) delete ctx.progress.skills[String(unitN)];
}

function itemOwner(unitN, item) {
  return item.spiral && item.rung ? item.sourceUnit : unitN;
}

function itemDone(unitN, item) {
  return masteredIn(itemOwner(unitN, item)).has(item.id);
}

async function setItemDone(unitN, item, done) {
  const owner = itemOwner(unitN, item);
  if (done) {
    recordAnswer(owner, item, true);
    if (item.rung && ladderComplete(owner, await authoredFor(owner))) markDone(owner);
  } else {
    const u = ctx.progress.units[owner];
    if (u && u.done) {
      const key = rungKey(item);
      u.done = { ...u.done, [key]: (u.done[key] || []).filter((id) => id !== item.id) };
    }
  }
  commit();
}

function lastTest(scope, key) {
  const list = (ctx.progress.tests || []).filter((t) => t.scope === scope && (scope === "final" || t.key === key));
  return list.length ? list[list.length - 1] : null;
}

function pickLadder(authored, plan, unitN) {
  const used = new Set();
  const out = [];
  for (const [rung, count] of plan) {
    const pool = shuffle(authored.filter((it) => it.rung === rung && !used.has(it.src || it.id)));
    for (const it of pool.slice(0, count)) {
      used.add(it.src || it.id);
      out.push({ ...it, sourceUnit: unitN });
    }
  }
  return out;
}

async function testItems(opts) {
  const units = opts.scope === "unit" ? [opts.unit]
    : opts.scope === "part" ? ctx.course.units.filter((u) => u.part === opts.part).map((u) => u.n)
      : ctx.course.units.map((u) => u.n);
  const authoredBy = {};
  for (const n of units) authoredBy[n] = ctx.ladder[String(n)] ? await authoredFor(n) : [];
  return withSeed(`${opts.seed}:test`, () => {
    let items = [];
    if (opts.scope === "unit") {
      items = pickLadder(authoredBy[opts.unit], [[5, 6], [4, 6], [3, 4], [2, 2], [1, 2]], opts.unit);
    } else {
      const plan = opts.scope === "part" ? [[5, 1], [4, 1]] : [[5, 1], [4, 1]];
      const cap = 30;
      const per = shuffle(units.filter((n) => authoredBy[n].length)).map((n) => pickLadder(authoredBy[n], plan, n));
      for (let round = 0; items.length < cap && per.some((l) => l.length > round); round++) {
        for (const l of per) if (l[round] && items.length < cap) items.push(l[round]);
      }
    }
    if (ctx.features && ctx.features.wordLadder) {
      const words = shuffle(units.flatMap((n) => unitWords(n))).slice(0, items.length ? 5 : 12);
      const wordItems = wordItemsFor(items.length ? 3 : 2, words, wordDistractors(Math.max(...units)))
        .map((it) => ({ ...it, sourceUnit: ctx.vocab[it.wordIds[0]] ? ctx.vocab[it.wordIds[0]].unit : undefined }));
      items = [...items, ...wordItems];
    }
    return shuffle(items);
  });
}

async function loadTest(opts) {
  const seq = routeSeq;
  if (!opts.seed) {
    const seed = newSeed();
    setHash(opts.scope === "unit" ? routeFor("test", opts.unit, { seed }) : testRoute(opts.scope, opts.part, seed));
    return route();
  }
  const items = await testItems(opts);
  if (seq !== routeSeq) return;
  const unit = opts.scope === "unit" ? ctx.course.units.find((u) => u.n === opts.unit) : null;
  const part = opts.scope === "part" ? (ctx.course.parts || []).find((p) => p.n === opts.part) : null;
  const title = unit ? `Unit ${unit.n} test — ${unit.title}` : part ? `Part ${part.n} test — ${part.title}` : "Final exam (mock)";
  renderTest(ctx.root, {
    course: ctx.course,
    items,
    seed: opts.seed,
    title,
    backLabel: unit ? "← Lesson" : "← Roadmap",
    onBack: () => (unit ? navigate("lesson", unit.n) : navigate("roadmap")),
    onFinish: (r) => {
      const key = unit ? unit.n : part ? part.n : null;
      ctx.progress.tests = [...(ctx.progress.tests || []), {
        scope: opts.scope, key, seed: opts.seed, date: new Date().toISOString(),
        correct: r.correct, total: r.total, score: r.score, elapsed: r.elapsed,
      }];
      let msg = null;
      if (unit && r.passed && (ctx.progress.units[unit.n] || {}).state !== "done") {
        markDone(unit.n);
        msg = `Passed — Unit ${unit.n} is marked done and the next unit is open.`;
      }
      commit();
      return msg;
    },
  });
}

async function loadWords(unitN, opts = {}) {
  const unit = ctx.course.units.find((u) => u.n === unitN);
  const words = unitWords(unitN);
  if (!words.length) return loadLesson(unitN);
  const rung = opts.rung || openRung(words, wordsDone(unitN)) || WORD_RUNG_COUNT;
  if (!opts.seed) {
    setHash(routeFor("words", unitN, { rung, seed: newSeed() }));
    return route();
  }
  const items = withSeed(opts.seed, () => wordsSession(words, wordsDone(unitN), rung, wordDistractors(unitN), (ctx.features && ctx.features.wordsPerSession) || 10));
  if (!items.length) return loadLesson(unitN);
  showDrill(unit, items, { seed: opts.seed, pos: opts.pos, words: rung });
}

async function loadDrill(unitN, opts = {}) {
  const seq = routeSeq;
  const unit = ctx.course.units.find((u) => u.n === unitN);
  const pool = ctx.vocabList.filter((item) => item.unit === unitN);
  const authored = await authoredFor(unitN);
  if (seq !== routeSeq) return;

  if (opts.item) {
    const item = authored.find((it) => it.id === opts.item);
    if (!item) return loadLesson(unitN);
    return showDrill(unit, [item], { seed: opts.item, single: true, ladder: authored.some((it) => it.rung) });
  }

  if (!opts.seed) {
    const seed = newSeed();
    setHash(opts.block ? routeFor("block", unitN, { block: opts.block, seed })
      : opts.rung ? routeFor("rung", unitN, { rung: opts.rung, seed }) : routeFor("drill", unitN, { seed }));
    return loadDrill(unitN, { ...opts, seed });
  }

  const mastered = masteredIn(unitN);
  const satisfied = satisfiedIn(unitN, authored);
  const reviewPlan = opts.block || opts.rung ? null : await buildReviewPlan(unitN, opts.seed);
  if (seq !== routeSeq) return;
  const items = withSeed(opts.seed, () => {
    if (opts.block || opts.rung) {
      const inBlock = authored.filter((it) => (opts.block ? it.block === opts.block : it.rung === opts.rung));
      const cap = (ctx.features && ctx.features.authoredPerSession) || inBlock.length;
      return [...shuffle(inBlock.filter((it) => !mastered.has(it.id))), ...shuffle(inBlock.filter((it) => mastered.has(it.id)))].slice(0, cap);
    }
    const wordWarmup = ctx.features && ctx.features.wordLadder
      ? warmupWords(unitWords(unitN), wordsDone(unitN), wordDistractors(unitN), ctx.features.vocabPerSession ?? 3)
      : null;
    return buildSession(ctx.course, pool, {
      wordWarmup,
      unitN,
      vocabList: ctx.vocabList,
      progress: ctx.progress,
      authored,
      mastered: satisfied,
      reviewPlan,
      features: ctx.features,
    });
  });
  opts.ladder = authored.some((it) => it.rung);
  opts.pool = authored;
  if (!items.length) return loadLesson(unitN);
  showDrill(unit, items, opts);
}

function savedItems(saved, items, pool) {
  if (!saved || !saved.ids) return items;
  const byId = new Map([...(pool || []), ...items].map((it) => [it.id, it]));
  const restored = saved.ids.map((id) => byId.get(id));
  return restored.every(Boolean) ? restored : items;
}

function showDrill(unit, built, opts) {
  const unitN = unit.n;
  const group = opts.block || (opts.rung ? `rung${opts.rung}` : opts.words ? `words${opts.words}` : null);
  const key = sessionKey(unitN, group);
  const sessions = ctx.progress.sessions || {};
  const saved = !opts.single && sessions[key] && sessions[key].seed === opts.seed ? sessions[key] : null;
  const items = savedItems(saved, built, opts.pool);
  const pos = saved ? saved.pos : Math.min(Math.max(parseInt(opts.pos, 10) || 1, 1), items.length);
  const where = (p) => (opts.words
    ? routeFor("words", unitN, { rung: opts.words, seed: opts.seed, pos: p })
    : opts.block
    ? routeFor("block", unitN, { block: opts.block, seed: opts.seed, pos: p })
    : opts.rung ? routeFor("rung", unitN, { rung: opts.rung, seed: opts.seed, pos: p })
      : routeFor("drill", unitN, { seed: opts.seed, pos: p }));
  if (!opts.single) setHash(where(pos));

  renderDrill(ctx.root, {
    course: ctx.course,
    vocab: ctx.vocab,
    progress: ctx.progress,
    navigate,
    unit,
    items,
    seed: opts.seed,
    single: Boolean(opts.single),
    start: pos - 1,
    initial: saved ? { correct: saved.correct, answered: saved.answered, detail: saved.detail || [], requeue: saved.requeue || [] } : null,
    features: ctx.features,
    onPosition: (idx) => {
      if (!opts.single) setHash(where(idx + 1));
    },
    isItemDone: (item) => itemDone(unitN, item),
    onMarkItem: (item, done) => setItemDone(unitN, item, done),
    onAnswer: async (item, correct, state, res = {}) => {
      const owner = itemOwner(unitN, item);
      if (item.wordRung) recordWords(unitN, item, { ...res, correct });
      else recordAnswer(owner, item, correct);
      if (correct && item.rung && ladderComplete(owner, await authoredFor(owner))) markDone(owner);
      if (!opts.single) {
        ctx.progress.sessions = { ...(ctx.progress.sessions || {}) };
        ctx.progress.sessions[key] = { seed: opts.seed, block: opts.block || null, rung: opts.rung || null, pos: state.next + 1, total: items.length, correct: state.correct, answered: state.answered, detail: state.detail, requeue: state.requeue || [], ids: items.map((it) => it.id) };
      }
      commit();
    },
    onComplete: (correct, total, detail) => {
      if (ctx.progress.sessions) delete ctx.progress.sessions[key];
      if (opts.single || opts.block || opts.rung || opts.words || !total) {
        commit();
        return;
      }
      const prev = ctx.progress.units[unitN] || {};
      const bestScore = Math.round((correct / total) * 100);
      const wasDone = prev.state === "done";
      const passed = opts.ladder ? prev.state === "done" : bestScore >= 70;
      const newState = wasDone || passed ? "done" : "in-progress";
      ctx.progress.units[unitN] = {
        ...prev,
        state: newState,
        lessonRead: true,
        bestScore: Math.max(prev.bestScore || 0, bestScore),
        lastPlayed: new Date().toISOString(),
      };
      if (newState === "done" && !wasDone && ctx.progress.currentUnit === unitN) {
        ctx.progress.currentUnit = unitN + 1;
      }
      if (ctx.features && ctx.features.diagnostics && detail) {
        ctx.progress.skills = ctx.progress.skills || {};
        for (const d of detail) {
          const k = String(d.unit);
          const s = ctx.progress.skills[k] || { correct: 0, attempts: 0 };
          s.attempts += 1;
          if (d.correct) s.correct += 1;
          ctx.progress.skills[k] = s;
        }
      }
      commit();
    },
  });
}

async function bootstrap() {
  ctx.root = document.getElementById("app");
  ctx.base = document.body.dataset.courseBase || "../";
  ctx.course = await fetchJSON(ctx.base + "course.json");
  ctx.features = ctx.course.features || {};
  setScript(ctx.course);
  const vocabData = await fetchJSON(ctx.base + "vocab.json");
  ctx.vocabList = vocabData.items;
  for (const item of vocabData.items) ctx.vocab[item.id] = item;
  ctx.progress = await loadProgress(ctx.course.id);
  try {
    const ladder = await fetchJSON(ctx.base + "authored/ladder.json");
    ctx.ladder = ladder.units || {};
    ctx.ladderExtra = ladder.extra || {};
  } catch {
    ctx.ladder = {};
    ctx.ladderExtra = {};
  }
  initKeyboard(document.body, ctx.course.script.keyboard);
  window.addEventListener("hashchange", route);
  route();
}

bootstrap().catch((err) => {
  const root = document.getElementById("app");
  root.textContent = `Error: ${err.message}`;
});
