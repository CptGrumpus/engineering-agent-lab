// Result viewer: one or more results (window.VP, written by build_v2.py) shown in the dark viewport, with the
// legend in the CAE convention, the render checks as the status line, a switch between a page's results,
// and a load-step slider where a result has frames. viewer3d.js adds the 3D view on top of this.
(() => {
  const VP = window.VP || [];
  const vp = document.getElementById("vp");
  if (!vp || !VP.length) return;
  const img = document.getElementById("vp-img");
  const sw = document.getElementById("lg-sw"), ticks = document.getElementById("lg-ticks");
  const title = document.getElementById("lg-title"), status = document.getElementById("vp-status");
  const partsBar = document.getElementById("vp-parts");
  const reduce = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const sci = v => (v < 0 ? "-" : "+") + Math.abs(v).toExponential(3).replace(/e([+-])(\d)$/, "e$10$2");
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  window.addEventListener("load", () => VP.forEach(v => { const p = new Image(); p.src = v.img; }));

  // the 3D view listens for changes; the current entry is also kept on the element for late listeners
  const announce = v => { vp.vpEntry = v; vp.dispatchEvent(new CustomEvent("vpchange", { detail: v })); };
  function paint(v) {
    vp.classList.toggle("is-figure", v.kind === "figure");
    vp.classList.toggle("is-plain", v.kind === "plain");
    if (v.bands) {
      const n = v.bands.length;
      sw.innerHTML = v.bands.slice().reverse().map(c => `<i style="background:${c}"></i>`).join("");
      ticks.innerHTML = Array.from({ length: n + 1 }, (_, i) => {
        const val = v.vmax - (v.vmax - v.vmin) * i / n;
        // a dimensionless ratio reads better as 0.80 than +8.000e-01; solver fields keep the solver's style
        return `<span style="top:${(100 * i / n).toFixed(3)}%">${v.fixed != null ? val.toFixed(v.fixed) : sci(val)}</span>`;
      }).join("");
      title.innerHTML = `${esc(v.legend)}<small>${esc(v.unit)}</small>`;
    } else { sw.innerHTML = ""; ticks.innerHTML = ""; title.innerHTML = ""; }
    status.innerHTML = `<b>${esc(v.model)}</b>` + v.lines.map(l => `<span>${esc(l)}</span>`).join("") +
      (v.check ? `<span class="chk">${esc(v.check)}</span>` : "") +
      (v.href ? `<a class="vp-link" href="${esc(v.href)}">Read this study →</a>` : "");
    img.alt = v.model;
  }

  // load-step slider: results with frames can be stepped through, or played
  const scrub = document.getElementById("vp-scrub"), range = document.getElementById("vp-range");
  const step = document.getElementById("vp-step"), play = document.getElementById("vp-play");
  let timer = null, current = -1;
  const loaded = new Set();
  const stopPlay = () => { clearInterval(timer); timer = null; play.textContent = "▶"; play.setAttribute("aria-label", "Play the analysis step by step"); };
  const preload = v => { if (loaded.has(v.id)) return; loaded.add(v.id); v.frames.forEach(f => { const p = new Image(); p.src = f.img; }); };
  function setFrame(k) {
    const f = VP[current].frames[k];
    range.value = k; img.src = f.img; step.textContent = f.text;
  }
  function setupScrub(v) {
    stopPlay();
    scrub.hidden = !v.frames;
    if (!v.frames) return;
    range.max = v.frames.length - 1; range.value = v.frames_main;
    step.textContent = v.frames[v.frames_main].text;
  }
  range.addEventListener("input", () => { stopPlay(); preload(VP[current]); setFrame(+range.value); });
  play.addEventListener("click", () => {
    const v = VP[current];
    if (timer) return stopPlay();
    preload(v);
    let k = +range.value >= v.frames.length - 1 ? 0 : +range.value;
    setFrame(k);
    play.textContent = "❚❚"; play.setAttribute("aria-label", "Pause");
    timer = setInterval(() => { k += 1; if (k >= v.frames.length) return stopPlay(); setFrame(k); }, 220);
  });

  function show(i) {
    if (i === current) return;
    const first = current < 0;
    current = i;
    announce(VP[i]);
    setupScrub(VP[i]);
    partsBar.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", +b.dataset.i === i ? "true" : "false"));
    if (first || reduce()) { img.src = VP[i].img; paint(VP[i]); return; }
    vp.classList.add("switching");
    setTimeout(() => {
      img.src = VP[i].img; paint(VP[i]);
      const done = () => requestAnimationFrame(() => vp.classList.remove("switching"));
      if (img.complete) done(); else img.onload = done;
    }, 220);
  }

  // a page with several results (a report of related studies, or the home page's highlights) gets a switch
  partsBar.hidden = VP.length < 2;
  if (VP.length > 1) {
    partsBar.innerHTML = VP.map((v, i) => `<button type="button" data-i="${i}" aria-pressed="false">${esc(v.part || v.tab || v.model)}</button>`).join("");
    partsBar.addEventListener("click", e => {
      const b = e.target.closest("button[data-i]");
      if (b) show(+b.dataset.i);
    });
  }

  // a link to one study of a report (page.html#study) opens the viewer on that study's result
  const fromHash = () => {
    const key = decodeURIComponent(location.hash.slice(1));
    const i = VP.findIndex(v => v.study === key);
    if (i >= 0) show(i);
    return i >= 0;
  };
  window.addEventListener("hashchange", fromHash);
  if (!fromHash()) show(Math.max(0, VP.findIndex(v => v.main)));
})();
