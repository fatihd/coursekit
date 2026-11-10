import { el, scriptSpan } from "../dom.js";
import { shuffle } from "./util.js";

export default {
  id: "match-by-line",

  generate(params, pool) {
    const uniquePool = [...new Map(pool.map((item) => [item.scriptForm, item])).values()];
    const count = Math.min(params.count || 4, uniquePool.length);
    const picked = shuffle(uniquePool).slice(0, count);
    const answer = {};
    picked.forEach((x) => {
      answer[x.scriptForm] = x.gloss;
    });
    return [
      {
        type: "match-by-line",
        prompt: "Match each Hebrew word to its translation",
        left: picked.map((x) => x.scriptForm),
        right: shuffle(picked.map((x) => x.gloss)),
        answer,
        leftIsScript: true,
      },
    ];
  },

  render(item, ctx) {
    const root = el("div", "ex ex--match");
    root.appendChild(el("p", "ex-prompt", item.prompt));

    const rows = el("div", "ex-match-rows");
    for (const l of item.left) {
      const row = el("div", "ex-match-row");
      row.appendChild(item.leftIsScript ? scriptSpan(ctx.course, l) : el("span", null, l));

      const sel = document.createElement("select");
      sel.className = "ex-select";
      sel.dataset.left = l;
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "— choose —";
      sel.appendChild(blank);
      for (const r of item.right) {
        const o = document.createElement("option");
        o.value = r;
        o.textContent = r;
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
      result[sel.dataset.left] = sel.value;
    }
    return result;
  },

  grade(item, answer) {
    const correct = item.left.every((l) => answer[l] === item.answer[l]);
    return {
      correct,
      expected: item.left.map((l) => `${l} = ${item.answer[l]}`).join(" · "),
    };
  },
};
