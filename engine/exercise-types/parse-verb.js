import { el, scriptSpan } from "../dom.js";
import { shuffle } from "./util.js";
import { distinctOptions } from "./mcq.js";

// Flatten verb lemmas + their embedded forms into parse candidates already taught
// by `unitN`. The lemma itself is the Qatal 3ms citation; forms carry their own unit.
function candidates(lemmas, unitN) {
  const out = [];
  for (const L of lemmas) {
    if (L.unit <= unitN && L.extra && L.extra.parse) {
      out.push({ scriptForm: L.scriptForm, parse: L.extra.parse });
    }
    for (const f of (L.extra && L.extra.forms) || []) {
      if ((f.unit || 0) <= unitN && f.scriptForm && f.parse) {
        out.push({ scriptForm: f.scriptForm, parse: f.parse });
      }
    }
  }
  return out;
}

export default {
  id: "parse-verb",

  generate(params, pool, unitN) {
    const cands = candidates(pool, unitN);
    const count = Math.min(params.count || 2, cands.length);
    const items = [];
    for (const correct of shuffle(cands)) {
      if (items.length >= count) break;
      const label = correct.parse;
      const options = distinctOptions([
        label,
        ...cands.filter((c) => c.parse !== label).map((c) => c.parse),
      ]).slice(0, 4);
      if (options.length < 2) continue;
      items.push({
        type: "parse-verb",
        prompt: "Choose the stem, conjugation, person, gender and number of this verb",
        stimulus: correct.scriptForm,
        stimulusIsScript: true,
        optionIsScript: false,
        options: shuffle(options),
        answer: label,
      });
    }
    return items;
  },

  render(item, ctx) {
    const root = el("div", "ex ex--parse-verb");
    const prompt = el("div", "ex-prompt");
    const stim = el("span", "ex-stimulus");
    stim.appendChild(scriptSpan(ctx.course, item.stimulus));
    prompt.appendChild(stim);
    prompt.appendChild(el("span", "ex-prompt-text", ` ${item.prompt}`));
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
      btn.textContent = opt;
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
