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

export function spiralItems(progress, vocabList, currentUnit, count = 2) {
  const known = knownSetItems(progress, vocabList).filter((item) => item.unit < currentUnit);
  if (!known.length) return [];
  return shuffle(known).slice(0, count);
}

function skillAccuracy(skill) {
  if (!skill || !skill.attempts) return 1;
  return skill.correct / skill.attempts;
}

export function weakUnits(progress, currentUnit, count = 3) {
  const skills = progress.skills || {};
  return completedUnitNumbers(progress)
    .filter((n) => n < currentUnit)
    .sort((a, b) => skillAccuracy(skills[a]) - skillAccuracy(skills[b]))
    .slice(0, count);
}

export function reviewItems(progress, vocabList, currentUnit, count = 2) {
  const known = knownSetItems(progress, vocabList).filter((item) => item.unit < currentUnit);
  if (!known.length) return [];
  const byUnit = {};
  for (const item of known) (byUnit[item.unit] ||= []).push(item);
  const ordered = weakUnits(progress, currentUnit, Object.keys(byUnit).length);
  const seen = new Set(ordered);
  for (const n of Object.keys(byUnit).map(Number)) {
    if (!seen.has(n)) ordered.push(n);
  }
  const picked = [];
  for (const n of ordered) {
    for (const item of shuffle(byUnit[n] || [])) {
      if (picked.length >= count) break;
      picked.push(item);
    }
    if (picked.length >= count) break;
  }
  return picked;
}
