import { el } from "../dom.js";
import { normalize, shuffle } from "./util.js";

export default {
  id: "dictation",

  generate(params, pool) {
    const count = Math.min(params.count || 2, pool.length);
    return shuffle(pool)
      .slice(0, count)
      .map((x) => ({
        type: "dictation",
        prompt: "Type the Hebrew word for this gloss",
        stimulus: x.gloss,
        stimulusIsScript: false,
        answer: x.scriptForm,
        transliteration: x.transliteration,
      }));
  },

  render(item, ctx) {
    const root = el("div", "ex ex--dictation");
    root.appendChild(el("p", "ex-prompt", item.prompt));

    root.appendChild(el("div", "ex-stimulus", item.stimulus));

    const input = document.createElement("input");
    input.className = "ex-text hebrew-input";
    input.type = "text";
    input.dir = "rtl";
    input.autocomplete = "off";
    input.spellcheck = false;
    root.appendChild(input);

    root.appendChild(el("p", "ex-hint", "Use the on-screen keyboard, or type the transliteration."));
    return root;
  },

  collect(node) {
    const input = node.querySelector(".hebrew-input");
    return input && input.value.trim() ? input.value : null;
  },

  grade(item, answer) {
    const a = answer.normalize("NFC");
    const exp = item.answer.normalize("NFC");
    const translitOk = item.transliteration && normalize(answer) === normalize(item.transliteration);
    const correct = a === exp || translitOk;
    return { correct, expected: item.answer };
  },
};
