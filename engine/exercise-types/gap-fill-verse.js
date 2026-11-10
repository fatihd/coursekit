import { el, scriptSpan } from "../dom.js";

export default {
  id: "gap-fill-verse",

  generate() {
    return [
      {
        type: "gap-fill-verse",
        prompt: "Fill each blank with the word from the bank",
        before: "וַיֹּאמֶר",
        blanks: [
          { word: "אֱלֹהִים", hint: "God" },
          { word: "מַיִם", hint: "waters" },
        ],
        after: "",
        bank: ["אֱלֹהִים", "מַיִם", "אָדָם", "אֶרֶץ", "אוֹר"],
      },
    ];
  },

  render(item, ctx) {
    const root = el("div", "ex ex--gaps");
    root.appendChild(el("p", "ex-prompt", item.prompt));

    const line = el("div", "ex-blank-verse ex-gap-verse");
    if (item.before) line.appendChild(scriptSpan(ctx.course, item.before));
    for (let i = 0; i < item.blanks.length; i++) {
      line.appendChild(el("span", "ex-blank-marker", " ____ "));
    }
    if (item.after) line.appendChild(scriptSpan(ctx.course, item.after));
    root.appendChild(line);

    const bank = el("div", "ex-gap-bank");
    const selects = [];
    for (let i = 0; i < item.blanks.length; i++) {
      const sel = document.createElement("select");
      sel.className = "ex-select ex-gap-select";
      sel.dataset.gap = i;
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = `— blank ${i + 1} —`;
      sel.appendChild(blank);
      for (const w of item.bank) {
        const o = document.createElement("option");
        o.value = w;
        const hint = item.blanks.find((b) => b.word === w);
        o.textContent = hint && hint.hint ? `${w} (${hint.hint})` : w;
        sel.appendChild(o);
      }
      selects.push(sel);
      bank.appendChild(sel);
    }
    root.appendChild(bank);
    return root;
  },

  collect(node) {
    const answers = [];
    for (const sel of node.querySelectorAll(".ex-gap-select")) {
      if (!sel.value) return null;
      answers.push(sel.value);
    }
    return answers;
  },

  grade(item, answers) {
    const expected = item.blanks.map((b) => b.word);
    const clean = answers && answers.length === expected.length ? answers : [];
    const correct = expected.every((w, i) => w === clean[i]);
    return { correct, expected: expected.join(" · ") };
  },
};