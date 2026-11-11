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

let rand = Math.random;

function seeded(seed) {
  let h = 2166136261;
  for (const ch of String(seed)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return () => {
    h += 0x6d2b79f5;
    let t = h;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function random() {
  return rand();
}

export function withSeed(seed, fn) {
  const prev = rand;
  rand = seeded(seed);
  try {
    return fn();
  } finally {
    rand = prev;
  }
}

export function newSeed() {
  return Math.random().toString(36).slice(2, 8);
}

export function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
