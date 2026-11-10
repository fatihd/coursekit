import { el, scriptSpan } from "../dom.js";
import { normalize, normalizeHebrew, shuffle } from "./util.js";

export default {
  id: "translate-phrase",

  generate(params, pool) {
    const count = Math.min(params.count || 3, pool.length);
    return shuffle(pool)
      .slice(0, count)
      .map((x) => ({
        type: "translate-phrase",
        prompt: "Translate this Hebrew word into English",
        stimulus: x.scriptForm,
        stimulusIsScript: true,
        accepted: [x.gloss],
      }));
  },

  render(item, ctx) {
    const root = el("div", "ex ex--translate");
    root.appendChild(el("p", "ex-prompt", item.prompt));

    const stim = el("div", "ex-stimulus");
    if (item.stimulusIsScript) stim.appendChild(scriptSpan(ctx.course, item.stimulus));
    else stim.textContent = item.stimulus;
    root.appendChild(stim);

    const input = document.createElement("input");
    input.className = "ex-text";
    input.type = "text";
    input.autocomplete = "off";
    input.spellcheck = false;
    if (item.answerIsScript && ctx.course.script && ctx.course.script.direction === "rtl") {
      input.classList.add("hebrew-input");
      input.dir = "rtl";
      input.lang = ctx.course.script.code || "he";
    }
    root.appendChild(input);
    return root;
  },

  collect(node) {
    const input = node.querySelector(".ex-text");
    return input && input.value.trim() ? input.value : null;
  },

  grade(item, answer) {
    if (item.answerIsScript) {
      const a = normalizeHebrew(answer);
      const correct = item.accepted.some((acc) => normalizeHebrew(acc) === a);
      return { correct, expected: item.accepted[0] };
    }
    const a = normalize(answer);
    const correct = item.accepted.some((acc) => normalize(acc) === a);
    return { correct, expected: item.accepted.join(" / ") };
  },
};
