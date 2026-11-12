import { confirmAction, el, scriptSpan } from "../dom.js";
import { weakUnits } from "../knowledge.js";

function renderVocabCard(course, item, showTranslit = true) {
  const card = el("div", "vocab-card");

  const word = el("div", "vocab-word");
  word.appendChild(scriptSpan(course, item.scriptForm));
  if (item.plural) {
    word.appendChild(el("span", "vocab-plural-sep", " · "));
    word.appendChild(scriptSpan(course, item.plural));
  }
  card.appendChild(word);

  card.appendChild(el("div", "vocab-gloss", item.gloss));

  const meta = el("div", "vocab-meta");
  if (item.gender || item.number) {
    const g = item.gender === "m" ? "masc." : item.gender === "f" ? "fem." : item.gender === "c" ? "common" : "";
    const n = item.number === "s" ? "sing." : item.number === "p" ? "plur." : item.number === "d" ? "dual" : "";
    meta.appendChild(el("span", "vocab-gender", [g, n].filter(Boolean).join(" ")));
  }
  if (showTranslit && item.transliteration) meta.appendChild(el("span", "vocab-translit", item.transliteration));
  if (showTranslit && item.pronunciation && item.pronunciation !== item.transliteration) {
    meta.appendChild(el("span", "vocab-pron", item.pronunciation));
  }
  if (item.category) meta.appendChild(el("span", "vocab-cat", item.category));
  card.appendChild(meta);

  return card;
}

function renderTable(block) {
  const wrap = el("div", "block-table");
  if (block.caption) wrap.appendChild(el("p", "table-caption", block.caption));

  const table = document.createElement("table");
  if (block.columns && block.columns.length) {
    const thead = document.createElement("thead");
    const tr = document.createElement("tr");
    for (const c of block.columns) tr.appendChild(el("th", null, c));
    thead.appendChild(tr);
    table.appendChild(thead);
  }

  const tbody = document.createElement("tbody");
  for (const row of block.rows || []) {
    const tr = document.createElement("tr");
    for (const cell of row) {
      const td = el("td", null, cell);
      td.dir = "auto";
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}

export function renderLesson(root, ctx, unit, lesson) {
  root.replaceChildren();

  const back = el("button", "back", "← Roadmap");
  back.addEventListener("click", () => ctx.navigate("roadmap"));
  root.appendChild(back);

  root.appendChild(el("h1", "lesson-title", `Unit ${unit.n} — ${lesson.title}`));
  root.appendChild(el("p", "lesson-desc", lesson.description));

  if (ctx.recap) {
    const recap = el("div", "recap");
    recap.appendChild(el("span", "recap-label", "Previously… "));
    recap.appendChild(el("span", "recap-text", ctx.recap.text));
    root.appendChild(recap);
  }

  if (ctx.features && ctx.features.reviewWarmup && ctx.progress) {
    const weak = ctx.warmup || weakUnits(ctx.progress, unit.n, 3);
    if (weak.length) {
      const warmup = el("div", "warmup");
      warmup.appendChild(el("p", "warmup-label", "Warm up — earlier units you have not practised yet or got least right:"));
      for (const n of weak) {
        const btn = el("button", "warmup-unit", `Review Unit ${n}`);
        btn.addEventListener("click", () => ctx.navigate("drill", n));
        warmup.appendChild(btn);
      }
      root.appendChild(warmup);
    }
  }

  for (const block of lesson.blocks) {
    if (block.type === "prose") {
      const p = el("div", "block-prose");
      if (block.caption) p.appendChild(el("h2", "block-prose-heading", block.caption));
      const content = el("div", "block-prose-content");
      content.innerHTML = block.html;
      p.appendChild(content);
      root.appendChild(p);
    } else if (block.type === "vocab") {
      const grid = el("div", "vocab-grid");
      for (const ref of block.refs) {
        const item = ctx.vocab[ref];
        if (item) grid.appendChild(renderVocabCard(ctx.course, item, !ctx.features || ctx.features.transliteration !== false));
      }
      root.appendChild(grid);
    } else if (block.type === "table" || block.type === "paradigm") {
      root.appendChild(renderTable(block));
    } else if (block.type === "callout") {
      const box = el("div", `callout callout--${block.variant || "note"}`);
      box.innerHTML = block.html;
      root.appendChild(box);
    }
  }

  if (ctx.ladder && ctx.ladder.length) {
    const box = el("section", "ladder");
    box.appendChild(el("h2", "blocks-title", "Exercise ladder"));
    if (ctx.unlockRung) {
      box.appendChild(el("p", "ladder-note", `Get every exercise right once on rungs 1–${ctx.unlockRung} to unlock the next unit; the higher rungs earn its stars.`));
    }
    const list = el("ol", "ladder-list");
    for (const r of ctx.ladder) {
      const row = el("li", r.done >= r.total ? "ladder-row ladder-row--done" : "ladder-row");
      row.dataset.rung = r.rung;
      row.appendChild(el("span", "blocks-label", `${r.rung}. ${r.label}`));
      const bar = el("span", "ladder-bar");
      const fill = el("span", "ladder-fill");
      fill.style.width = `${Math.round((100 * r.done) / Math.max(1, r.total))}%`;
      bar.appendChild(fill);
      row.appendChild(bar);
      row.appendChild(el("span", "blocks-count", `${r.done} / ${r.total}`));
      const practice = el("a", "blocks-practice", "Practice");
      practice.href = r.href;
      row.appendChild(practice);
      list.appendChild(row);
    }
    box.appendChild(list);
    root.appendChild(box);
  }

  if (ctx.blocks && ctx.blocks.length) {
    const box = el("section", "blocks");
    box.appendChild(el("h2", "blocks-title", "Exercises by Davidson section"));
    const list = el("ul", "blocks-list");
    for (const b of ctx.blocks) {
      const row = el("li", "blocks-row");
      row.dataset.block = b.id;
      row.appendChild(el("span", "blocks-label", b.label));
      row.appendChild(el("span", "blocks-count", `${b.done} / ${b.total} right`));
      const practice = el("a", "blocks-practice", "Practice");
      practice.href = b.href;
      row.appendChild(practice);
      list.appendChild(row);
    }
    box.appendChild(list);
    root.appendChild(box);
  }

  const gate = el("div", "gate");
  if (ctx.resume) {
    const resume = el("button", "gate-btn gate-resume", `Resume drills (question ${ctx.resume.pos} of ${ctx.resume.total}) →`);
    resume.addEventListener("click", () => {
      location.hash = ctx.resume.href;
    });
    gate.appendChild(resume);
  }
  const btn = el("button", ctx.resume ? "gate-btn gate-secondary" : "gate-btn", ctx.resume ? "Start new drills" : "Start drills →");
  btn.addEventListener("click", () => ctx.onStartDrills(unit.n));
  gate.appendChild(btn);
  root.appendChild(gate);

  if (ctx.onMarkUnitDone || ctx.onResetUnit) {
    const ops = el("div", "unit-ops");
    if (ctx.unitDone) {
      ops.appendChild(el("span", "unit-ops-done", "Unit complete ✓"));
    } else if (ctx.onMarkUnitDone) {
      const mark = el("button", "gate-btn gate-secondary unit-mark-done", "Mark unit as done");
      mark.type = "button";
      mark.title = "Unlock the next unit without finishing these exercises (no stars are given)";
      mark.addEventListener("click", () => ctx.onMarkUnitDone(unit.n));
      ops.appendChild(mark);
    }
    if (ctx.onResetUnit && (ctx.unitStarted || ctx.unitDone)) {
      ops.appendChild(confirmAction("Reset this unit…", "Clear this unit's answers, ladder progress and saved session?",
        "Reset unit", () => ctx.onResetUnit(unit.n), "unit-reset"));
    }
    root.appendChild(ops);
  }
}
