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
