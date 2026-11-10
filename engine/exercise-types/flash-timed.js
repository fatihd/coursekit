import mcq from "./mcq.js";

export default {
  id: "flash-timed",

  generate(params, pool) {
    const item = mcq.generate({ count: 1, directions: ["script->gloss"] }, pool)[0];
    return [
      {
        ...item,
        type: "flash-timed",
        prompt: (item && item.stimulus ? `Flash translation — ${item.stimulus}` : "Flash translation").slice(0, 80),
        seconds: params.seconds || 15,
      },
    ];
  },

  render(item, ctx) {
    const root = mcq.render(item, ctx);
    const timer = document.createElement("span");
    timer.className = "ex-timer ex-hint";
    timer.textContent = `⏱ ${item.seconds || 15}s`;
    root.prepend(timer);
    const start = Date.now();
    const deadline = start + (item.seconds || 15) * 1000;
    const tick = () => {
      const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
      timer.textContent = `⏱ ${left}s`;
      if (left <= 0) {
        clearInterval(iv);
        root.querySelectorAll(".ex-option").forEach((b) => b.disabled = true);
      } else {
        iv = setTimeout(tick, 1000);
      }
    };
    let iv = setTimeout(tick, 1000);
    return root;
  },

  collect: mcq.collect,
  grade: mcq.grade,
};