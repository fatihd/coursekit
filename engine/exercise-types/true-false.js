import { el, scriptSpan } from "../dom.js";

export default {
  id: "true-false",

  generate() {
    return [];
  },

  render(item, ctx) {
    const root = el("div", "ex ex--tf");
    if (item.prompt) root.appendChild(el("p", "ex-instruction", item.prompt));
    const prompt = el("div", "ex-prompt");
    const stim = el("span", "ex-stimulus");
    if (item.stimulusIsScript) stim.appendChild(scriptSpan(ctx.course, item.stimulus));
    else stim.textContent = item.stimulus;
    prompt.appendChild(stim);
    root.appendChild(prompt);
    const statement = el("p", "ex-statement", item.statement);
    statement.dir = "auto";
    root.appendChild(statement);
    const options = el("div", "ex-options ex-options--tf");
    for (const [value, label] of [["true", "True"], ["false", "False"]]) {
      const btn = el("button", "ex-option", label);
      btn.type = "button";
      btn.dataset.value = value;
      btn.addEventListener("click", () => {
        options.querySelectorAll(".ex-option").forEach((b) => b.classList.remove("ex-option--selected"));
        btn.classList.add("ex-option--selected");
      });
      options.appendChild(btn);
    }
    root.appendChild(options);
    return root;
  },

  collect(node) {
    const sel = node.querySelector(".ex-option--selected");
    return sel ? sel.dataset.value === "true" : null;
  },

  grade(item, answer) {
    const correct = answer === item.answer;
    const expected = item.answer ? "True — that is the translation." : `False — the translation is: ${item.expected}`;
    return { correct, expected };
  },
};
