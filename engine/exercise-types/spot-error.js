import mcq from "./mcq.js";
import { shuffle } from "./util.js";

export default {
  id: "spot-error",

  generate(params, pool) {
    const phrased = (pool || []).filter((x) => x.scriptForm && x.gloss);
    const src = params.fixed ? null : shuffle(phrased)[0];
    const phrase = src ? `${src.scriptForm} ${src.gloss}` : "שָׁמַר he guarded";
    const correct = src ? src.scriptForm : "שָׁמַר";
    const wrong = shuffle(phrased.filter((x) => x.scriptForm !== correct).map((x) => x.scriptForm))[0] || "שִׁמֵּר";
    const options = shuffle([correct, wrong, `וְ${correct}`, `${correct}־`]);
    return [
      {
        type: "spot-error",
        prompt: "One word in this phrase is wrong — choose the correct spelling",
        phrase,
        stimulus: phrase,
        stimulusIsScript: true,
        options,
        answer: correct,
        optionIsScript: true,
      },
    ];
  },

  render: mcq.render,
  collect: mcq.collect,
  grade: mcq.grade,
};