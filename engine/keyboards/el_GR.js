import { composeGreek } from "../greek.js";

export default {
  id: "el_GR",
  compose: composeGreek,
  rows: [
    [
      { key: "α" }, { key: "β" }, { key: "γ" }, { key: "δ" }, { key: "ε" }, { key: "ζ" },
      { key: "η" }, { key: "θ" }, { key: "ι" }, { key: "κ" },
    ],
    [
      { key: "λ" }, { key: "μ" }, { key: "ν" }, { key: "ξ" }, { key: "ο" }, { key: "π" },
      { key: "ρ" }, { key: "σ" }, { key: "τ" }, { key: "υ" },
    ],
    [
      { key: "φ" }, { key: "χ" }, { key: "ψ" }, { key: "ω" }, { key: "ς" }, { key: "’", label: "’" },
      { key: "⌫", action: "backspace", label: "⌫" },
    ],
    [
      { key: " ", action: "space", label: "space" },
      { key: "done", action: "done", label: "done" },
    ],
  ],
  marks: [
    { key: "̓", name: "smooth", base: "α" },
    { key: "̔", name: "rough", base: "α" },
    { key: "́", name: "acute", base: "α" },
    { key: "̀", name: "grave", base: "α" },
    { key: "͂", name: "circumflex", base: "α" },
    { key: "̓́", name: "smooth acute", base: "α" },
    { key: "̔́", name: "rough acute", base: "α" },
    { key: "̓͂", name: "smooth circ.", base: "α" },
    { key: "̔͂", name: "rough circ.", base: "α" },
    { key: "ͅ", name: "iota subscript", base: "ω" },
    { key: "̈", name: "diaeresis", base: "ι" },
  ],
};
