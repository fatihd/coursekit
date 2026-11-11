import { el } from "../dom.js";
import { getType } from "../exercise-types/index.js";
import { withSeed } from "../exercise-types/util.js";

function unitTitle(course, n) {
  const u = course.units.find((x) => x.n === n);
  return u ? u.title : `Unit ${n}`;
}

function renderSource(source) {
  const box = el("div", "drill-source");
  if (source.note) box.appendChild(el("p", "drill-source-note", source.note));
  const links = el("p", "drill-source-links");
  const prompt = el("a", "drill-source-link", "Original exercise page");
  prompt.href = source.promptUrl;
  prompt.target = "_blank";
  prompt.rel = "noopener";
  links.appendChild(prompt);
  if (source.answerUrl) {
    links.appendChild(document.createTextNode(" · "));
    const answer = el("a", "drill-source-link", "Answer key page");
    answer.href = source.answerUrl;
    answer.target = "_blank";
    answer.rel = "noopener";
    links.appendChild(answer);
  }
  box.appendChild(links);
  return box;
}

function renderHint(text) {
  const box = el("div", "drill-tip");
  const toggle = el("button", "drill-tip-toggle", "Show hint");
  toggle.type = "button";
  toggle.addEventListener("click", () => {
    const body = el("p", "drill-tip-text", text);
    body.dir = "auto";
    box.replaceChildren(body);
  });
  box.appendChild(toggle);
  return box;
}

function focusFirst(container) {
  const input = container.querySelector(".ex-text, .hebrew-input");
  if (input) {
    input.focus();
    return;
  }
  const option = container.querySelector(".ex-option");
  if (option) {
    option.focus();
    return;
  }
  const select = container.querySelector(".ex-select");
  if (select) select.focus();
}

export function renderDrill(root, ctx) {
  const { course, items, navigate, unit, onComplete } = ctx;
  const features = ctx.features || {};
  root.replaceChildren();

  let idx = ctx.start || 0;
  let correctCount = ctx.initial ? ctx.initial.correct : 0;
  let answered = ctx.initial ? ctx.initial.answered : 0;
  const detail = ctx.initial ? [...ctx.initial.detail] : [];

  const wrap = el("div", "drill-wrap");
  root.appendChild(wrap);

  const back = el("button", "back", "← Lesson");
  back.addEventListener("click", () => navigate("lesson", unit.n));
  wrap.appendChild(back);

  const progress = el("p", "drill-progress", "");
  wrap.appendChild(progress);

  const stage = el("div", "drill-stage");
  wrap.appendChild(stage);

  const feedback = el("div", "drill-feedback");
  wrap.appendChild(feedback);

  let nextBtn = null;

  function showResults() {
    stage.replaceChildren();
    feedback.replaceChildren();
    progress.textContent = "";
    const total = answered || items.length;
    const score = Math.round((correctCount / total) * 100);
    stage.appendChild(el("h2", "drill-result", `${correctCount} / ${total} correct — ${score}%`));
    if (!ctx.single) {
      const pass = score >= 70;
      stage.appendChild(
        el("p", "drill-result-note", pass ? "Unit complete." : "Below 70% — you can retry."),
      );
    }
    const toRoadmap = el("button", "gate-btn", ctx.single ? "Back to lesson →" : "Back to roadmap →");
    toRoadmap.addEventListener("click", () => (ctx.single ? navigate("lesson", unit.n) : navigate("roadmap")));
    stage.appendChild(toRoadmap);
    toRoadmap.focus();
    onComplete(correctCount, answered, detail);
  }

  function next() {
    idx += 1;
    nextBtn = null;
    if (idx >= items.length) showResults();
    else renderQuestion();
  }

  function renderQuestion() {
    const rungLabel = items[idx].rungLabel ? ` · ${items[idx].rungLabel}` : "";
    progress.textContent = `Question ${idx + 1} of ${items.length}${rungLabel}`;
    if (ctx.onPosition) ctx.onPosition(idx);
    feedback.replaceChildren();
    stage.replaceChildren();
    nextBtn = null;

    const item = items[idx];
    const type = getType(item.type);

    if (item.spiral) {
      const from = item.sourceUnit ? ` · Unit ${item.sourceUnit} — ${unitTitle(course, item.sourceUnit)}` : "";
      stage.appendChild(el("span", "drill-review-tag", `Review${from}`));
    }

    const node = ctx.seed ? withSeed(`${ctx.seed}:${idx}`, () => type.render(item, { course })) : type.render(item, { course });
    stage.appendChild(node);

    if (item.hint) stage.appendChild(renderHint(item.hint));

    if (item.source && (item.source.promptUrl || item.source.answerUrl)) {
      stage.appendChild(renderSource(item.source));
    }
    if (item.id) stage.appendChild(el("p", "drill-item-code", `Item ${item.id}`));

    const checkBtn = el("button", "gate-btn", "Check");
    checkBtn.addEventListener("click", () => {
      const answer = type.collect ? type.collect(node, item) : null;
      if (answer === null || answer === undefined) {
        const hint = feedback.querySelector(".drill-hint");
        if (!hint) feedback.appendChild(el("p", "drill-hint", "Complete your answer first."));
        return;
      }

      const result = type.grade(item, answer);
      stage.querySelectorAll("button, input, select").forEach((n) => {
        n.disabled = true;
      });
      if (result.selfCheck) {
        feedback.replaceChildren();
        const ask = el("div", "drill-selfcheck");
        ask.appendChild(el("p", "drill-selfcheck-text", "No exact match. Compare your answer with the Key:"));
        const key = el("p", "drill-selfcheck-key", result.expected);
        key.dir = "auto";
        ask.appendChild(key);
        const yes = el("button", "gate-btn drill-selfcheck-yes", "I had it right");
        const no = el("button", "gate-btn gate-secondary drill-selfcheck-no", "I had it wrong");
        yes.addEventListener("click", () => finish({ ...result, correct: true, selfMarked: true }));
        no.addEventListener("click", () => finish({ ...result, correct: false, selfMarked: true }));
        ask.append(yes, no);
        feedback.appendChild(ask);
        no.focus();
        return;
      }
      finish(result);

      function finish(res) {
        if (type.annotate) type.annotate(node, item, answer, res);
        if (res.correct) correctCount += 1;
        answered += 1;
        detail.push({ unit: item.sourceUnit || unit.n, correct: res.correct });
        if (ctx.onAnswer) ctx.onAnswer(item, res.correct, { next: idx + 1, correct: correctCount, answered, detail });

        feedback.replaceChildren();
        const text = res.correct
          ? (res.selfMarked ? "Marked right." : "Correct!")
          : (res.selfMarked ? "Marked wrong." : `Not quite — answer: ${res.expected}`);
        const msg = el("p", res.correct ? "drill-ok" : "drill-no", res.message && !res.correct ? `${res.message} ${text}` : text);
        msg.dir = "auto";
        feedback.appendChild(msg);
        if (item.explain) {
          const explain = el("p", "drill-explain", item.explain);
          explain.dir = "auto";
          const source = stage.querySelector(".drill-source") || stage.querySelector(".drill-item-code");
          stage.insertBefore(explain, source);
        }
        if (!res.correct && features.diagnostics) {
          const srcUnit = item.sourceUnit || unit.n;
          const review = el("button", "back", `Review Unit ${srcUnit} — ${unitTitle(course, srcUnit)}`);
          review.addEventListener("click", () => navigate("drill", srcUnit));
          feedback.appendChild(review);
        }
        nextBtn = el("button", "gate-btn", idx + 1 < items.length ? "Next →" : "See results");
        nextBtn.addEventListener("click", next);
        feedback.appendChild(nextBtn);
        nextBtn.focus();
      }
    });
    feedback.appendChild(checkBtn);

    focusFirst(stage);
  }

  wrap.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.isComposing || event.shiftKey) return;
    // After an answer is checked, Enter advances to the next question (or results).
    // Only when a "Next"/"See results" button is showing, and focus isn't inside a
    // <select> (whose native Enter toggles the dropdown).
    if (nextBtn && !(event.target instanceof HTMLSelectElement)) {
      event.preventDefault();
      nextBtn.click();
    }
  });

  if (idx >= items.length) showResults();
  else renderQuestion();
}
