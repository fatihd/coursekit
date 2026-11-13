import { el, scriptSpan } from "../dom.js";
import { script, usesKeyboard } from "../script.js";
import { normalize, normalizeEnglish, shuffle } from "./util.js";

function bestExpected(item, answer) {
  const { full } = script();
  const mine = full(answer).split(" ");
  let best = item.accepted[0];
  let bestScore = -1;
  for (const acc of item.accepted) {
    const theirs = full(acc).split(" ");
    const score = mine.filter((w, i) => w === theirs[i]).length - Math.abs(mine.length - theirs.length);
    if (score > bestScore) {
      best = acc;
      bestScore = score;
    }
  }
  return best;
}

export default {
  id: "translate-phrase",

  generate(params, pool) {
    const count = Math.min(params.count || 3, pool.length);
    return shuffle(pool)
      .slice(0, count)
      .map((x) => ({
        type: "translate-phrase",
        prompt: `Translate this ${script().name} word into English`,
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
    if (item.answerIsScript && ctx.course.script && usesKeyboard(ctx.course)) {
      input.classList.add("hebrew-input");
      input.dir = script().dir;
      input.lang = ctx.course.script.code || script().lang;
    }
    root.appendChild(input);
    return root;
  },

  collect(node) {
    const input = node.querySelector(".ex-text");
    return input && input.value.trim() ? input.value : null;
  },

  grade(item, answer) {
    if (item.answerIsScript && item.pointing === "required") {
      const { full, hasMarks, missing } = script();
      const a = full(answer);
      const correct = item.accepted.some((acc) => full(acc) === a);
      const expected = correct ? item.accepted[0] : bestExpected(item, answer);
      const message = hasMarks(answer) ? null : missing;
      return { correct, expected, message };
    }
    if (item.answerIsScript) {
      const { plain } = script();
      const a = plain(answer);
      const correct = item.accepted.some((acc) => plain(acc) === a);
      return { correct, expected: item.accepted[0] };
    }
    if (item.selfCheck) {
      const a = normalizeEnglish(answer);
      const correct = item.accepted.some((acc) => normalizeEnglish(acc) === a);
      return { correct, expected: item.accepted[0], selfCheck: !correct };
    }
    const a = normalize(answer);
    const correct = item.accepted.some((acc) => normalize(acc) === a);
    return { correct, expected: item.accepted.join(" / ") };
  },

  hint(node, item, answer, result) {
    if (item.answerIsScript && item.pointing === "required") {
      this.annotate(node, item, answer, result);
      return script().marked;
    }
    if (item.answerIsScript) {
      const first = (item.accepted[0] || "").split(/\s+/).map((w) => script().strip(w).charAt(0)).filter(Boolean);
      return first.length ? `It starts with ${first.join(" … ")}.` : null;
    }
    return null;
  },

  annotate(node, item, answer, result) {
    const old = node.querySelector(".ex-pointing");
    if (old) old.remove();
    if (!(item.answerIsScript && item.pointing === "required") || result.correct) return;
    const box = el("div", "ex-pointing");
    box.appendChild(el("span", "ex-pointing-label", script().yours));
    const line = el("span", "ex-pointing-words script");
    line.dir = script().dir;
    script().diff(answer, result.expected).forEach((w, i) => {
      if (i) line.appendChild(document.createTextNode(" "));
      const word = el("span", w.ok ? "pt-word" : "pt-word pt-word--no");
      for (const c of w.clusters) word.appendChild(el("span", c.ok ? "pt-ok" : "pt-no", c.text));
      line.appendChild(word);
    });
    box.appendChild(line);
    node.appendChild(box);
  },
};
