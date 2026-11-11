import { el, scriptSpan } from "../dom.js";
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
    const weak = weakUnits(ctx.progress, unit.n, 3);
    if (weak.length) {
      const warmup = el("div", "warmup");
      warmup.appendChild(el("p", "warmup-label", "Warm up — review earlier units before starting this one:"));
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

  const gate = el("div", "gate");
  const btn = el("button", "gate-btn", "Start drills →");
  btn.addEventListener("click", () => ctx.onStartDrills(unit.n));
  gate.appendChild(btn);
  root.appendChild(gate);
}
