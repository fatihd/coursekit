import mcq from "./mcq.js";

const BINYANIM = ["Qal", "Niphal", "Piel", "Pual", "Hiphil", "Hophal", "Hithpael"];

export default {
  id: "identify-binyan",

  generate() {
    return [
      {
        type: "identify-binyan",
        prompt: "Identify the binyan (verbal stem) of this verb form",
        stimulus: "שָׁמַר",
        stimulusIsScript: true,
        options: BINYANIM.slice(),
        answer: "Qal",
        optionIsScript: false,
      },
    ];
  },

  render: mcq.render,
  collect: mcq.collect,
  grade: mcq.grade,
};