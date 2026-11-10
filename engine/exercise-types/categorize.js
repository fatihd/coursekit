import { el, scriptSpan } from "../dom.js";
import { shuffle } from "./util.js";

export default {
  id: "categorize",

  generate(params, pool) {
    const picked = shuffle(pool).slice(0, params.count || 6);
    const cats = [...new Set(picked.map((x) => x.category))].slice(0, 3);
    // A categorization needs at least two categories to be non-trivial; a
    // single-category pool (e.g. an all-verb unit) would produce a one-option
    // sort, so yield nothing instead.
    if (cats.length < 2) return [];
    const words = shuffle(
      picked.filter((x) => cats.includes(x.category)).slice(0, params.count || 6),
    ).map((x) => ({ text: x.scriptForm, cat: x.category }));
    return [
      {
        type: "categorize",
        prompt: "Sort each word into its part of speech",
        columns: cats,
        words,
        isScript: true,
      },
    ];
  },

  render(item, ctx) {
    const root = el("div", "ex ex--categorize");
    root.appendChild(el("p", "ex-prompt", item.prompt));

    const rows = el("div", "ex-cat-rows");
    for (const w of item.words) {
      const row = el("div", "ex-cat-row");
      row.appendChild(item.isScript ? scriptSpan(ctx.course, w.text) : el("span", null, w.text));

      const sel = document.createElement("select");
      sel.className = "ex-select";
      sel.dataset.word = w.text;
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "— choose —";
      sel.appendChild(blank);
      for (const c of item.columns) {
        const o = document.createElement("option");
        o.value = c;
        o.textContent = c;
        sel.appendChild(o);
      }
      row.appendChild(sel);
      rows.appendChild(row);
    }
    root.appendChild(rows);
    return root;
  },

  collect(node) {
    const result = {};
    for (const sel of node.querySelectorAll(".ex-select")) {
      if (!sel.value) return null;
      result[sel.dataset.word] = sel.value;
    }
    return result;
  },

  grade(item, answer) {
    const correct = item.words.every((w) => answer[w.text] === w.cat);
    return {
      correct,
      expected: item.words.map((w) => `${w.text} = ${w.cat}`).join(" · "),
    };
  },
};
