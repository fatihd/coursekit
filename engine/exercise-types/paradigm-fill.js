import { el, scriptSpan } from "../dom.js";

export default {
  id: "paradigm-fill",

  generate() {
    return [
      {
        type: "paradigm-fill",
        prompt: "Complete the Qatal paradigm (Qal, root קטל)",
        rows: [
          { label: "1cs", answer: "קָטַלְתִּי", options: ["קָטַלְתִּי", "קָטַלְתָּ", "קָטְלָה", "קָטַל"] },
          { label: "2ms", answer: "קָטַלְתָּ", options: ["קָטַלְתִּי", "קָטַלְתָּ", "קָטְלָה", "קָטַל"] },
          { label: "3fs", answer: "קָטְלָה", options: ["קָטַלְתִּי", "קָטַלְתָּ", "קָטְלָה", "קָטַל"] },
        ],
        isScript: true,
      },
    ];
  },

  render(item, ctx) {
    const root = el("div", "ex ex--paradigm-fill");
    root.appendChild(el("p", "ex-prompt", item.prompt));

    const table = document.createElement("table");
    table.className = "ex-table";
    for (const row of item.rows) {
      const tr = document.createElement("tr");
      tr.appendChild(el("td", "ex-cell-label", row.label));
      const td = document.createElement("td");
      const sel = document.createElement("select");
      sel.className = "ex-select";
      sel.dataset.label = row.label;
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "— choose —";
      sel.appendChild(blank);
      for (const o of row.options) {
        const opt = document.createElement("option");
        opt.value = o;
        opt.textContent = o;
        sel.appendChild(opt);
      }
      td.appendChild(sel);
      tr.appendChild(td);
      table.appendChild(tr);
    }
    root.appendChild(table);
    return root;
  },

  collect(node) {
    const result = {};
    for (const sel of node.querySelectorAll(".ex-select")) {
      if (!sel.value) return null;
      result[sel.dataset.label] = sel.value;
    }
    return result;
  },

  grade(item, answer) {
    const correct = item.rows.every((r) => answer[r.label] === r.answer);
    return {
      correct,
      expected: item.rows.map((r) => `${r.label} = ${r.answer}`).join(" · "),
    };
  },
};
