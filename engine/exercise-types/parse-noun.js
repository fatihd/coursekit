import { el, scriptSpan } from "../dom.js";
import { shuffle } from "./util.js";
import { distinctOptions } from "./mcq.js";

const GENDER_WORDS = { m: "masculine", f: "feminine", c: "common" };
const NUMBER_WORDS = { s: "singular", p: "plural", d: "dual" };

export function nounLabel(item) {
  const parts = [];
  if (GENDER_WORDS[item.gender]) parts.push(GENDER_WORDS[item.gender]);
  if (NUMBER_WORDS[item.number]) parts.push(NUMBER_WORDS[item.number]);
  return parts.join(" ") || null;
}

export default {
  id: "parse-noun",

  generate(params, pool) {
    const nouns = pool.filter((x) => x.category === "noun" && nounLabel(x));
    const count = Math.min(params.count || 2, nouns.length);
    const items = [];
    for (const correct of shuffle(nouns)) {
      if (items.length >= count) break;
      const label = nounLabel(correct);
      const options = distinctOptions([
        label,
        ...nouns.filter((x) => x.id !== correct.id).map((x) => nounLabel(x)),
      ]).slice(0, 4);
      if (options.length < 2) continue;
      items.push({
        type: "parse-noun",
        prompt: "Choose the gender and number of this noun",
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
    const root = el("div", "ex ex--parse-noun");
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
