import { el, scriptSpan } from "../dom.js";
import { shuffle } from "./util.js";

const DIRECTIONS = {
  "script->gloss": {
    stimulusKey: "scriptForm",
    optionKey: "gloss",
    stimulusIsScript: true,
    optionIsScript: false,
  },
  "gloss->script": {
    stimulusKey: "gloss",
    optionKey: "scriptForm",
    stimulusIsScript: false,
    optionIsScript: true,
  },
  "translit->script": {
    stimulusKey: "transliteration",
    optionKey: "scriptForm",
    stimulusIsScript: false,
    optionIsScript: true,
  },
};

// Keep the first occurrence of each value; drop empties.
export function distinctOptions(values) {
  const seen = new Set();
  const out = [];
  for (const v of values) {
    if (v === null || v === undefined || v === "") continue;
    if (seen.has(v)) continue;
    seen.add(v);
    out.push(v);
  }
  return out;
}

export default {
  id: "mcq",

  generate(params, pool) {
    const count = params.count || 12;
    const directions = params.directions || ["script->gloss", "gloss->script"];
    const items = [];
    const shuffled = shuffle(pool);
    let emitted = 0;
    for (let i = 0; i < shuffled.length && emitted < count; i++) {
      const correct = shuffled[i];
      const direction = directions[i % directions.length];
      const cfg = DIRECTIONS[direction];
      const correctValue = correct[cfg.optionKey];
      if (!correctValue) continue;

      const distractorValues = distinctOptions(
        shuffled
          .filter((x) => x.id !== correct.id)
          .map((x) => x[cfg.optionKey]),
      );
      // Correct answer plus up to three distinct distractors. Never ship a
      // single-option MCQ: require at least one real, visibly distinct wrong answer.
      const options = distinctOptions([correctValue, ...distractorValues]).slice(0, 4);
      if (options.length < 2) continue;

      items.push({
        type: "mcq",
        direction,
        stimulus: correct[cfg.stimulusKey],
        options: shuffle(options),
        answer: correctValue,
        stimulusIsScript: cfg.stimulusIsScript,
        optionIsScript: cfg.optionIsScript,
      });
      emitted += 1;
    }
    return items;
  },

  render(item, ctx) {
    const root = el("div", "ex ex--mcq");

    if (item.prompt) root.appendChild(el("p", "ex-instruction", item.prompt));
    const prompt = el("div", "ex-prompt");
    const stim = el("span", "ex-stimulus");
    if (item.stimulusIsScript) stim.appendChild(scriptSpan(ctx.course, item.stimulus));
    else stim.textContent = item.stimulus;
    prompt.appendChild(stim);
    root.appendChild(prompt);

    const options = el("div", "ex-options");
    for (const opt of item.options) {
      const btn = document.createElement("button");
      btn.className = "ex-option";
      btn.dataset.value = opt;
      btn.addEventListener("click", () => {
        options.querySelectorAll(".ex-option").forEach((b) => b.classList.remove("ex-option--selected"));
        btn.classList.add("ex-option--selected");
      });
      if (item.optionIsScript) btn.appendChild(scriptSpan(ctx.course, opt));
      else btn.textContent = opt;
      options.appendChild(btn);
    }
    root.appendChild(options);
    return root;
  },

  collect(node) {
    const sel = node.querySelector(".ex-option--selected");
    return sel ? sel.dataset.value : null;
  },

  grade(item, answer) {
    return { correct: answer === item.answer, expected: item.answer };
  },
};
