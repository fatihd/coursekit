import { el, scriptSpan } from "../dom.js";

export default {
  id: "multi-translation",

  generate() {
    return [
      {
        type: "multi-translation",
        prompt: "Select every valid translation of this Qatal form",
        stimulus: "קָטַל",
        stimulusIsScript: true,
        options: [
          "he killed",
          "he will kill",
          "he has killed",
          "he kills",
        ],
        answer: ["he killed", "he has killed"],
      },
    ];
  },

  render(item, ctx) {
    const root = el("div", "ex ex--multi");

    root.appendChild(el("p", "ex-prompt", item.prompt));

    const stim = el("div", "ex-stimulus");
    if (item.stimulusIsScript) stim.appendChild(scriptSpan(ctx.course, item.stimulus));
    else stim.textContent = item.stimulus;
    root.appendChild(stim);

    const opts = el("div", "ex-options");
    for (const o of item.options) {
      const btn = document.createElement("button");
      btn.className = "ex-option";
      btn.dataset.value = o;
      btn.textContent = o;
      btn.addEventListener("click", () => btn.classList.toggle("ex-option--selected"));
      opts.appendChild(btn);
    }
    root.appendChild(opts);
    return root;
  },

  collect(node) {
    const sel = [...node.querySelectorAll(".ex-option--selected")].map((b) => b.dataset.value);
    return sel.length ? sel : null;
  },

  grade(item, answer) {
    const s = new Set(answer);
    const correct = answer.length === item.answer.length && item.answer.every((a) => s.has(a));
    return { correct, expected: item.answer.join(", ") };
  },
};
