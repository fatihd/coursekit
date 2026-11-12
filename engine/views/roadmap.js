import { confirmAction } from "../dom.js";
import { unitState } from "../store.js";

export function renderRoadmap(root, course, progress, navigate, sync) {
  root.replaceChildren();

  const header = document.createElement("header");
  header.className = "roadmap-header";
  const h1 = document.createElement("h1");
  h1.textContent = course.title;
  header.appendChild(h1);

  const stats = document.createElement("p");
  stats.className = "roadmap-stats";
  const done = course.units.filter((u) => unitState(progress, u.n) === "done").length;
  stats.textContent = `${done} of ${course.units.length} units complete`;
  header.appendChild(stats);

  if (sync) {
    const box = document.createElement("div");
    box.className = "sync";
    const status = document.createElement("span");
    status.className = "sync-status";

    const exportBtn = document.createElement("button");
    exportBtn.type = "button";
    exportBtn.className = "gate-btn";
    exportBtn.textContent = "Export progress";
    exportBtn.addEventListener("click", () => {
      sync.onExport();
      status.textContent = "Progress file downloaded. Keep it safe; import it in any browser.";
    });

    const file = document.createElement("input");
    file.type = "file";
    file.accept = ".json,application/json";
    file.hidden = true;
    file.addEventListener("change", async () => {
      if (!file.files.length) return;
      const r = await sync.onImport(file.files[0]);
      file.value = "";
      if (!r.ok) {
        status.textContent = `Import failed: ${r.error}`;
        return;
      }
      navigate("roadmap");
      const s = document.querySelector(".sync-status");
      if (s) s.textContent = r.added > 0 ? `Imported: ${r.added} more unit(s) complete.` : "Imported: nothing new — your progress was already up to date.";
    });

    const importBtn = document.createElement("button");
    importBtn.type = "button";
    importBtn.className = "gate-btn";
    importBtn.textContent = "Import progress";
    importBtn.addEventListener("click", () => file.click());

    const last = progress.lastExportedAt;
    if (!last) {
      status.textContent = progress.updatedAt ? "Progress is stored in this browser only — export it to keep a copy." : "";
    } else if (progress.updatedAt && progress.updatedAt > last) {
      status.textContent = `Last exported ${last.slice(0, 10)}; you have made progress since.`;
    } else {
      status.textContent = `Last exported ${last.slice(0, 10)}.`;
    }

    box.append(exportBtn, importBtn, file);
    if (sync.onReset) {
      box.appendChild(confirmAction("Reset all progress…",
        "Erase all progress for this course in this browser? Export it first if you may want it back.",
        "Erase progress", () => {
          sync.onReset();
          navigate("roadmap");
          const s = document.querySelector(".sync-status");
          if (s) s.textContent = "Progress reset.";
        }, "progress-reset"));
    }
    box.appendChild(status);
    header.appendChild(box);
  }

  root.appendChild(header);

  for (const part of course.parts) {
    const section = document.createElement("section");
    section.className = "part";

    const h2 = document.createElement("h2");
    h2.textContent = `${part.n}. ${part.title}`;
    section.appendChild(h2);

    const grid = document.createElement("div");
    grid.className = "roadmap";

    for (const u of course.units) {
      if (u.part !== part.n) continue;
      const state = unitState(progress, u.n);

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `unit unit--${state}`;
      btn.dataset.unit = u.n;

      const num = document.createElement("span");
      num.className = "unit-n";
      num.textContent = String(u.n);

      const title = document.createElement("span");
      title.className = "unit-title";
      title.textContent = u.title;

      btn.append(num, title);
      const stars = sync && sync.stars ? sync.stars(u.n) : null;
      if (stars && stars.length) {
        const s = document.createElement("span");
        s.className = "unit-stars";
        s.setAttribute("aria-label", `${stars.filter(Boolean).length} of ${stars.length} ladder rungs complete`);
        s.textContent = stars.map((x) => (x ? "★" : "☆")).join("");
        btn.appendChild(s);
      }
      btn.addEventListener("click", () => navigate("lesson", u.n));
      grid.appendChild(btn);
    }

    section.appendChild(grid);
    root.appendChild(section);
  }
}
