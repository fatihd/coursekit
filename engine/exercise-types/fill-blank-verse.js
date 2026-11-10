import { el, scriptSpan } from "../dom.js";

export default {
  id: "fill-blank-verse",

  generate() {
    return [
      {
        type: "fill-blank-verse",
        prompt: "Fill the blank with the correct word",
        before: "וַיִּשְׁמַע",
        after: "אֶת־קוֹלוֹ",
        blankLabel: "____",
        options: ["קוֹל", "קוֹלוֹ", "קָל", "קוֹלָם"],
        answer: "קוֹלוֹ",
        isScript: true,
      },
    ];
  },

  render(item, ctx) {
    const root = el("div", "ex ex--blank");
    root.appendChild(el("p", "ex-prompt", item.prompt));

    const line = el("div", "ex-blank-verse");
    line.appendChild(scriptSpan(ctx.course, item.before));
    line.appendChild(el("span", "ex-blank-marker", ` ${item.blankLabel || "____"} `));
    line.appendChild(scriptSpan(ctx.course, item.after));
    root.appendChild(line);

    const opts = el("div", "ex-options");
    for (const o of item.options) {
      const btn = document.createElement("button");
      btn.className = "ex-option";
      btn.dataset.value = o;
      btn.appendChild(scriptSpan(ctx.course, o));
      btn.addEventListener("click", () => {
        opts.querySelectorAll(".ex-option").forEach((b) => b.classList.remove("ex-option--selected"));
        btn.classList.add("ex-option--selected");
      });
      opts.appendChild(btn);
    }
    root.appendChild(opts);
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
