import mcq from "./mcq.js";

export default {
  id: "paradigm-tag",

  generate() {
    return [
      {
        type: "paradigm-tag",
        prompt: "Classify this Qatal verb by person, gender and number",
        stimulus: "קָטַלְתִּי",
        stimulusIsScript: true,
        options: ["1cs", "2ms", "3ms", "3fs"],
        answer: "1cs",
        optionIsScript: false,
      },
    ];
  },

  render: mcq.render,
  collect: mcq.collect,
  grade: mcq.grade,
};
