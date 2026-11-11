import { shuffle } from "./exercise-types/util.js";

export function completedUnitNumbers(progress) {
  return Object.entries(progress.units)
    .filter(([, u]) => u && u.state === "done")
    .map(([n]) => Number(n));
}

export function knownSetItems(progress, vocabList) {
  const done = new Set(completedUnitNumbers(progress));
  return vocabList.filter((item) => done.has(item.unit));
}

export function previousUnitItems(vocabList, currentUnit) {
  return vocabList.filter((item) => item.unit < currentUnit);
}

export function buildRecap(course, progress, currentUnit) {
  const recent = completedUnitNumbers(progress)
    .filter((n) => n < currentUnit)
    .sort((a, b) => b - a)
    .slice(0, 3);
  if (!recent.length) return null;
  const titles = recent.map((n) => {
    const u = course.units.find((x) => x.n === n);
    return u ? u.title : `Unit ${n}`;
  });
  return { titles, text: titles.join(" · ") };
}

export function unitAccuracy(progress, n) {
  const s = (progress.skills || {})[n];
  return s && s.attempts ? s.correct / s.attempts : null;
}

// Earlier units to review, gaps first: units never answered (e.g. skipped), then the lowest
// accuracy. Every earlier unit counts, completed or not.
export function reviewUnits(progress, candidates, count = 3) {
  return shuffle(candidates)
    .map((n) => ({ n, acc: unitAccuracy(progress, n) }))
    .sort((a, b) => (a.acc === null ? -1 : a.acc) - (b.acc === null ? -1 : b.acc))
    .slice(0, count)
    .map((x) => x.n);
}

export function weakUnits(progress, currentUnit, count = 3, candidates = null) {
  const pool = candidates || completedUnitNumbers(progress).filter((n) => n < currentUnit);
  return reviewUnits(progress, pool.filter((n) => n < currentUnit), count).sort((a, b) => a - b);
}

export function spiralItems(progress, vocabList, currentUnit, count = 2) {
  const earlier = previousUnitItems(vocabList, currentUnit);
  if (!earlier.length) return [];
  return shuffle(earlier).slice(0, count);
}

export function reviewItems(progress, vocabList, currentUnit, count = 2) {
  const earlier = previousUnitItems(vocabList, currentUnit);
  if (!earlier.length) return [];
  const units = reviewUnits(progress, [...new Set(earlier.map((i) => i.unit))], 3);
  const byUnit = {};
  for (const item of earlier) (byUnit[item.unit] ||= []).push(item);
  const picked = [];
  const queues = units.map((n) => shuffle(byUnit[n] || []));
  while (picked.length < count && queues.some((q) => q.length)) {
    for (const q of queues) if (q.length && picked.length < count) picked.push(q.shift());
  }
  return picked;
}

// The review part of a session: earlier units chosen by `reviewUnits`, alternating a vocabulary
// question and a sentence-ladder item from each. `plan` is [{ unit, vocab, ladder, mastered, done }].
export function reviewPlanItems(plan, count) {
  const out = [];
  const queues = plan.map((p) => {
    const words = shuffle(p.vocab || []);
    const ladder = p.ladder || [];
    let sentences = [];
    if (ladder.length) {
      const doneRungs = Object.entries(p.done || {}).filter(([, ids]) => ids.length).map(([r]) => Number(r));
      const best = doneRungs.length ? Math.max(...doneRungs) : 0;
      const rung = best ? Math.min(best + 1, 5) : 2;
      const atRung = ladder.filter((it) => it.rung === rung);
      const open = atRung.filter((it) => !p.mastered.has(it.id));
      sentences = shuffle(open.length ? open : atRung.length ? atRung : ladder);
    }
    return { unit: p.unit, words, sentences, turn: 0 };
  });
  while (out.length < count && queues.some((q) => q.words.length || q.sentences.length)) {
    for (const q of queues) {
      if (out.length >= count) break;
      const first = q.turn % 2 === 0 ? q.words : q.sentences;
      const second = q.turn % 2 === 0 ? q.sentences : q.words;
      q.turn += 1;
      if (first.length) out.push({ kind: first === q.words ? "word" : "sentence", unit: q.unit, item: first.shift() });
      else if (second.length) out.push({ kind: second === q.words ? "word" : "sentence", unit: q.unit, item: second.shift() });
    }
  }
  return out;
}
