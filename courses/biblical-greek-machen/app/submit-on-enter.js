document.addEventListener("keydown", (event) => {
  const target = event.target;
  if (event.key !== "Enter" || event.isComposing || event.shiftKey) return;
  if (!(target instanceof HTMLInputElement)) return;
  if (!target.matches(".ex--translate .ex-text, .ex--dictation .hebrew-input")) return;
  const check = document.querySelector(".drill-feedback .gate-btn");
  if (!check || check.textContent.trim() !== "Check") return;
  event.preventDefault();
  check.click();
});
