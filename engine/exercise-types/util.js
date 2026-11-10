export function normalize(s) {
  return (s || "")
    .toString()
    .toLowerCase()
    .replace(/[.,;:!?'"()\-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// Strip Hebrew pointing (niqqud) but keep the sin/shin dots, which distinguish
// letters. Also normalises the maqqeph hyphen, final-form variants and stray
// spacing so a student's typed answer matches a pointed reference leniently.
const NIQQUD = /[\u0591-\u05c7]/g;

export function normalizeHebrew(s) {
  return (s || "")
    .toString()
    .replace(NIQQUD, (m) => (m === "\u05c1" || m === "\u05c2" ? m : ""))
    .replace(/[\u05be\u05f3\u05f4]/g, " ") // maqqeph, geresh
    .replace(/[\s.,;:!?'"()\-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
