import { loadProgress, saveProgress, exportProgress, importProgress } from "./store.js";
import { renderRoadmap } from "./views/roadmap.js";
import { renderLesson } from "./views/lesson.js";
import { renderDrill } from "./views/drill.js";
import { buildSession } from "./session.js";
import { buildRecap } from "./knowledge.js";
import { initKeyboard } from "./keyboard.js";
import { newSeed, shuffle, withSeed } from "./exercise-types/util.js";

const ctx = {
  base: "",
  course: null,
  vocab: {},
  vocabList: [],
  progress: null,
  root: null,
};

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
  if (kind === "item") return loadDrill(unit.n, { item: a });
  return loadLesson(unit.n);
}

function showRoadmap() {
  renderRoadmap(ctx.root, ctx.course, ctx.progress, navigate, {
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
      items = data.items || [];
    } catch {
      items = [];
    }
    authoredCache.set(unitN, items);
  }
  return authoredCache.get(unitN);
}

function masteredIn(unitN) {
  const blocks = (ctx.progress.units[unitN] || {}).blocks || {};
  return new Set(Object.values(blocks).flatMap((b) => b.correct || []));
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
    blocks: blockSummary(unitN, authored),
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
  if (!correct || !item.id || !item.block || item.spiral) return;
  const u = ctx.progress.units[unitN] || {};
  const blocks = { ...(u.blocks || {}) };
  const b = blocks[item.block] || { correct: [] };
  if (!b.correct.includes(item.id)) blocks[item.block] = { correct: [...b.correct, item.id] };
  ctx.progress.units[unitN] = { ...u, blocks };
}

async function loadDrill(unitN, opts = {}) {
  const unit = ctx.course.units.find((u) => u.n === unitN);
  const pool = ctx.vocabList.filter((item) => item.unit === unitN);
  const authored = await authoredFor(unitN);

  if (opts.item) {
    const item = authored.find((it) => it.id === opts.item);
    if (!item) return loadLesson(unitN);
    return showDrill(unit, [item], { seed: opts.item, single: true });
  }

  if (!opts.seed) {
    const seed = newSeed();
    setHash(opts.block ? routeFor("block", unitN, { block: opts.block, seed }) : routeFor("drill", unitN, { seed }));
    return loadDrill(unitN, { ...opts, seed });
  }

  const mastered = masteredIn(unitN);
  const items = withSeed(opts.seed, () => {
    if (opts.block) {
      const inBlock = authored.filter((it) => it.block === opts.block);
      const cap = (ctx.features && ctx.features.authoredPerSession) || inBlock.length;
      return [...shuffle(inBlock.filter((it) => !mastered.has(it.id))), ...shuffle(inBlock.filter((it) => mastered.has(it.id)))].slice(0, cap);
    }
    return buildSession(ctx.course, pool, {
      unitN,
      vocabList: ctx.vocabList,
      progress: ctx.progress,
      authored,
      mastered,
      features: ctx.features,
    });
  });
  if (!items.length) return loadLesson(unitN);
  showDrill(unit, items, opts);
}

function showDrill(unit, items, opts) {
  const unitN = unit.n;
  const key = sessionKey(unitN, opts.block);
  const sessions = ctx.progress.sessions || {};
  const saved = !opts.single && sessions[key] && sessions[key].seed === opts.seed ? sessions[key] : null;
  const pos = saved ? saved.pos : Math.min(Math.max(parseInt(opts.pos, 10) || 1, 1), items.length);
  const where = (p) => (opts.block
    ? routeFor("block", unitN, { block: opts.block, seed: opts.seed, pos: p })
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
    onAnswer: (item, correct, state) => {
      recordAnswer(unitN, item, correct);
      if (!opts.single) {
        ctx.progress.sessions = { ...(ctx.progress.sessions || {}) };
        ctx.progress.sessions[key] = { seed: opts.seed, block: opts.block || null, pos: state.next + 1, total: items.length, correct: state.correct, answered: state.answered, detail: state.detail };
      }
      commit();
    },
    onComplete: (correct, total, detail) => {
      if (ctx.progress.sessions) delete ctx.progress.sessions[key];
      if (opts.single || opts.block || !total) {
        commit();
        return;
      }
      const prev = ctx.progress.units[unitN] || {};
      const bestScore = Math.round((correct / total) * 100);
      const wasDone = prev.state === "done";
      const newState = wasDone || bestScore >= 70 ? "done" : "in-progress";
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
  initKeyboard(document.body, ctx.course.script.keyboard);
  window.addEventListener("hashchange", route);
  route();
}

bootstrap().catch((err) => {
  const root = document.getElementById("app");
  root.textContent = `Error: ${err.message}`;
});
