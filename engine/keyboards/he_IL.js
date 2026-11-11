export default {
  id: "he_IL",
  rows: [
    [
      { key: "א" }, { key: "ב" }, { key: "ג" }, { key: "ד" }, { key: "ה" },
      { key: "ו" }, { key: "ז" }, { key: "ח" }, { key: "ט" }, { key: "י" },
    ],
    [
      { key: "כ" }, { key: "ל" }, { key: "מ" }, { key: "נ" }, { key: "ס" },
      { key: "ע" }, { key: "פ" }, { key: "צ" }, { key: "ק" }, { key: "ר" },
    ],
    [
      { key: "ש" }, { key: "ת" }, { key: "ם" }, { key: "ן" }, { key: "ף" }, { key: "ץ" }, { key: "ך" },
      { key: "⌫", action: "backspace", label: "⌫" },
    ],
    [
      { key: " ", action: "space", label: "space" },
      { key: "done", action: "done", label: "done" },
    ],
  ],
  niqqud: [
    { key: "ָ", name: "qamets" }, { key: "ַ", name: "patah" }, { key: "ֶ", name: "segol" },
    { key: "ֵ", name: "tsere" }, { key: "ִ", name: "hiriq" }, { key: "ֹ", name: "holem" },
    { key: "ֻ", name: "qibbuts" }, { key: "ְ", name: "shewa" }, { key: "ֲ", name: "hatef patah" },
    { key: "ֱ", name: "hatef segol" }, { key: "ֳ", name: "hatef qamets" }, { key: "ּ", name: "dagesh" },
    { key: "ׁ", name: "shin dot", base: "ש" }, { key: "ׂ", name: "sin dot", base: "ש" },
    { key: "־", name: "maqqef", base: "" },
  ],
};
