// Drives headless Chrome through the page's 3D view and prints, as JSON, a lit and an unlit frame of
// every study whose viewer entry has a mesh, from four angles. Used by check_viewer3d.py.
// usage: node check_viewer3d.mjs <page url> <chrome.exe>
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [url, chromePath] = process.argv.slice(2);
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
await send("Page.navigate", { url });
await sleep(2500);
const script = `(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  document.getElementById("vp-3d").click();
  for (let i = 0; i < 50 && !document.getElementById("vp").classList.contains("is-3d"); i++) await wait(100);
  const out = {};
  const targets = [];
  for (const t of document.querySelectorAll("#gallery .card")) {
    t.click(); await wait(600);
    const chips = [...document.querySelectorAll("#vp-parts button")];
    if (chips.length) chips.forEach((_, k) => targets.push([t, k])); else targets.push([t, -1]);
  }
  for (const [t, k] of targets) {
    t.click(); await wait(1200);
    if (k >= 0) { document.querySelectorAll("#vp-parts button")[k].click(); }
    await wait(2400);
    if (!document.getElementById("vp").classList.contains("is-3d")) continue;
    const views = [];
    for (const [da, de] of [[0, 0], [1.2, 0.3], [2.6, -0.2], [-1.9, 0.6]]) {
      window.__m3d.turn(da, de);
      views.push({ lit: window.__m3d.snap(1), flat: window.__m3d.snap(0) });
      window.__m3d.turn(-da, -de);
    }
    out[document.getElementById("vp").vpEntry.id] = views;
  }
  return out;
})()`;
const r = await send("Runtime.evaluate", { expression: script, returnByValue: true, awaitPromise: true });
console.log(JSON.stringify({ frames: r.result.result.value, errors }));
ws.close(); chrome.kill();
process.exit(0);
