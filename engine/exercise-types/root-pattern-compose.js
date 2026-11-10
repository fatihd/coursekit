import mcq from "./mcq.js";
import { shuffle } from "./util.js";

const PATTERNS = [
  "Qal (Qatal 3ms)",
  "Qal (Qatal 1cs)",
  "Qal (Yiqtol 3ms)",
  "Qal (infinitive construct)",
  "Psalter C-stem (Piel)",
];

export default {
  id: "root-pattern-compose",

  generate(params, pool) {
    const rooted = (pool || []).filter((x) => x.root);
    const rootedVerbs = rooted.filter((x) => x.category === "verb");
    const src = params.fixed ? null : shuffle(rootedVerbs.length ? rootedVerbs : rooted)[0];

    const stimulus = src ? `${src.root} · ${PATTERNS[0]}` : "שמר · Qal (Qatal 3ms)";
    const answer = src ? src.scriptForm : "שָׁמַר";
    const distractors = (rootedVerbs.length ? rootedVerbs : rooted)
      .filter((x) => x.scriptForm !== answer)
      .map((x) => x.scriptForm)
      .slice(0, 3);
    const fallback = ["יִשְׁמֹר", "לִשְׁמֹר", "שִׁמֵּר"];
    const options = shuffle([answer, ...(distractors.length ? distractors : fallback)]);

    return [
      {
        type: "root-pattern-compose",
        prompt: "Compose the pointed form matching this root + pattern",
        stimulus,
        stimulusIsScript: true,
        options,
        answer,
        optionIsScript: true,
      },
    ];
  },

  render: mcq.render,
  collect: mcq.collect,
  grade: mcq.grade,
};