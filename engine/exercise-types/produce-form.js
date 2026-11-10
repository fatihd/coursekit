import { el, scriptSpan } from "../dom.js";
import { shuffle } from "./util.js";
import { distinctOptions } from "./mcq.js";

// Flatten verb lemmas + forms already taught by `unitN` into {scriptForm, parse, root}.
function verbCandidates(lemmas, unitN) {
  const out = [];
  for (const L of lemmas) {
    if (L.unit <= unitN && L.extra && L.extra.parse && L.root) {
      out.push({ scriptForm: L.scriptForm, parse: L.extra.parse, root: L.root });
    }
    for (const f of (L.extra && L.extra.forms) || []) {
      if ((f.unit || 0) <= unitN && f.scriptForm && f.parse && L.root) {
        out.push({ scriptForm: f.scriptForm, parse: f.parse, root: L.root });
      }
    }
  }
  return out;
}

export default {
  id: "produce-form",

  generate(params, pool, unitN) {
    const only = params.only || "both";
    const items = [];

    if (only !== "verb") {
      const nouns = pool.filter((x) => x.category === "noun" && x.plural);
      const pluralTarget = Math.min(only === "noun" ? (params.count || 2) : Math.round((params.count || 2) / 2), nouns.length);
      let n = 0;
      for (const correct of shuffle(nouns)) {
        if (n >= pluralTarget) break;
        const options = distinctOptions([
          correct.plural,
          ...nouns.filter((x) => x.id !== correct.id).map((x) => x.plural),
        ]).slice(0, 4);
        if (options.length < 2) continue;
        items.push({
          type: "produce-form",
          variant: "noun-plural",
          prompt: "Choose the plural of this noun",
          stimulus: correct.scriptForm,
          stimulusIsScript: true,
          optionIsScript: true,
          options: shuffle(options),
          answer: correct.plural,
        });
        n += 1;
      }
    }

    if (only !== "noun") {
      const verbs = verbCandidates(pool, unitN);
      const verbTarget = Math.min((params.count || 2) - (only === "noun" ? 0 : Math.round((params.count || 2) / 2)), verbs.length);
      let n = 0;
      for (const correct of shuffle(verbs)) {
        if (n >= verbTarget) break;
        const stimulus = `${correct.parse} (root ${correct.root})`;
        const options = distinctOptions([
          correct.scriptForm,
          ...verbs.filter((c) => c.scriptForm !== correct.scriptForm).map((c) => c.scriptForm),
        ]).slice(0, 4);
        if (options.length < 2) continue;
        items.push({
          type: "produce-form",
          variant: "verb-form",
          prompt: "Choose the Hebrew form that matches this description",
          stimulus,
          stimulusIsScript: false,
          optionIsScript: true,
          options: shuffle(options),
          answer: correct.scriptForm,
        });
        n += 1;
      }
    }

    return items;
  },

  render(item, ctx) {
    const root = el("div", "ex ex--produce");
    const prompt = el("div", "ex-prompt");
    const stim = el("span", "ex-stimulus");
    if (item.stimulusIsScript) stim.appendChild(scriptSpan(ctx.course, item.stimulus));
    else stim.textContent = item.stimulus;
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
