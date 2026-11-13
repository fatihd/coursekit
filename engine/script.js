import { hasPoints, normalizeHebrew, pointedForm, pointingDiff } from "./exercise-types/util.js";
import { accentDiff, greekKey, hasAccents } from "./greek.js";

const HEBREW = {
  id: "hebrew",
  name: "Hebrew",
  dir: "rtl",
  lang: "he",
  marks: "vowel points",
  plain: normalizeHebrew,
  full: pointedForm,
  hasMarks: hasPoints,
  diff: pointingDiff,
  strip: (w) => w.replace(/[֑-ׇ]/g, ""),
  fullPrompt: "Type the Hebrew word with full vowel points",
  plainPrompt: "Type the Hebrew word (vowel points not checked)",
  missing: "Vowel points are required here.",
  marked: "Letters marked red have wrong or missing vowel points.",
  yours: "Your pointing: ",
};

function greekProfile(grading = {}) {
  const plainLevel = grading.plain || "breathings";
  const fullLevel = grading.full || "full";
  const opts = { movableNu: grading.movableNu !== false, elision: grading.elision !== false, clitics: grading.clitics !== false };
  return {
    id: "greek",
    name: "Greek",
    dir: "ltr",
    lang: "grc",
    marks: "accents",
    plain: (s) => greekKey(s, plainLevel, opts),
    full: (s) => greekKey(s, fullLevel, opts),
    hasMarks: hasAccents,
    diff: accentDiff,
    strip: (w) => w.normalize("NFD").replace(/\p{M}/gu, "").normalize("NFC"),
    fullPrompt: "Type the Greek word with full accents",
    plainPrompt: "Type the Greek word with breathings (accents not checked)",
    missing: "Accents are required here.",
    marked: "Letters marked red have wrong or missing accents, breathings or iota subscripts.",
    yours: "Your accents: ",
  };
}

let active = HEBREW;

export function profileFor(course) {
  const s = (course && course.script) || {};
  if (s.profile === "greek") return greekProfile(s.grading || {});
  return HEBREW;
}

export function setScript(course) {
  active = profileFor(course);
  return active;
}

export function script() {
  return active;
}

export function usesKeyboard(course) {
  const s = (course && course.script) || {};
  return s.direction === "rtl" || profileFor(course).id !== "hebrew";
}
