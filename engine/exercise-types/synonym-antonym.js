import matchByLine from "./match-by-line.js";

export default {
  id: "synonym-antonym",

  generate() {
    return [
      {
        type: "synonym-antonym",
        prompt: "Match each word with its opposite",
        left: ["טוֹב", "גָּדוֹל", "יוֹם", "אוֹר"],
        right: ["לַיְלָה", "רַע", "קָטֹן", "חֹשֶׁךְ"],
        answer: {
          טוֹב: "רַע",
          גָּדוֹל: "קָטֹן",
          יוֹם: "לַיְלָה",
          אוֹר: "חֹשֶׁךְ",
        },
        leftIsScript: true,
      },
    ];
  },

  render: matchByLine.render,
  collect: matchByLine.collect,
  grade: matchByLine.grade,
};
