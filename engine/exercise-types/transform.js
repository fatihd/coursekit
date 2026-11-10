import mcq from "./mcq.js";

export default {
  id: "transform",

  generate() {
    return [
      {
        type: "transform",
        prompt: "Convert the Yiqtol verb to its Wayyiqtol form",
        stimulus: "יִשְׁמֹר",
        stimulusIsScript: true,
        options: ["וַיִּשְׁמֹר", "יִשְׁמֹר", "שָׁמַר", "וְשָׁמַר"],
        answer: "וַיִּשְׁמֹר",
        optionIsScript: true,
      },
    ];
  },

  render: mcq.render,
  collect: mcq.collect,
  grade: mcq.grade,
};
