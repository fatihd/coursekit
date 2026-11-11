import { getType } from "./exercise-types/index.js";
import { distinctOptions } from "./exercise-types/mcq.js";
import { shuffle } from "./exercise-types/util.js";
import { previousUnitItems, reviewItems, reviewPlanItems, spiralItems } from "./knowledge.js";

// Review MCQs: Hebrew word -> its English. Wrong options are random glosses from the given pool,
// words of the same category first, so they cannot be ruled out by habit.
function spiralMcqItems(sources, pool) {
  const items = [];
  for (const correct of sources) {
    const others = shuffle(pool.filter((x) => x.id !== correct.id && x.gloss && x.gloss !== correct.gloss));
    const same = others.filter((x) => x.category === correct.category);
    const distractorGlosses = distinctOptions([...same, ...others].map((x) => x.gloss)).slice(0, 3);
    const options = distinctOptions([correct.gloss, ...distractorGlosses]);
    if (options.length < 2) continue;
    items.push({
      type: "mcq",
      direction: "script->gloss",
      stimulus: correct.scriptForm,
      options: shuffle(options),
      answer: correct.gloss,
      stimulusIsScript: true,
      optionIsScript: false,
      spiral: true,
      sourceUnit: correct.unit,
    });
  }
  return items;
}

function generatedId(item) {
  const text = [item.type, item.direction || "", JSON.stringify(item.stimulus || ""), JSON.stringify(item.answer || item.accepted || "")].join("|");
  let h = 2166136261;
  for (const ch of text) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return `${item.spiral ? "review" : "vocab"}-${(h >>> 0).toString(36)}`;
}

export function ladderSession(items, mastered, room) {
  const rungs = [...new Set(items.map((i) => i.rung))].sort((a, b) => a - b);
  const open = items.filter((i) => !mastered.has(i.id));
  const current = rungs.find((r) => open.some((i) => i.rung === r));
  let picked = [];
  if (current === undefined) {
    picked = shuffle(items).slice(0, room);
  } else {
    for (const r of rungs.filter((x) => x >= current)) {
      picked.push(...shuffle(open.filter((i) => i.rung === r)));
      if (picked.length >= room) break;
    }
    picked = picked.slice(0, room);
  }
  return picked.map((it, i) => ({ it, i })).sort((a, b) => a.it.rung - b.it.rung || a.i - b.i).map((x) => x.it);
}

export function buildSession(course, pool, options = {}) {
  const mcq = getType("mcq");
  const match = getType("match-by-line");
  const trans = getType("translate-phrase");
  const dict = getType("dictation");
  const parseNoun = getType("parse-noun");
  const parseVerb = getType("parse-verb");
  const produce = getType("produce-form");

  const features = options.features || {};
  const translit = features.transliteration !== false;
  const target = options.count || features.targetItems || 14;
  const allAuthored = options.authored || [];
  const authoredCap = features.authoredPerSession;
  const mastered = options.mastered || new Set();
  const ladderItems = allAuthored.filter((i) => i.rung);
  const ladderMode = ladderItems.length > 0;
  const authored = ladderMode ? [] : authoredCap && allAuthored.length > authoredCap
    ? [...shuffle(allAuthored.filter((i) => !mastered.has(i.id))), ...shuffle(allAuthored.filter((i) => mastered.has(i.id)))].slice(0, authoredCap)
    : allAuthored;

  const reviewCount = features.reviewItems || 2;
  const picker = features.diagnostics ? reviewItems : spiralItems;
  const earlier = options.vocabList && options.unitN ? previousUnitItems(options.vocabList, options.unitN) : [];
  let spiralItems_;
  if (options.reviewPlan) {
    spiralItems_ = reviewPlanItems(options.reviewPlan, reviewCount).flatMap((r) => {
      if (r.kind === "sentence") return [{ ...r.item, spiral: true, sourceUnit: r.unit }];
      return spiralMcqItems([r.item], options.vocabList.filter((x) => x.unit < options.unitN || x.unit === r.unit));
    });
  } else {
    const spiral = options.progress && options.vocabList && options.unitN
      ? picker(options.progress, options.vocabList, options.unitN, reviewCount)
      : [];
    spiralItems_ = spiralMcqItems(spiral, earlier);
  }

  const remaining = Math.max(0, target - spiralItems_.length - authored.length);

  const generated = [];
  generated.push(
    ...mcq.generate(
      { count: 6, directions: translit ? ["script->gloss", "gloss->script", "translit->script"] : ["script->gloss", "gloss->script"] },
      pool,
    ),
  );
  generated.push(...match.generate({ count: 5 }, pool));
  generated.push(...trans.generate({ count: 3 }, pool));
  generated.push(...dict.generate({ count: 3, transliteration: translit }, pool));

  if (features.parsing) {
    const verbLemmas = options.vocabList
      ? options.vocabList.filter((i) => i.category === "verb")
      : [];
    if (options.unitN >= 9) {
      generated.push(...parseNoun.generate({ count: 3 }, pool));
      generated.push(...produce.generate({ count: 3, only: "noun" }, pool, options.unitN));
    }
    if (options.unitN >= 16) {
      generated.push(...parseVerb.generate({ count: 3 }, verbLemmas, options.unitN));
      generated.push(...produce.generate({ count: 3, only: "verb" }, verbLemmas, options.unitN));
    }
  }

  if (ladderMode) {
    const vocabCount = Math.min(features.vocabPerSession ?? 4, generated.length);
    const vocab = generated.slice(0, vocabCount);
    const climb = ladderSession(ladderItems, mastered, Math.max(0, target - spiralItems_.length - vocab.length));
    return [...spiralItems_, ...vocab, ...climb].map((item) => (item.id ? item : { ...item, id: generatedId(item) }));
  }

  return [...spiralItems_, ...authored, ...generated.slice(0, remaining)].map((item) =>
    (item.id ? item : { ...item, id: generatedId(item) }));
}
