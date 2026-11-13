import { getType } from "./exercise-types/index.js";
import { distinctOptions } from "./exercise-types/mcq.js";
import { random, shuffle } from "./exercise-types/util.js";
import { script } from "./script.js";

export const WORD_RUNGS = { 1: "Recognize", 2: "Recall", 3: "Type the word", 4: "Type with vowel points" };

export function wordRungs() {
  return { ...WORD_RUNGS, 4: `Type with ${script().marks}` };
}
export const WORD_RUNG_COUNT = 4;

function chooseItem(word, others, toScript) {
  const pool = shuffle(others.filter((x) => x.id !== word.id && x.gloss && x.gloss !== word.gloss && x.scriptForm !== word.scriptForm));
  const same = pool.filter((x) => x.category === word.category);
  const key = toScript ? "scriptForm" : "gloss";
  const options = distinctOptions([word[key], ...distinctOptions([...same, ...pool].map((x) => x[key])).slice(0, 3)]);
  if (options.length < 2) return null;
  return {
    type: "mcq",
    direction: toScript ? "gloss->script" : "script->gloss",
    prompt: toScript ? `Choose the ${script().name} word` : "Choose the translation",
    stimulus: toScript ? word.gloss : word.scriptForm,
    stimulusIsScript: !toScript,
    options: shuffle(options),
    answer: word[key],
    optionIsScript: toScript,
  };
}

function typeItem(word, pointed) {
  return {
    type: "translate-phrase",
    prompt: pointed ? script().fullPrompt : script().plainPrompt,
    stimulus: word.gloss,
    stimulusIsScript: false,
    accepted: [word.scriptForm],
    answerIsScript: true,
    ...(pointed ? { pointing: "required" } : {}),
  };
}

function tag(item, rung, ids, id) {
  const wordIds = item.words ? ids.filter((x) => Object.values(item.words).includes(x)) : ids;
  return { ...item, id, wordRung: rung, rungLabel: `Words · ${wordRungs()[rung]}`, wordIds };
}

export function wordItemsFor(rung, words, distractors) {
  const items = [];
  if (rung === 1) {
    const match = getType("match-by-line");
    let rest = [...words];
    while (rest.length >= 3) {
      const chunk = rest.slice(0, 5);
      rest = rest.slice(5);
      if (rest.length > 0 && rest.length < 3 && chunk.length === 5) {
        rest = [...chunk.slice(3), ...rest];
        chunk.length = 3;
      }
      const made = match.generate({ count: chunk.length, extra: 2, direction: "random", distractors }, chunk);
      if (made.length) items.push(tag(made[0], 1, chunk.map((w) => w.id), `w1-m-${chunk.map((w) => w.id).join("+")}`));
    }
    for (const w of rest) {
      const it = chooseItem(w, [...words, ...distractors], false);
      if (it) items.push(tag(it, 1, [w.id], `w1-${w.id}`));
    }
    return items;
  }
  for (const w of words) {
    const it = rung === 2 ? chooseItem(w, [...words, ...distractors], true) : typeItem(w, rung === 4);
    if (it) items.push(tag(it, rung, [w.id], `w${rung}-${w.id}`));
  }
  return items;
}

export function wordSummary(words, done) {
  const out = [];
  for (let r = 1; r <= WORD_RUNG_COUNT; r++) {
    const set = new Set((done && done[r]) || []);
    out.push({ rung: r, label: wordRungs()[r], total: words.length, done: words.filter((w) => set.has(w.id)).length });
  }
  return out;
}

export function openRung(words, done) {
  for (let r = 1; r <= WORD_RUNG_COUNT; r++) {
    const set = new Set((done && done[r]) || []);
    if (words.some((w) => !set.has(w.id))) return r;
  }
  return null;
}

// A session of one word rung: words not yet right on it first, then the rest; a match set counts as one item.
export function wordsSession(words, done, rung, distractors, size = 10) {
  const set = new Set((done && done[rung]) || []);
  const open = shuffle(words.filter((w) => !set.has(w.id)));
  const known = shuffle(words.filter((w) => set.has(w.id)));
  const cap = rung === 1 ? size * 5 : size;
  const chosen = [...open, ...known].slice(0, Math.max(cap, Math.min(words.length, 3)));
  return wordItemsFor(rung, chosen, distractors).slice(0, size);
}

// Two or three word questions to open a book-exercise session: one match set and choose items.
export function warmupWords(words, done, distractors, count = 3) {
  if (!words.length) return [];
  const set = new Set((done && done[1]) || []);
  const order = [...shuffle(words.filter((w) => !set.has(w.id))), ...shuffle(words.filter((w) => set.has(w.id)))];
  const items = [];
  const plurals = words.filter((w) => w.plural);
  if (plurals.length >= 3 && random() < 0.5) {
    const made = getType("match-by-line").generate({ count: 5, extra: 2, kind: "plural", distractors: distractors.filter((w) => w.plural) }, plurals);
    if (made.length) items.push({ ...made[0], id: `wp-${Object.values(made[0].words).join("+")}` });
  } else if (order.length >= 3) {
    const chunk = order.slice(0, 5);
    const made = getType("match-by-line").generate({ count: chunk.length, extra: 2, direction: "random", distractors }, chunk);
    if (made.length) items.push(tag(made[0], 1, chunk.map((w) => w.id), `w1-m-${chunk.map((w) => w.id).join("+")}`));
  }
  for (const w of order.slice(0, count)) {
    if (items.length >= count) break;
    const it = chooseItem(w, [...words, ...distractors], items.length % 2 === 1);
    if (it) items.push(tag(it, it.optionIsScript ? 2 : 1, [w.id], `w${it.optionIsScript ? 2 : 1}-${w.id}`));
  }
  return items;
}
