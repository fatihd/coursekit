import { el, scriptSpan } from "../dom.js";

export const NOT_APPLICABLE = "—";

function fieldMatches(reading, field, value) {
  return !(field in reading) || reading[field] === value;
}

function bestReading(item, answer) {
  let best = null;
  let bestScore = -1;
  for (const reading of item.readings) {
    const score = item.fields.filter((f) => fieldMatches(reading, f.key, answer[f.key])).length;
    if (score > bestScore) {
      best = reading;
      bestScore = score;
    }
  }
  return best;
}

function describe(item, reading) {
  return item.fields
    .filter((f) => f.key in reading)
    .map((f) => `${f.label.toLowerCase()} ${reading[f.key]}`)
    .join(", ");
}

export default {
  id: "parse-form",

  generate() {
    return [];
  },

  render(item, ctx) {
    const root = el("div", "ex ex--parse-form");
    if (item.prompt) root.appendChild(el("p", "ex-instruction", item.prompt));
    const prompt = el("div", "ex-prompt");
    const stim = el("span", "ex-stimulus");
    if (item.stimulusIsScript) stim.appendChild(scriptSpan(ctx.course, item.stimulus));
    else stim.textContent = item.stimulus;
    prompt.appendChild(stim);
    root.appendChild(prompt);

    const grid = el("div", "ex-parse-grid");
    for (const field of item.fields) {
      const label = el("label", "ex-parse-field");
      label.appendChild(el("span", "ex-parse-label", field.label));
      const sel = document.createElement("select");
      sel.className = "ex-select";
      sel.dataset.field = field.key;
      if (field.isScript) sel.dir = "rtl";
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "— choose —";
      sel.appendChild(blank);
      for (const o of [...field.options, NOT_APPLICABLE]) {
        const opt = document.createElement("option");
        opt.value = o;
        opt.textContent = o === NOT_APPLICABLE ? "— (not applicable)" : o;
        sel.appendChild(opt);
      }
      label.appendChild(sel);
      grid.appendChild(label);
    }
    root.appendChild(grid);
    return root;
  },

  collect(node) {
    const result = {};
    for (const sel of node.querySelectorAll(".ex-select")) {
      if (!sel.value) return null;
      result[sel.dataset.field] = sel.value;
    }
    return result;
  },

  grade(item, answer) {
    const correct = item.readings.some((r) => item.fields.every((f) => fieldMatches(r, f.key, answer[f.key])));
    const reading = bestReading(item, answer);
    const fields = {};
    for (const f of item.fields) fields[f.key] = fieldMatches(reading, f.key, answer[f.key]);
    const wrong = item.fields.filter((f) => !fields[f.key]).map((f) => f.label.toLowerCase());
    const expected = describe(item, reading) + (wrong.length ? ` (check: ${wrong.join(", ")})` : "");
    return { correct, expected, fields };
  },

  hint(node, item, answer, result) {
    this.annotate(node, item, answer, result);
    return "Fields outlined red are wrong.";
  },

  annotate(node, item, answer, result) {
    for (const sel of node.querySelectorAll(".ex-select")) {
      sel.classList.remove("ex-select--ok", "ex-select--no");
      const ok = result.fields && result.fields[sel.dataset.field];
      sel.classList.add(ok ? "ex-select--ok" : "ex-select--no");
    }
  },
};
