import { el } from "./dom.js";
import heIL from "./keyboards/he_IL.js";

const layouts = { he_IL: heIL };

let overlay = null;
let activeInput = null;

function insertAtCursor(input, text) {
  const start = input.selectionStart ?? input.value.length;
  const end = input.selectionEnd ?? input.value.length;
  input.value = input.value.slice(0, start) + text + input.value.slice(end);
  const pos = start + text.length;
  input.setSelectionRange(pos, pos);
}

function applyKey(k) {
  const input = activeInput;
  if (!input) return;
  if (k.action === "backspace") {
    const start = input.selectionStart ?? input.value.length;
    if (start > 0) {
      input.value = input.value.slice(0, start - 1) + input.value.slice(input.selectionEnd ?? start);
      input.setSelectionRange(start - 1, start - 1);
    }
  } else if (k.action === "space") {
    insertAtCursor(input, " ");
  } else if (k.action === "done") {
    input.blur();
    return;
  } else {
    insertAtCursor(input, k.key);
  }
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.focus();
}

function buildKey(k) {
  let btn;
  if (k.niqqud) {
    btn = el("button", "kb-key kb-key--niqqud");
    const base = k.base === undefined ? "ב" : k.base;
    btn.appendChild(el("span", "kb-glyph", base + k.key));
    if (k.name) {
      btn.appendChild(el("span", "kb-name", k.name));
      btn.title = k.name;
      btn.setAttribute("aria-label", k.name);
    }
  } else {
    btn = el("button", "kb-key", k.label || k.key);
  }
  btn.dataset.key = k.key;
  btn.type = "button";
  btn.addEventListener("mousedown", (e) => {
    e.preventDefault();
    applyKey(k);
  });
  return btn;
}

export function initKeyboard(root, layoutId) {
  const layout = layouts[layoutId] || heIL;
  overlay = el("div", "keyboard");
  overlay.style.display = "none";

  for (const row of layout.rows) {
    const r = el("div", "kb-row");
    for (const k of row) r.appendChild(buildKey(k));
    overlay.appendChild(r);
  }

  const nrow = el("div", "kb-row kb-row--niqqud");
  for (const k of layout.niqqud) {
    nrow.appendChild(buildKey({ ...k, niqqud: true }));
  }
  overlay.appendChild(nrow);

  root.appendChild(overlay);

  document.addEventListener("focusin", (e) => {
    if (e.target.classList && e.target.classList.contains("hebrew-input")) {
      activeInput = e.target;
      overlay.style.display = "";
      document.body.style.paddingBottom = `${overlay.offsetHeight + 16}px`;
      const area = e.target.closest(".drill-wrap") || e.target;
      const feedback = area.querySelector ? area.querySelector(".drill-feedback") : null;
      (feedback || e.target).scrollIntoView({ block: "nearest" });
    }
  });
  document.addEventListener("focusout", (e) => {
    if (e.target.classList && e.target.classList.contains("hebrew-input")) {
      activeInput = null;
      overlay.style.display = "none";
    }
  });
  window.addEventListener("hashchange", () => {
    document.body.style.paddingBottom = "";
  });
}
