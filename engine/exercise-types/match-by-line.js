import { el, scriptSpan } from "../dom.js";
import { random, shuffle } from "./util.js";

const LEFT_KEYS = "123456789";
const RIGHT_KEYS = "abcdefghi";

function norm(s) {
  return (s || "").toString().trim().toLowerCase();
}

function card(w) {
  return { script: w.scriptForm, gloss: w.gloss, plural: w.plural || "", gender: w.gender || "", number: w.number || "", id: w.id };
}

function pickWords(pool, count, prefer, key) {
  const seenScript = new Set();
  const seenValue = new Set();
  const out = [];
  const ordered = [...shuffle(pool.filter((x) => prefer.has(x.id))), ...shuffle(pool.filter((x) => !prefer.has(x.id)))];
  for (const x of ordered) {
    const value = key(x);
    if (!x.scriptForm || !value || seenScript.has(x.scriptForm) || seenValue.has(norm(value))) continue;
    seenScript.add(x.scriptForm);
    seenValue.add(norm(value));
    out.push(x);
    if (out.length >= count) break;
  }
  return out;
}

export default {
  id: "match-by-line",

  generate(params, pool) {
    const kind = params.kind || "gloss";
    const key = kind === "plural" ? (x) => x.plural : (x) => x.gloss;
    const prefer = params.prefer || new Set();
    const usable = pool.filter((x) => key(x));
    const picked = pickWords(usable, Math.min(params.count || 5, usable.length), prefer, key);
    if (picked.length < 2) return [];
    const taken = new Set(picked.map((x) => norm(key(x))));
    const extraPool = [...(params.distractors || []), ...usable].filter((x) => key(x) && !taken.has(norm(key(x))));
    const sameCategory = (x) => picked.some((p) => p.category && p.category === x.category);
    const extras = [];
    for (const x of [...shuffle(extraPool.filter(sameCategory)), ...shuffle(extraPool.filter((x) => !sameCategory(x)))]) {
      if (extras.length >= (params.extra ?? 2)) break;
      if (taken.has(norm(key(x)))) continue;
      taken.add(norm(key(x)));
      extras.push(key(x));
    }
    const reverse = kind === "gloss" && (params.direction === "en-he" || (params.direction === "random" && random() < 0.5));
    const answer = {};
    let left;
    let right;
    if (reverse) {
      left = picked.map((x) => x.gloss);
      picked.forEach((x) => { answer[x.gloss] = x.scriptForm; });
      const extraScript = extraPool.filter((x) => extras.includes(x.gloss)).map((x) => x.scriptForm);
      right = shuffle([...picked.map((x) => x.scriptForm), ...[...new Set(extraScript)].slice(0, extras.length)]);
    } else {
      left = picked.map((x) => x.scriptForm);
      picked.forEach((x) => { answer[x.scriptForm] = key(x); });
      right = shuffle([...picked.map(key), ...extras]);
    }
    return [{
      type: "match-by-line",
      prompt: kind === "plural" ? "Match each word to its plural" : reverse ? "Match each translation to its Hebrew word" : "Match each Hebrew word to its translation",
      left,
      right,
      answer,
      leftIsScript: !reverse,
      rightIsScript: reverse || kind === "plural",
      words: Object.fromEntries(picked.map((x) => [reverse ? x.gloss : x.scriptForm, x.id])),
      cards: picked.map(card),
    }];
  },

  render(item, ctx = {}) {
    const exam = Boolean(ctx.exam);
    const root = el("div", "ex ex--match");
    root.appendChild(el("p", "ex-prompt", item.prompt));
    const board = el("div", "ex-match-board");
    const leftCol = el("div", "ex-match-col ex-match-col--left");
    const rightCol = el("div", "ex-match-col ex-match-col--right");
    board.append(leftCol, rightCol);
    root.appendChild(board);
    const status = el("p", "ex-match-status");
    status.setAttribute("aria-live", "polite");
    root.appendChild(status);

    const state = { pairs: {}, misses: 0, missed: new Set(), selected: null };
    root._match = state;

    const tile = (side, value, index, isScript) => {
      const b = el("button", "ex-tile");
      b.type = "button";
      b.dataset.side = side;
      b.dataset.value = value;
      const keyLabel = side === "left" ? LEFT_KEYS[index] : RIGHT_KEYS[index];
      if (keyLabel) b.appendChild(el("span", "ex-tile-key", keyLabel));
      b.appendChild(isScript && ctx.course ? scriptSpan(ctx.course, value) : el("span", "ex-tile-text", value));
      b.setAttribute("aria-pressed", "false");
      return b;
    };
    const leftTiles = item.left.map((v, i) => tile("left", v, i, item.leftIsScript));
    const rightTiles = item.right.map((v, i) => tile("right", v, i, item.rightIsScript));
    leftCol.append(...leftTiles);
    rightCol.append(...rightTiles);

    const total = item.left.length;
    const update = () => {
      const made = Object.keys(state.pairs).length;
      status.textContent = exam
        ? `Pairs: ${made} of ${total}`
        : `Pairs: ${made} of ${total}${state.misses ? ` · misses: ${state.misses}` : ""}`;
    };
    const select = (b) => {
      if (state.selected) {
        state.selected.classList.remove("ex-tile--selected");
        state.selected.setAttribute("aria-pressed", "false");
      }
      state.selected = b;
      if (b) {
        b.classList.add("ex-tile--selected");
        b.setAttribute("aria-pressed", "true");
      }
    };
    const pairOf = (side, value) => (side === "left" ? state.pairs[value] : Object.keys(state.pairs).find((l) => state.pairs[l] === value));
    const tileFor = (side, value) => (side === "left" ? leftTiles : rightTiles).find((t) => t.dataset.value === value);
    const unpair = (l) => {
      const r = state.pairs[l];
      delete state.pairs[l];
      for (const t of [tileFor("left", l), tileFor("right", r)]) {
        if (!t) continue;
        t.classList.remove("ex-tile--paired");
        delete t.dataset.pair;
      }
    };
    const renumber = () => {
      Object.keys(state.pairs).forEach((l, i) => {
        tileFor("left", l).dataset.pair = String(i + 1);
        tileFor("right", state.pairs[l]).dataset.pair = String(i + 1);
      });
    };

    const tryPair = (a, b) => {
      const l = a.dataset.side === "left" ? a : b;
      const r = a.dataset.side === "left" ? b : a;
      if (exam) {
        state.pairs[l.dataset.value] = r.dataset.value;
        l.classList.add("ex-tile--paired");
        r.classList.add("ex-tile--paired");
        renumber();
        if (Object.keys(state.pairs).length === total) root.dispatchEvent(new CustomEvent("ex-complete", { bubbles: true }));
      } else if (item.answer[l.dataset.value] === r.dataset.value) {
        state.pairs[l.dataset.value] = r.dataset.value;
        for (const t of [l, r]) {
          t.classList.add("ex-tile--matched");
          t.disabled = true;
        }
        if (Object.keys(state.pairs).length === total) root.dispatchEvent(new CustomEvent("ex-complete", { bubbles: true }));
      } else {
        state.misses += 1;
        state.missed.add(l.dataset.value);
        for (const t of [l, r]) {
          t.classList.remove("ex-tile--wrong");
          void t.offsetWidth;
          t.classList.add("ex-tile--wrong");
        }
      }
      update();
    };

    const press = (b) => {
      if (b.disabled) return;
      if (exam && b.classList.contains("ex-tile--paired")) {
        const l = b.dataset.side === "left" ? b.dataset.value : pairOf("right", b.dataset.value);
        unpair(l);
        renumber();
        select(null);
        update();
        return;
      }
      const cur = state.selected;
      if (!cur || cur === b) {
        select(cur === b ? null : b);
        return;
      }
      if (cur.dataset.side === b.dataset.side) {
        select(b);
        return;
      }
      select(null);
      tryPair(cur, b);
    };

    for (const b of [...leftTiles, ...rightTiles]) {
      b.addEventListener("click", () => press(b));
      b.addEventListener("animationend", () => b.classList.remove("ex-tile--wrong"));
    }
    root.addEventListener("keydown", (event) => {
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      const k = event.key.toLowerCase();
      const li = LEFT_KEYS.indexOf(k);
      const ri = RIGHT_KEYS.indexOf(k);
      const b = li >= 0 ? leftTiles[li] : ri >= 0 ? rightTiles[ri] : null;
      if (!b) return;
      event.preventDefault();
      b.focus();
      press(b);
    });
    update();
    return root;
  },

  collect(node, item) {
    const state = node._match;
    if (!state) return null;
    if (Object.keys(state.pairs).length < item.left.length) return null;
    return {
      pairs: { ...state.pairs },
      misses: state.misses,
      firstTry: item.left.filter((l) => !state.missed.has(l)),
    };
  },

  grade(item, answer) {
    const pairs = answer && answer.pairs ? answer.pairs : answer || {};
    const allRight = item.left.every((l) => pairs[l] === item.answer[l]);
    const misses = answer && typeof answer.misses === "number" ? answer.misses : 0;
    const firstTry = answer && answer.firstTry ? answer.firstTry : item.left.filter((l) => pairs[l] === item.answer[l]);
    return {
      correct: allRight && misses <= 1,
      expected: item.left.map((l) => `${l} = ${item.answer[l]}`).join(" · "),
      message: allRight && misses > 1 ? `${misses} misses.` : undefined,
      words: item.words ? firstTry.map((l) => item.words[l]).filter(Boolean) : [],
    };
  },

  annotate(node, item, answer) {
    const pairs = answer && answer.pairs ? answer.pairs : answer || {};
    for (const t of node.querySelectorAll(".ex-tile")) {
      t.disabled = true;
      if (t.dataset.side !== "left") continue;
      const ok = pairs[t.dataset.value] === item.answer[t.dataset.value];
      t.classList.add(ok ? "ex-tile--ok" : "ex-tile--no");
    }
    if (!item.cards || !item.cards.length || node.querySelector(".ex-match-cards")) return;
    const list = el("div", "ex-match-cards");
    for (const c of item.cards) {
      const row = el("div", "ex-match-card");
      const word = el("span", "ex-match-card-word");
      word.appendChild(el("span", "script", c.script));
      word.firstChild.dir = "rtl";
      if (c.plural) {
        word.appendChild(el("span", "ex-match-card-sep", " · "));
        const pl = el("span", "script", c.plural);
        pl.dir = "rtl";
        word.appendChild(pl);
      }
      row.appendChild(word);
      row.appendChild(el("span", "ex-match-card-gloss", c.gloss));
      const g = c.gender === "m" ? "masc." : c.gender === "f" ? "fem." : c.gender === "c" ? "common" : "";
      if (g) row.appendChild(el("span", "ex-match-card-meta", g));
      list.appendChild(row);
    }
    node.appendChild(list);
  },
};
