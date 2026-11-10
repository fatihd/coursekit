import { loadProgress, saveProgress, exportProgress, importProgress } from "./store.js";
import { renderRoadmap } from "./views/roadmap.js";
import { renderLesson } from "./views/lesson.js";
import { renderDrill } from "./views/drill.js";
import { buildSession } from "./session.js";
import { buildRecap } from "./knowledge.js";
import { initKeyboard } from "./keyboard.js";

const ctx = {
  base: "",
  course: null,
  vocab: {},
  vocabList: [],
  progress: null,
  root: null,
};

async function fetchJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`failed to load ${path}: ${res.status}`);
  return res.json();
}

function commit() {
  saveProgress(ctx.course.id, ctx.progress);
}

function navigate(view, param) {
  if (view === "roadmap") {
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
  } else if (view === "lesson") {
    loadLesson(param);
  } else if (view === "drill") {
    loadDrill(param);
  }
}

async function loadLesson(unitN) {
  const padded = String(unitN).padStart(2, "0");
  const lesson = await fetchJSON(`${ctx.base}units/${padded}.json`);
  const unit = ctx.course.units.find((u) => u.n === unitN);

  const viewCtx = {
    course: ctx.course,
    vocab: ctx.vocab,
    progress: ctx.progress,
    navigate,
    features: ctx.features,
    recap: buildRecap(ctx.course, ctx.progress, unitN),
    onStartDrills: (n) => {
      const prev = ctx.progress.units[n] || {};
      ctx.progress.units[n] = { ...prev, state: "in-progress", lessonRead: true };
      commit();
      navigate("drill", n);
    },
  };

  renderLesson(ctx.root, viewCtx, unit, lesson);
}

async function loadDrill(unitN) {
  const unit = ctx.course.units.find((u) => u.n === unitN);
  const pool = ctx.vocabList.filter((item) => item.unit === unitN);

  let authored = [];
  try {
    const padded = String(unitN).padStart(2, "0");
    const authoredData = await fetchJSON(`${ctx.base}authored/${padded}.json`);
    authored = authoredData.items || [];
  } catch {
    authored = [];
  }

  const items = buildSession(ctx.course, pool, {
    unitN,
    vocabList: ctx.vocabList,
    progress: ctx.progress,
    authored,
    features: ctx.features,
  });

  const viewCtx = {
    course: ctx.course,
    vocab: ctx.vocab,
    progress: ctx.progress,
    navigate,
    unit,
    items,
    features: ctx.features,
    onComplete: (correct, total, detail) => {
      const prev = ctx.progress.units[unitN] || {};
      const bestScore = Math.round((correct / total) * 100);
      const wasDone = prev.state === "done";
      const newState = bestScore >= 70 ? "done" : "in-progress";
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
          const key = String(d.unit);
          const s = ctx.progress.skills[key] || { correct: 0, attempts: 0 };
          s.attempts += 1;
          if (d.correct) s.correct += 1;
          ctx.progress.skills[key] = s;
        }
      }
      commit();
    },
  };

  renderDrill(ctx.root, viewCtx);
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
  navigate("roadmap");
}

bootstrap().catch((err) => {
  const root = document.getElementById("app");
  root.textContent = `Error: ${err.message}`;
});
