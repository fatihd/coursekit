const KEY_PREFIX = "lang-research.progress.";

function emptyProgress(courseId) {
  return {
    schema: "progress-v1.json",
    courseId,
    student: { name: "", forkRemote: "" },
    currentUnit: 1,
    units: {},
    knownSet: [],
    xp: 0,
    lastAttemptBranch: null,
    updatedAt: null,
  };
}

function validProgress(progress, courseId) {
  return progress && progress.schema === "progress-v1.json" && progress.courseId === courseId
    && progress.student && typeof progress.units === "object"
    && Number.isInteger(progress.currentUnit) && progress.currentUnit >= 1;
}

function loadLocalProgress(courseId) {
  const key = KEY_PREFIX + courseId;
  try {
    const raw = localStorage.getItem(key);
    const progress = raw && JSON.parse(raw);
    if (validProgress(progress, courseId)) return progress;
  } catch {
    return null;
  }
  return null;
}

export async function loadProgress(courseId) {
  return loadLocalProgress(courseId) || emptyProgress(courseId);
}

let persistRequested = false;

export function saveProgress(courseId, progress) {
  progress.updatedAt = new Date().toISOString();
  localStorage.setItem(KEY_PREFIX + courseId, JSON.stringify(progress));
  if (!persistRequested && navigator.storage && navigator.storage.persist) {
    persistRequested = true;
    navigator.storage.persist().catch(() => {});
  }
}

export function exportProgress(courseId, progress) {
  saveProgress(courseId, progress);
  progress.lastExportedAt = progress.updatedAt;
  localStorage.setItem(KEY_PREFIX + courseId, JSON.stringify(progress));
  const blob = new Blob([JSON.stringify(progress, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${courseId}-progress-${progress.lastExportedAt.slice(0, 10)}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const STATE_RANK = { "in-progress": 1, done: 2 };

export function mergeProgress(a, b) {
  const units = { ...a.units };
  for (const [n, ub] of Object.entries(b.units || {})) {
    const ua = units[n];
    if (!ua) { units[n] = { ...ub }; continue; }
    const better = (STATE_RANK[ub.state] || 0) > (STATE_RANK[ua.state] || 0) ? ub : ua;
    const merged = { ...ua, ...ub, state: better.state };
    merged.lessonRead = Boolean(ua.lessonRead || ub.lessonRead);
    if (ua.bestScore !== undefined || ub.bestScore !== undefined) {
      merged.bestScore = Math.max(ua.bestScore || 0, ub.bestScore || 0);
    }
    const la = ua.lastPlayed || "", lb = ub.lastPlayed || "";
    if (la || lb) merged.lastPlayed = la > lb ? la : lb;
    if (ua.done || ub.done) {
      const done = { ...(ua.done || {}) };
      for (const [rung, ids] of Object.entries(ub.done || {})) {
        done[rung] = [...new Set([...(done[rung] || []), ...ids])];
      }
      merged.done = done;
    }
    units[n] = merged;
  }
  const out = {
    ...a,
    units,
    currentUnit: Math.max(a.currentUnit || 1, b.currentUnit || 1),
    knownSet: [...new Set([...(a.knownSet || []), ...(b.knownSet || [])])],
    xp: Math.max(a.xp || 0, b.xp || 0),
  };
  if (a.skills || b.skills) {
    const skills = { ...(a.skills || {}) };
    for (const [k, sb] of Object.entries(b.skills || {})) {
      const sa = skills[k];
      skills[k] = !sa || (sb.attempts || 0) > (sa.attempts || 0) ? { ...sb } : sa;
    }
    out.skills = skills;
  }
  if (a.sessions || b.sessions) out.sessions = { ...(b.sessions || {}), ...(a.sessions || {}) };
  if (!out.student?.name && b.student?.name) out.student = { ...b.student };
  return out;
}

export async function importProgress(courseId, progress, file) {
  let incoming;
  try {
    incoming = JSON.parse(await file.text());
  } catch {
    return { ok: false, error: "This file is not valid JSON." };
  }
  if (!incoming || incoming.schema !== "progress-v1.json") {
    return { ok: false, error: "This file is not a progress export." };
  }
  if (incoming.courseId !== courseId) {
    return { ok: false, error: `This file belongs to another course (${incoming.courseId}).` };
  }
  if (!validProgress(incoming, courseId)) {
    return { ok: false, error: "This progress file is damaged or incomplete." };
  }
  const before = Object.values(progress.units).filter((u) => u.state === "done").length;
  const merged = mergeProgress(progress, incoming);
  const after = Object.values(merged.units).filter((u) => u.state === "done").length;
  return { ok: true, progress: merged, added: after - before };
}

export function unitState(progress, n) {
  const u = progress.units[n];
  if (u && u.state === "done") return "done";
  if (u && u.state === "in-progress") return "in-progress";
  if (n === progress.currentUnit) return "available";
  return "locked";
}
