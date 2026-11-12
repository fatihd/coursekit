export function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

export function scriptSpan(course, text) {
  const span = document.createElement("span");
  span.className = "script";
  if (course.script && course.script.direction === "rtl") span.dir = "rtl";
  span.textContent = text;
  return span;
}

export function confirmAction(label, question, yesLabel, onYes, className = "") {
  const box = el("span", `confirm ${className}`.trim());
  const start = el("button", "gate-btn gate-secondary confirm-start", label);
  start.type = "button";
  const ask = el("span", "confirm-ask");
  ask.hidden = true;
  const yes = el("button", "gate-btn confirm-yes", yesLabel);
  const no = el("button", "gate-btn gate-secondary confirm-no", "Cancel");
  yes.type = "button";
  no.type = "button";
  ask.append(el("span", "confirm-question", question), yes, no);
  start.addEventListener("click", () => {
    start.hidden = true;
    ask.hidden = false;
    no.focus();
  });
  no.addEventListener("click", () => {
    ask.hidden = true;
    start.hidden = false;
    start.focus();
  });
  yes.addEventListener("click", () => onYes());
  box.append(start, ask);
  return box;
}
