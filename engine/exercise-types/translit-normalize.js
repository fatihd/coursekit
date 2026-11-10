import { el, scriptSpan } from "../dom.js";
import { normalize, shuffle } from "./util.js";

const DIRECTIONS = {
  "translit->script": {
    stimulusKey: "transliteration",
    answerKey: "scriptForm",
    prompt: "Type the pointed Hebrew word for this transliteration",
    stimulusIsScript: false,
    answerIsScript: true,
    inputDir: "rtl",
  },
  "script->translit": {
    stimulusKey: "scriptForm",
    answerKey: "transliteration",
    prompt: "Transliterate this Hebrew word into Latin script",
    stimulusIsScript: true,
    answerIsScript: false,
    inputDir: "ltr",
  },
};

export default {
  id: "translit-normalize",

  generate(params, pool) {
    const count = Math.min(params.count || 3, pool.length);
    const direction = params.direction || "translit->script";
    const cfg = DIRECTIONS[direction] || DIRECTIONS["translit->script"];
    if (count < 1) return demo(pool, cfg);
    return shuffle(pool)
      .slice(0, count)
      .map((x) => ({
        type: "translit-normalize",
        direction,
        prompt: cfg.prompt,
        stimulus: x[cfg.stimulusKey],
        stimulusIsScript: cfg.stimulusIsScript,
        answer: x[cfg.answerKey],
        answerIsScript: cfg.answerIsScript,
      }));
  },

  render(item, ctx) {
    const root = el("div", "ex ex--translit");
    root.appendChild(el("p", "ex-prompt", item.prompt));

    const stim = el("div", "ex-stimulus");
    if (item.stimulusIsScript) stim.appendChild(scriptSpan(ctx.course, item.stimulus));
    else stim.textContent = item.stimulus;
    root.appendChild(stim);

    const input = document.createElement("input");
    input.className = "ex-text hebrew-input";
    input.type = "text";
    input.dir = item.answerIsScript ? "rtl" : "ltr";
    input.autocomplete = "off";
    input.spellcheck = false;
    root.appendChild(input);
    return root;
  },

  collect(node) {
    const input = node.querySelector(".hebrew-input");
    return input && input.value.trim() ? input.value : null;
  },

  grade(item, answer) {
    const a = answer.normalize("NFC");
    const exp = item.answer.normalize("NFC");
    let correct;
    if (item.answerIsScript) {
      correct = a === exp || normalize(answer) === normalize(item.stimulus);
    } else {
      correct = normalize(a) === normalize(exp);
    }
    return { correct, expected: item.answer };
  },
};

function demo(pool, cfg) {
  const x = pool.find((i) => i[cfg.stimulusKey] && i[cfg.answerKey]) || {
    transliteration: "dābār",
    scriptForm: "דָּבָר",
    gloss: "word, thing",
  };
  return [
    {
      type: "translit-normalize",
      direction: cfg === DIRECTIONS["script->translit"] ? "script->translit" : "translit->script",
      prompt: cfg.prompt,
      stimulus: x[cfg.stimulusKey],
      stimulusIsScript: cfg.stimulusIsScript,
      answer: x[cfg.answerKey],
      answerIsScript: cfg.answerIsScript,
    },
  ];
}