import { getType } from "./exercise-types/index.js";
import { distinctOptions } from "./exercise-types/mcq.js";
import { shuffle } from "./exercise-types/util.js";
import { spiralItems, reviewItems, knownSetItems } from "./knowledge.js";

// Build spiral review MCQs with distractors drawn from the full known set so a
// review question is never a single-option MCQ (a one-word pool would otherwise
// produce exactly one choice).
function spiralMcqItems(sources, known) {
  const items = [];
  for (const correct of sources) {
    const distractorGlosses = distinctOptions(
      known
        .filter((x) => x.id !== correct.id && x.gloss && x.gloss !== correct.gloss)
        .map((x) => x.gloss),
    ).slice(0, 3);
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
  const authored = authoredCap && allAuthored.length > authoredCap
    ? [...shuffle(allAuthored.filter((i) => !mastered.has(i.id))), ...shuffle(allAuthored.filter((i) => mastered.has(i.id)))].slice(0, authoredCap)
    : allAuthored;

  const reviewCount = features.reviewItems || 2;
  const picker = features.diagnostics ? reviewItems : spiralItems;
  const known = options.progress && options.vocabList
    ? knownSetItems(options.progress, options.vocabList)
    : [];
  const spiral = options.progress && options.vocabList && options.unitN
    ? picker(options.progress, options.vocabList, options.unitN, reviewCount)
    : [];

  const spiralItems_ = spiralMcqItems(spiral, known);

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

  return [...spiralItems_, ...authored, ...generated.slice(0, remaining)].map((item) =>
    (item.id ? item : { ...item, id: generatedId(item) }));
}
