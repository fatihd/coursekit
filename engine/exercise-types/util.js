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

const CONTRACTIONS = [
  [/\bwon't\b/g, "will not"], [/\bcan't\b/g, "can not"], [/\bcannot\b/g, "can not"],
  [/n't\b/g, " not"], [/\bi'm\b/g, "i am"], [/'re\b/g, " are"], [/'ve\b/g, " have"],
  [/'ll\b/g, " will"], [/'d\b/g, " would"],
];

export function normalizeEnglish(s) {
  let t = (s || "").toString().toLowerCase().replace(/[‘’]/g, "'");
  for (const [re, r] of CONTRACTIONS) t = t.replace(re, r);
  t = t.replace(/'s\b/g, "s").replace(/[^a-z0-9\s]/g, " ");
  t = t.replace(/\bshall\b/g, "will").replace(/\bunto\b/g, "to").replace(/\btowards\b/g, "toward")
    .replace(/\bupon\b/g, "on").replace(/\bo\b/g, " ");
  return t.replace(/\s+/g, " ").trim();
}

const CANTILLATION = /[֑-ֽֿ֯׀׃-׆]/g;
const LETTER = /[א-ת]/;
const VOWELS = /[ְ-ֻ]/;
const BEGADKEFAT = "בגדכפת";

export function hebrewClusters(word) {
  const out = [];
  for (const ch of word.normalize("NFD")) {
    if (LETTER.test(ch)) out.push({ base: ch, marks: [] });
    else if (out.length && /[ְ-ׂ]/.test(ch)) out[out.length - 1].marks.push(ch);
  }
  for (const c of out) c.marks = [...new Set(c.marks)].sort();
  return out;
}

function canonicalWord(word) {
  const cl = hebrewClusters(word);
  if (cl.length && BEGADKEFAT.includes(cl[0].base)) cl[0].marks = cl[0].marks.filter((m) => m !== "ּ");
  const out = [];
  for (let i = 0; i < cl.length; i++) {
    const c = cl[i];
    const prev = out[out.length - 1];
    const last = i === cl.length - 1;
    const prevBare = prev && !prev.marks.some((m) => VOWELS.test(m));
    if (!last && prev && prevBare && c.base === "ו" && c.marks.join("") === "ֹ") {
      prev.marks = [...prev.marks, "ֹ"].sort();
      continue;
    }
    if (!last && prev && prevBare && c.base === "ו" && c.marks.join("") === "ּ") {
      prev.marks = [...prev.marks, "ֻ"].sort();
      continue;
    }
    if (!last && prev && c.base === "י" && !c.marks.length
        && prev.marks.some((m) => m === "ִ" || m === "ֵ" || m === "ֶ")) {
      continue;
    }
    out.push({ base: c.base, marks: c.marks });
  }
  return out;
}

function hebrewWordsOf(s) {
  return (s || "").toString().normalize("NFD")
    .replace(CANTILLATION, "")
    .replace(/ׇ/g, "ָ")
    .replace(/ֺ/g, "ֹ")
    .replace(/־/g, " ")
    .replace(/[^ְ-ּׁׂא-ת\s]/g, " ")
    .split(/\s+/)
    .filter((w) => LETTER.test(w));
}

const FINALS = { "ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ" };

function clusterKey(c) {
  return (FINALS[c.base] || c.base) + c.marks.join("");
}

export function pointedForm(s) {
  return hebrewWordsOf(s).map((w) => canonicalWord(w).map(clusterKey).join("")).join(" ");
}

export function hasPoints(s) {
  return /[ְ-ֻ]/.test((s || "").normalize("NFD"));
}

export function pointingDiff(answer, expected) {
  const a = hebrewWordsOf(answer);
  const e = hebrewWordsOf(expected);
  return a.map((word, i) => {
    const mine = hebrewClusters(word);
    const theirs = e[i] ? hebrewClusters(e[i]) : [];
    const sameLetters = mine.length === theirs.length
      && mine.every((c, j) => (FINALS[c.base] || c.base) === (FINALS[theirs[j].base] || theirs[j].base));
    const wordOk = e[i] !== undefined && canonicalWord(word).map(clusterKey).join("")
      === canonicalWord(e[i]).map(clusterKey).join("");
    return {
      word,
      ok: wordOk,
      clusters: mine.map((c, j) => ({
        text: c.base + c.marks.join(""),
        ok: wordOk || (sameLetters && c.marks.join("") === theirs[j].marks.join("")),
      })),
    };
  });
}
