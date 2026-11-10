import { el } from "../dom.js";

export default {
  id: "scan-text",

  generate() {
    return [
      {
        type: "scan-text",
        prompt: "Click the words that contain a definite article (ה)",
        tokens: ["בְּרֵאשִׁית", "בָּרָא", "אֱלֹהִים", "הַשָּׁמַיִם", "וְאֵת", "הָאָרֶץ"],
        answer: ["הַשָּׁמַיִם", "הָאָרֶץ"],
        isScript: true,
      },
    ];
  },

  render(item, ctx) {
    const root = el("div", "ex ex--scan");
    root.appendChild(el("p", "ex-prompt", item.prompt));

    const line = el("div", "ex-scan-text");
    for (const t of item.tokens) {
      const w = document.createElement("span");
      w.className = "ex-token";
      w.dataset.value = t;
      if (item.isScript) {
        w.dir = "rtl";
        w.classList.add("script");
      }
      w.textContent = t;
      w.addEventListener("click", () => w.classList.toggle("ex-token--selected"));
      line.appendChild(w);
      line.appendChild(document.createTextNode(" "));
    }
    root.appendChild(line);
    return root;
  },

  collect(node) {
    const sel = [...node.querySelectorAll(".ex-token--selected")].map((s) => s.dataset.value);
    return sel.length ? sel : null;
  },

  grade(item, answer) {
    const s = new Set(answer);
    const correct = answer.length === item.answer.length && item.answer.every((a) => s.has(a));
    return { correct, expected: item.answer.join(", ") };
  },
};
