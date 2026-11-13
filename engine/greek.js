const MARK_RANK = {
  "̈": 0,
  "̓": 1,
  "̔": 1,
  "́": 2,
  "̀": 2,
  "͂": 2,
  "ͅ": 3,
};
const COMBINING = /\p{M}/u;
const GREEK_LETTER = /[Ͱ-Ͽἀ-῿]/u;
const ACCENTS = /[̀́͂]/g;
const ALL_MARKS = /\p{M}/gu;
const ELISION = /[᾽᾿’ʼ']/g;
const PUNCT = /[.,;:!?"()\[\]··;—–‘“”-]/g;

function clusters(s) {
  const out = [];
  for (const ch of s.normalize("NFD")) {
    if (COMBINING.test(ch) && out.length) out[out.length - 1].marks.push(ch);
    else out.push({ base: ch, marks: [] });
  }
  for (const c of out) {
    const seen = new Set();
    c.marks = c.marks.filter((m) => (seen.has(m) ? false : seen.add(m)))
      .sort((a, b) => (MARK_RANK[a] ?? 9) - (MARK_RANK[b] ?? 9));
  }
  return out;
}

function finalSigma(s) {
  return s
    .replace(/ς(?=[\p{L}\p{M}])/gu, "σ")
    .replace(/σ(?![\p{L}\p{M}])/gu, "ς");
}

export function composeGreek(s) {
  const text = clusters((s || "").toString()).map((c) => c.base + c.marks.join("")).join("");
  return finalSigma(text.normalize("NFC"));
}

const ELIDED = {
  "δι’": "διά", "ἀπ’": "ἀπό", "ἀφ’": "ἀπό", "ἀλλ’": "ἀλλά", "κατ’": "κατά", "καθ’": "κατά",
  "μετ’": "μετά", "μεθ’": "μετά", "παρ’": "παρά", "ἐπ’": "ἐπί", "ἐφ’": "ἐπί", "ὑπ’": "ὑπό",
  "ὑφ’": "ὑπό", "ἀντ’": "ἀντί", "ἀνθ’": "ἀντί", "δ’": "δέ", "οὐδ’": "οὐδέ", "μηδ’": "μηδέ",
  "ἵν’": "ἵνα", "τοῦτ’": "τοῦτο",
};
const ENCLITIC = new Set(("μου μοι με σου σοι σε τις τι τινος τινι τινα τινες τινων τισι τισιν τινας "
  + "εστι εστιν εισι εισιν εσμεν εστε ειμι φημι φησι φησιν φαμεν φασι φασιν γε τε τοι περ που ποτε πω πως ποθεν")
  .replace(/ς/g, "σ").split(" "));
const PROCLITIC = new Set("ει εν εις εκ εξ ως ου ουκ ουχ".replace(/ς/g, "σ").split(" "));
const NU_KEEP = new Set(["ουδεν", "μηδεν"]);

function bare(w) {
  return w.normalize("NFD").replace(ALL_MARKS, "").replace(/ς/g, "σ");
}

function spacingBreathings(s) {
  return s.replace(/[\u1fbf\u1fbd](?=\p{L})(\p{L})/gu, "$1\u0313").replace(/\u1ffe(\p{L})/gu, "$1\u0314");
}

function cliticTolerant(words) {
  const isEnclitic = (w) => w !== undefined && ENCLITIC.has(bare(w));
  return words.map((w, i) => {
    const b = bare(w);
    if (ENCLITIC.has(b) || PROCLITIC.has(b)) return w.replace(ACCENTS, "");
    if (isEnclitic(words[i + 1]) && (w.match(/[\u0301\u0342]/g) || []).length > 1) {
      const at = w.lastIndexOf("\u0301");
      return w.slice(0, at) + w.slice(at + 1);
    }
    return w;
  });
}

function dropMovableNu(w) {
  const b = bare(w);
  if (b.length <= 3 || NU_KEEP.has(b)) return w;
  if (b === "εστιν" || /(σι|ε)ν$/u.test(b)) return w.replace(/ν$/u, "");
  return w;
}

export function greekKey(s, level = "full", options = {}) {
  const opts = { movableNu: true, elision: true, clitics: true, ...options };
  let t = composeGreek(spacingBreathings((s || "").toString())).toLowerCase();
  t = t.replace(ELISION, "’").replace(PUNCT, " ");
  let words = t.split(/\s+/).filter(Boolean);
  if (opts.elision) words = words.map((w) => ELIDED[w] || w);
  words = words.map((w) => w.normalize("NFD"));
  if (level === "full") words = words.map((w) => w.replace(/\u0300/g, "\u0301"));
  else if (level === "breathings") words = words.map((w) => w.replace(ACCENTS, "").replace(/\u0308/g, ""));
  else words = words.map((w) => w.replace(ALL_MARKS, ""));
  words = words.map((w) => w.replace(/ς/g, "σ"));
  if (level === "full" && opts.clitics) words = cliticTolerant(words);
  if (opts.movableNu) words = words.map(dropMovableNu);
  return words.join(" ").normalize("NFC");
}

const POSTPOSITIVE = new Set(("δε γαρ ουν μεν τε γε αν δη τοι μεντοι τοινυν μου μοι με σου σοι σε")
  .split(" "));
const ARTICLE = new Set("ο η το οι αι τα του της τω τη τον την των τοις ταις τους τας".replace(/ς/g, "σ").split(" "));
const CLAUSE_END = /[.;:··;!?]+/;

export function wordOrderOk(s) {
  const text = composeGreek(spacingBreathings((s || "").toString())).replace(ELISION, "’");
  for (const clause of text.split(CLAUSE_END)) {
    const words = clause.replace(PUNCT, " ").split(/\s+/).filter((w) => GREEK_LETTER.test(w)).map(bare);
    if (!words.length) continue;
    if (POSTPOSITIVE.has(words[0])) return false;
    if (ARTICLE.has(words[words.length - 1])) return false;
  }
  return true;
}

export function sameWordsAnyOrder(a, b, level = "full", options = {}) {
  const sort = (s) => greekKey(s, level, options).split(" ").sort().join(" ");
  return sort(a) === sort(b) && wordOrderOk(a);
}

export function sameGreek(a, b, level = "full", options = {}) {
  return greekKey(a, level, options) === greekKey(b, level, options);
}

export function hasAccents(s) {
  return /[̀́͂]/.test((s || "").normalize("NFD"));
}

export function hasBreathings(s) {
  return /[̓̔]/.test((s || "").normalize("NFD"));
}

function greekWords(s) {
  return composeGreek(s).replace(ELISION, "’").replace(PUNCT, " ").split(/\s+/)
    .filter((w) => GREEK_LETTER.test(w));
}

function letterClusters(word) {
  return clusters(word).filter((c) => !COMBINING.test(c.base));
}

function plain(c) {
  return c.base.toLowerCase().replace("ς", "σ");
}

function marksKey(c) {
  return c.marks.map((m) => (m === "̀" ? "́" : m)).join("");
}

export function accentDiff(answer, expected) {
  const a = greekWords(answer);
  const e = greekWords(expected);
  return a.map((word, i) => {
    const mine = letterClusters(word);
    const theirs = e[i] !== undefined ? letterClusters(e[i]) : [];
    const sameLetters = mine.length === theirs.length && mine.every((c, j) => plain(c) === plain(theirs[j]));
    const wordOk = e[i] !== undefined && greekKey(word) === greekKey(e[i]);
    return {
      word,
      ok: wordOk,
      clusters: mine.map((c, j) => ({
        text: (c.base + c.marks.join("")).normalize("NFC"),
        ok: wordOk || (sameLetters && marksKey(c) === marksKey(theirs[j])),
      })),
    };
  });
}
