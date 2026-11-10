import mcq from "./mcq.js";
import { shuffle } from "./util.js";

export default {
  id: "build-construct-chain",

  generate() {
    const answer = "מֶלֶךְ הָאָרֶץ";
    const options = shuffle([answer, "הָאָרֶץ מֶלֶךְ", "מֶלֶךְ אֶרֶץ", "מַלְכֵי הָאָרֶץ"]);
    return [
      {
        type: "build-construct-chain",
        prompt: 'Build the construct chain that translates "the king of the land"',
        stimulus: '"the king of the land"',
        stimulusIsScript: false,
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