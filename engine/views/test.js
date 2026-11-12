import { el } from "../dom.js";
import { getType } from "../exercise-types/index.js";
import { withSeed } from "../exercise-types/util.js";

export const PASS_MARK = 80;

function describeAnswer(item, answer) {
  if (answer === null || answer === undefined) return "—";
  if (item.type === "true-false") return answer === true || answer === "true" ? "True" : "False";
  if (answer && answer.pairs) return Object.entries(answer.pairs).map(([l, r]) => `${l} = ${r}`).join(" · ");
  if (typeof answer === "object") return Object.values(answer).filter(Boolean).join(", ");
  return String(answer);
}

function promptOf(item) {
  if (item.type === "true-false") return `${item.stimulus} — “${item.statement}”`;
  return item.stimulus || item.prompt || "";
}

function clock(started) {
  const s = Math.floor((Date.now() - started) / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function renderTest(root, ctx) {
  const { course, items } = ctx;
  root.replaceChildren();
  const wrap = el("div", "drill-wrap test-wrap");
  root.appendChild(wrap);

  const back = el("button", "back", ctx.backLabel || "← Roadmap");
  back.addEventListener("click", () => ctx.onBack());
  wrap.appendChild(back);
  wrap.appendChild(el("h1", "test-title", ctx.title));
  wrap.appendChild(el("p", "test-rules", `${items.length} questions. One attempt each, no hints; everything is checked at the end. Pass mark ${PASS_MARK}%.`));

  const bar = el("p", "drill-progress test-progress", "");
  const timer = el("span", "test-timer", "0:00");
  wrap.append(bar, timer);
  const stage = el("div", "drill-stage");
  const feedback = el("div", "drill-feedback");
  wrap.append(stage, feedback);

  const started = Date.now();
  const tick = setInterval(() => {
    if (!timer.isConnected) return clearInterval(tick);
    timer.textContent = clock(started);
  }, 1000);

  const answers = new Array(items.length).fill(null);
  let idx = 0;

  function renderQuestion() {
    const item = items[idx];
    const type = getType(item.type);
    bar.textContent = `Question ${idx + 1} of ${items.length}${item.sourceUnit ? ` · Unit ${item.sourceUnit}` : ""}`;
    stage.replaceChildren();
    feedback.replaceChildren();
    const node = withSeed(`${ctx.seed}:${idx}`, () => type.render(item, { course, exam: true }));
    stage.appendChild(node);
    const nextBtn = el("button", "gate-btn test-next", idx + 1 < items.length ? "Next →" : "Finish test");
    nextBtn.addEventListener("click", () => {
      const a = type.collect ? type.collect(node, item) : null;
      if (a === null || a === undefined) {
        if (!feedback.querySelector(".drill-hint")) feedback.prepend(el("p", "drill-hint", "Complete your answer first."));
        return;
      }
      answers[idx] = a;
      idx += 1;
      if (idx < items.length) renderQuestion();
      else finish();
    });
    feedback.appendChild(nextBtn);
    node.addEventListener("ex-complete", () => nextBtn.focus());
    const first = stage.querySelector(".ex-text, .hebrew-input, .ex-option, .ex-tile, select");
    if (first) first.focus();
  }

  function finish() {
    clearInterval(tick);
    const elapsed = clock(started);
    const results = items.map((item, i) => {
      const res = getType(item.type).grade(item, answers[i]);
      return { item, answer: answers[i], res, correct: res.selfCheck ? null : Boolean(res.correct) };
    });
    stage.replaceChildren();
    feedback.replaceChildren();
    bar.textContent = "";
    timer.textContent = `Time: ${elapsed}`;
    const summary = el("h2", "drill-result test-result", "");
    const note = el("p", "drill-result-note", "");
    stage.append(summary, note);
    const list = el("ol", "test-review");
    stage.appendChild(list);
    const done = el("button", "gate-btn test-done", "Save result");
    done.disabled = true;

    const refresh = () => {
      const open = results.filter((r) => r.correct === null).length;
      const right = results.filter((r) => r.correct === true).length;
      const pct = Math.round((100 * right) / Math.max(1, results.length));
      summary.textContent = `${right} / ${results.length} correct — ${pct}%`;
      note.textContent = open
        ? `Mark the ${open} answer(s) compared with the Key below, then save the result.`
        : pct >= PASS_MARK ? "Passed." : `Below ${PASS_MARK}% — practise and try again.`;
      done.disabled = open > 0;
      return { right, pct };
    };

    results.forEach((r) => {
      const li = el("li", "test-row");
      const head = el("p", "test-q", promptOf(r.item));
      head.dir = "auto";
      const yours = el("p", "test-yours", `Your answer: ${describeAnswer(r.item, r.answer)}`);
      yours.dir = "auto";
      const key = el("p", "test-key", `Expected: ${r.res.expected}`);
      key.dir = "auto";
      const mark = el("span", "test-mark");
      const paint = () => {
        li.className = `test-row ${r.correct === true ? "test-row--ok" : r.correct === false ? "test-row--no" : "test-row--open"}`;
        mark.textContent = r.correct === true ? "✓" : r.correct === false ? "✗" : "?";
      };
      li.append(mark, head, yours, key);
      if (r.correct === null) {
        const ask = el("span", "test-selfmark");
        const yes = el("button", "gate-btn test-mark-right", "I had it right");
        const no = el("button", "gate-btn gate-secondary test-mark-wrong", "I had it wrong");
        const set = (v) => {
          r.correct = v;
          ask.remove();
          paint();
          refresh();
        };
        yes.addEventListener("click", () => set(true));
        no.addEventListener("click", () => set(false));
        ask.append(yes, no);
        li.appendChild(ask);
      }
      paint();
      list.appendChild(li);
    });

    done.addEventListener("click", () => {
      const { right, pct } = refresh();
      const msg = ctx.onFinish({ correct: right, total: results.length, score: pct, passed: pct >= PASS_MARK, elapsed });
      done.disabled = true;
      done.textContent = "Saved";
      if (msg) note.textContent = msg;
    });
    const again = el("button", "gate-btn gate-secondary test-back", ctx.backLabel ? ctx.backLabel.replace("← ", "Back to ") : "Back to roadmap");
    again.addEventListener("click", () => ctx.onBack());
    const actions = el("span", "drill-actions");
    actions.append(done, again);
    feedback.append(actions);
    refresh();
    if (!done.disabled) done.focus();
  }

  if (!items.length) {
    stage.appendChild(el("p", "drill-result-note", "No questions for this test yet."));
    return;
  }
  renderQuestion();
}
