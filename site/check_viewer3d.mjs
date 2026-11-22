// Drives headless Chrome through the site's 3D views and prints, as JSON, a lit and an unlit frame of every
// result that has a mesh, from four angles, plus any script error on any page. Used by check_viewer3d.py.
// usage: node check_viewer3d.mjs <site base url> <chrome.exe> <pages with a 3D view, comma separated> <all pages, comma separated>
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [base, chromePath, viewerPages, allPages] = process.argv.slice(2);
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn(chromePath, ["--headless=new", `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "m3d-"))}`, "--no-first-run", "about:blank"], { stdio: "ignore" });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let targets;
for (let i = 0; i < 50 && !targets; i++) {
  try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); } catch { await sleep(200); }
}
const ws = new WebSocket(targets.find(t => t.type === "page").webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener("open", r));
let id = 0; const pending = new Map(); const errors = [];
ws.addEventListener("message", e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
});
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
const script = `(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const vp = document.getElementById("vp"), btn = document.getElementById("vp-3d");
  const chips = [...document.querySelectorAll("#vp-parts button")];
  const out = {};
  for (const k of (chips.length ? chips.map((_, i) => i) : [-1])) {
    if (k >= 0) { document.querySelectorAll("#vp-parts button")[k].click(); await wait(900); }
    if (btn.hidden) continue;                       // this result has no 3D view
    if (!vp.classList.contains("is-3d")) btn.click();
    for (let i = 0; i < 60 && !vp.classList.contains("is-3d"); i++) await wait(100);
    await wait(2400);
    if (!vp.classList.contains("is-3d")) continue;
    const views = [];
    for (const [da, de] of [[0, 0], [1.2, 0.3], [2.6, -0.2], [-1.9, 0.6]]) {
      window.__m3d.turn(da, de);
      views.push({ lit: window.__m3d.snap(1), flat: window.__m3d.snap(0) });
      window.__m3d.turn(-da, -de);
    }
    out[vp.vpEntry.id] = views;
  }
  return out;
})()`;
const frames = {};
const withViewer = new Set(viewerPages.split(",").filter(Boolean));
for (const page of allPages.split(",").filter(Boolean)) {
  const before = errors.length;
  await send("Page.navigate", { url: base + page });
  await sleep(withViewer.has(page) ? 2500 : 1200);
  if (withViewer.has(page)) {
    const r = await send("Runtime.evaluate", { expression: script, returnByValue: true, awaitPromise: true });
    Object.assign(frames, r.result.result.value || {});
  }
  for (let i = before; i < errors.length; i++) errors[i] = page + ": " + errors[i];
}
console.log(JSON.stringify({ frames, errors }));
ws.close(); chrome.kill();
process.exit(0);
