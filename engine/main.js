import { loadProgress, saveProgress, exportProgress, importProgress } from "./store.js";
import { renderRoadmap } from "./views/roadmap.js";
import { renderLesson } from "./views/lesson.js";
import { renderDrill } from "./views/drill.js";
import { buildSession } from "./session.js";
import { buildRecap, reviewUnits, weakUnits } from "./knowledge.js";
import { initKeyboard } from "./keyboard.js";
import { newSeed, shuffle, withSeed } from "./exercise-types/util.js";

const ctx = {
  base: "",
  course: null,
  vocab: {},
  vocabList: [],
  progress: null,
  root: null,
  ladder: {},
};

const RUNG_NAMES = { 1: "True or false", 2: "Choose", 3: "Fill in", 4: "Translate", 5: "Translate with vowel points" };

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

function route() {
  const [slug, kind, a, b, c] = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  const unit = slug ? unitBySlug(slug) : null;
  if (!unit) return showRoadmap();
  if (!kind) return loadLesson(unit.n);
  if (kind === "drill") return loadDrill(unit.n, { seed: a, pos: b });
  if (kind === "block") return loadDrill(unit.n, { block: a, seed: b, pos: c });
  if (kind === "rung") return loadDrill(unit.n, { rung: Number(a), seed: b, pos: c });
  if (kind === "item") return loadDrill(unit.n, { item: a });
  return loadLesson(unit.n);
}

function showRoadmap() {
  renderRoadmap(ctx.root, ctx.course, ctx.progress, navigate, {
    stars: (n) => ladderStars(n),
    onExport: () => exportProgress(ctx.course.id, ctx.progress),
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

function ladderSummary(unitN, authored) {
  const mastered = masteredIn(unitN);
  const rungs = new Map();
  for (const it of authored) {
    if (!it.rung) continue;
    const r = rungs.get(it.rung) || { rung: it.rung, label: RUNG_NAMES[it.rung] || `Rung ${it.rung}`, total: 0, done: 0 };
    r.total += 1;
    if (mastered.has(it.id)) r.done += 1;
    rungs.set(it.rung, r);
  }
  return [...rungs.values()].sort((a, b) => a.rung - b.rung)
    .map((r) => ({ ...r, href: routeFor("rung", unitN, { rung: r.rung }) }));
}

function ladderComplete(unitN, authored) {
  const limit = (ctx.features && ctx.features.unlockRung) || 99;
  const mastered = masteredIn(unitN);
  const needed = authored.filter((it) => it.rung && it.rung <= limit);
  return needed.length > 0 && needed.every((it) => mastered.has(it.id));
}

function ladderStars(unitN) {
  const totals = ctx.ladder[String(unitN)];
  if (!totals) return null;
  const done = doneIds(unitN);
  return Object.keys(totals).sort().map((r) => (done[r] || []).length >= totals[r]);
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
  const lesson = await fetchJSON(`${ctx.base}units/${String(unitN).padStart(2, "0")}.json`);
  const unit = ctx.course.units.find((u) => u.n === unitN);
  const authored = await authoredFor(unitN);
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
    ladder: ladderSummary(unitN, authored),
    unlockRung: ctx.features && ctx.features.unlockRung,
    resume: saved ? { href: routeFor("drill", unitN, saved), pos: saved.pos, total: saved.total } : null,
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
  const key = String(item.rung || 0);
  const done = { ...(u.done || {}) };
  const list = done[key] || [];
  if (!list.includes(item.id)) done[key] = [...list, item.id];
  ctx.progress.units[unitN] = { ...u, done };
}

function markDone(unitN) {
  const prev = ctx.progress.units[unitN] || {};
  if (prev.state !== "done") {
    ctx.progress.units[unitN] = { ...prev, state: "done", lessonRead: true };
    if (ctx.progress.currentUnit === unitN) ctx.progress.currentUnit = unitN + 1;
  }
}

async function loadDrill(unitN, opts = {}) {
  const unit = ctx.course.units.find((u) => u.n === unitN);
  const pool = ctx.vocabList.filter((item) => item.unit === unitN);
  const authored = await authoredFor(unitN);

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
  const reviewPlan = opts.block || opts.rung ? null : await buildReviewPlan(unitN, opts.seed);
  const items = withSeed(opts.seed, () => {
    if (opts.block || opts.rung) {
      const inBlock = authored.filter((it) => (opts.block ? it.block === opts.block : it.rung === opts.rung));
      const cap = (ctx.features && ctx.features.authoredPerSession) || inBlock.length;
      return [...shuffle(inBlock.filter((it) => !mastered.has(it.id))), ...shuffle(inBlock.filter((it) => mastered.has(it.id)))].slice(0, cap);
    }
    return buildSession(ctx.course, pool, {
      unitN,
      vocabList: ctx.vocabList,
      progress: ctx.progress,
      authored,
      mastered,
      reviewPlan,
      features: ctx.features,
    });
  });
  opts.ladder = authored.some((it) => it.rung);
  if (!items.length) return loadLesson(unitN);
  showDrill(unit, items, opts);
}

function showDrill(unit, items, opts) {
  const unitN = unit.n;
  const group = opts.block || (opts.rung ? `rung${opts.rung}` : null);
  const key = sessionKey(unitN, group);
  const sessions = ctx.progress.sessions || {};
  const saved = !opts.single && sessions[key] && sessions[key].seed === opts.seed ? sessions[key] : null;
  const pos = saved ? saved.pos : Math.min(Math.max(parseInt(opts.pos, 10) || 1, 1), items.length);
  const where = (p) => (opts.block
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
    initial: saved ? { correct: saved.correct, answered: saved.answered, detail: saved.detail || [] } : null,
    features: ctx.features,
    onPosition: (idx) => {
      if (!opts.single) setHash(where(idx + 1));
    },
    onAnswer: async (item, correct, state) => {
      const owner = item.spiral && item.rung ? item.sourceUnit : unitN;
      recordAnswer(owner, item, correct);
      if (correct && item.rung && ladderComplete(owner, await authoredFor(owner))) markDone(owner);
      if (!opts.single) {
        ctx.progress.sessions = { ...(ctx.progress.sessions || {}) };
        ctx.progress.sessions[key] = { seed: opts.seed, block: opts.block || null, rung: opts.rung || null, pos: state.next + 1, total: items.length, correct: state.correct, answered: state.answered, detail: state.detail };
      }
      commit();
    },
    onComplete: (correct, total, detail) => {
      if (ctx.progress.sessions) delete ctx.progress.sessions[key];
      if (opts.single || opts.block || opts.rung || !total) {
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
  const vocabData = await fetchJSON(ctx.base + "vocab.json");
  ctx.vocabList = vocabData.items;
  for (const item of vocabData.items) ctx.vocab[item.id] = item;
  ctx.progress = await loadProgress(ctx.course.id);
  try {
    ctx.ladder = (await fetchJSON(ctx.base + "authored/ladder.json")).units || {};
  } catch {
    ctx.ladder = {};
  }
  initKeyboard(document.body, ctx.course.script.keyboard);
  window.addEventListener("hashchange", route);
  route();
}

bootstrap().catch((err) => {
  const root = document.getElementById("app");
  root.textContent = `Error: ${err.message}`;
});
