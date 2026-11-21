/* Interactive 3D view for the result viewer. Plain WebGL2, no library.
   Loads site/v2/m3d_<id>.bin (written by make_mesh3d.py from the same surface and field as the Blender
   render) only when asked. Colours: the field is banded per pixel exactly as the render's shader does,
   floor(s * bands), with the legend's colours; lighting only scales brightness, and keeps a high floor
   so a shaded face still reads as its band. */
(() => {
  const vp = document.getElementById("vp");
  const stage = vp.querySelector(".stage");
  const img = document.getElementById("vp-img");
  const btn = document.getElementById("vp-3d");
  const hint = document.getElementById("vp-hint");
  if (!btn) return;
  const probe = document.createElement("canvas");
  if (!probe.getContext("webgl2")) { btn.remove(); return; }

  let entry = null, active = false, want3d = false, canvas = null, gl = null, prog = null, lineProg = null, mesh = null;
  let az = 0, el = 0, dist = 1, dist0 = 1, az0 = 0, el0 = 0, lit = 1, frame = 0;
  const cache = new Map();

  const VS = `#version 300 es
  in vec3 aQ; in float aS;
  uniform vec3 uLo, uSpan; uniform mat4 uMVP;
  out float vS; out vec3 vP;
  void main() { vec3 p = uLo + aQ * uSpan; vP = p; vS = aS; gl_Position = uMVP * vec4(p, 1.0); }`;
  const FS = `#version 300 es
  precision highp float;
  in float vS; in vec3 vP;
  uniform vec3 uBands[16]; uniform int uN; uniform vec3 uEye; uniform float uLit;
  out vec4 o;
  void main() {
    int b = clamp(int(floor(vS * float(uN))), 0, uN - 1);
    vec3 c = uBands[b];
    vec3 n = normalize(cross(dFdx(vP), dFdy(vP)));
    vec3 v = normalize(uEye - vP);
    float d = abs(dot(n, v));                       // headlight: faces toward the viewer are brightest
    float k = mix(1.0, 0.80 + 0.20 * d, uLit);       // floor 0.80 keeps every face legible (checked)
    o = vec4(c * k, 1.0);
  }`;
  const LVS = `#version 300 es
  in vec3 aP; uniform mat4 uMVP; void main() { gl_Position = uMVP * vec4(aP, 1.0); }`;
  const LFS = `#version 300 es
  precision highp float; out vec4 o; void main() { o = vec4(0.16, 0.18, 0.22, 1.0); }`;

  function compile(vs, fs) {
    const p = gl.createProgram();
    for (const [t, src] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) {
      const s = gl.createShader(t); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      gl.attachShader(p, s);
    }
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    return p;
  }

  function parse(buf) {
    const h = new Uint32Array(buf, 0, 8);
    if (h[0] !== 0x3144334D) throw new Error("not a mesh file");
    const [nv, nt, ne, ib] = [h[1], h[2], h[3], h[4]];
    let o = 32;
    const box = new Float32Array(buf, o, 6); o += 24;
    const q = new Uint16Array(buf, o, 3 * nv); o += 6 * nv; o += (4 - o % 4) % 4;
    const s = new Float32Array(buf, o, nv); o += 4 * nv;
    const idx = ib === 2 ? new Uint16Array(buf, o, 3 * nt) : new Uint32Array(buf, o, 3 * nt);
    o += ib * 3 * nt; o += (4 - o % 4) % 4;
    const lines = new Float32Array(buf, o, 6 * ne);
    return { nv, nt, ne, ib, box, q, s, idx, lines };
  }

  function upload(m) {
    const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
    const bq = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bq); gl.bufferData(gl.ARRAY_BUFFER, m.q, gl.STATIC_DRAW);
    const lq = gl.getAttribLocation(prog, "aQ"); gl.enableVertexAttribArray(lq);
    gl.vertexAttribPointer(lq, 3, gl.UNSIGNED_SHORT, true, 0, 0);
    const bs = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bs); gl.bufferData(gl.ARRAY_BUFFER, m.s, gl.STATIC_DRAW);
    const ls = gl.getAttribLocation(prog, "aS"); gl.enableVertexAttribArray(ls);
    gl.vertexAttribPointer(ls, 1, gl.FLOAT, false, 0, 0);
    const bi = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, bi); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, m.idx, gl.STATIC_DRAW);
    m.vao = vao;
    if (m.ne) {
      m.lvao = gl.createVertexArray(); gl.bindVertexArray(m.lvao);
      const bl = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bl); gl.bufferData(gl.ARRAY_BUFFER, m.lines, gl.STATIC_DRAW);
      const la = gl.getAttribLocation(lineProg, "aP"); gl.enableVertexAttribArray(la);
      gl.vertexAttribPointer(la, 3, gl.FLOAT, false, 0, 0);
    }
    gl.bindVertexArray(null);
    const lo = [m.box[0], m.box[1], m.box[2]], hi = [m.box[3], m.box[4], m.box[5]];
    m.lo = lo; m.span = hi.map((v, i) => (v > lo[i] ? v - lo[i] : 1));
    m.centre = hi.map((v, i) => (v + lo[i]) / 2);
    m.radius = Math.hypot(...hi.map((v, i) => v - lo[i])) / 2;
  }

  // column-major 4x4 helpers
  const persp = (fy, a, n, f) => { const t = 1 / Math.tan(fy / 2); return [t / a, 0, 0, 0, 0, t, 0, 0, 0, 0, (f + n) / (n - f), -1, 0, 0, 2 * f * n / (n - f), 0]; };
  const sub = (a, b) => a.map((v, i) => v - b[i]);
  const norm = a => { const l = Math.hypot(...a); return a.map(v => v / l); };
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  function lookAt(eye, at, up) {
    const z = norm(sub(eye, at)), x = norm(cross(up, z)), y = cross(z, x);
    return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, eye), -dot(y, eye), -dot(z, eye), 1];
  }
  const mul = (a, b) => { const r = new Array(16).fill(0); for (let c = 0; c < 4; c++) for (let rr = 0; rr < 4; rr++) for (let k = 0; k < 4; k++) r[c * 4 + rr] += a[k * 4 + rr] * b[c * 4 + k]; return r; };

  const FOV = 28 * Math.PI / 180;
  function eye() {
    const c = mesh.centre;
    return [c[0] + dist * Math.cos(el) * Math.cos(az), c[1] + dist * Math.cos(el) * Math.sin(az), c[2] + dist * Math.sin(el)];
  }
  function draw() {
    frame = 0;
    if (!active || !mesh) return;
    const w = canvas.width, h = canvas.height;
    gl.viewport(0, 0, w, h);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    const e = eye();
    const mvp = mul(persp(FOV, w / h, mesh.radius * 0.05, dist + mesh.radius * 4), lookAt(e, mesh.centre, [0, 0, 1]));
    gl.useProgram(prog);
    gl.uniformMatrix4fv(gl.getUniformLocation(prog, "uMVP"), false, mvp);
    gl.uniform3fv(gl.getUniformLocation(prog, "uLo"), mesh.lo);
    gl.uniform3fv(gl.getUniformLocation(prog, "uSpan"), mesh.span);
    gl.uniform3fv(gl.getUniformLocation(prog, "uEye"), e);
    gl.uniform1f(gl.getUniformLocation(prog, "uLit"), lit);
    const bands = entry.bands.map(hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255));
    const flatB = new Float32Array(48); bands.forEach((c, i) => flatB.set(c, 3 * i));
    gl.uniform3fv(gl.getUniformLocation(prog, "uBands"), flatB);
    gl.uniform1i(gl.getUniformLocation(prog, "uN"), bands.length);
    gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(1, 1);
    gl.bindVertexArray(mesh.vao);
    gl.drawElements(gl.TRIANGLES, 3 * mesh.nt, mesh.ib === 2 ? gl.UNSIGNED_SHORT : gl.UNSIGNED_INT, 0);
    gl.disable(gl.POLYGON_OFFSET_FILL);
    if (mesh.ne && lit) {
      gl.useProgram(lineProg);
      gl.uniformMatrix4fv(gl.getUniformLocation(lineProg, "uMVP"), false, mvp);
      gl.bindVertexArray(mesh.lvao);
      gl.drawArrays(gl.LINES, 0, 2 * mesh.ne);
    }
    gl.bindVertexArray(null);
  }
  const redraw = () => { if (!frame) frame = requestAnimationFrame(draw); };

  function resize() {
    if (!canvas) return;
    const r = stage.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.round(r.width * dpr)); canvas.height = Math.max(1, Math.round(r.height * dpr));
    if (mesh) {           // the stage can change size (a tab's image loads): keep the framing, and any zoom
      const f = fitDistance(), zoom = dist / dist0;
      dist0 = f; dist = f * zoom;
    }
    redraw();
  }

  function setup() {
    canvas = document.createElement("canvas");
    canvas.className = "vp-canvas";
    canvas.setAttribute("role", "img");
    stage.appendChild(canvas);
    gl = canvas.getContext("webgl2", { antialias: true, alpha: true, premultipliedAlpha: true });
    prog = compile(VS, FS); lineProg = compile(LVS, LFS);
    new ResizeObserver(resize).observe(stage);
    const pts = new Map();
    let pinch0 = 0, distAtPinch = 1;
    canvas.addEventListener("pointerdown", e => { canvas.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]); if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch0 = Math.hypot(a[0] - b[0], a[1] - b[1]); distAtPinch = dist; } });
    canvas.addEventListener("pointermove", e => {
      if (!pts.has(e.pointerId)) return;
      const [px, py] = pts.get(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]);
      if (pts.size === 1) {
        az -= (e.clientX - px) * 0.008;
        el = Math.max(-1.5, Math.min(1.5, el + (e.clientY - py) * 0.008));
      } else if (pts.size === 2 && pinch0) {
        const [a, b] = [...pts.values()];
        dist = clampDist(distAtPinch * pinch0 / Math.max(1, Math.hypot(a[0] - b[0], a[1] - b[1])));
      }
      redraw();
    });
    const up = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch0 = 0; };
    canvas.addEventListener("pointerup", up); canvas.addEventListener("pointercancel", up);
    canvas.addEventListener("wheel", e => { e.preventDefault(); dist = clampDist(dist * Math.exp(e.deltaY * 0.0012)); redraw(); }, { passive: false });
    canvas.addEventListener("dblclick", () => { az = az0; el = el0; dist = dist0; redraw(); });
    canvas.tabIndex = 0;              // keyboard: arrows turn, + and - zoom, 0 resets
    canvas.addEventListener("keydown", e => {
      const k = e.key, step = 0.12;
      if (k === "ArrowLeft") az += step; else if (k === "ArrowRight") az -= step;
      else if (k === "ArrowUp") el = Math.min(1.5, el + step); else if (k === "ArrowDown") el = Math.max(-1.5, el - step);
      else if (k === "+" || k === "=") dist = clampDist(dist / 1.15); else if (k === "-") dist = clampDist(dist * 1.15);
      else if (k === "0") { az = az0; el = el0; dist = dist0; } else return;
      e.preventDefault(); redraw();
    });
  }
  // camera distance at which the bounding box fills FILL of the frame at the opening angle, as the
  // render's camera is framed: a point at offset p needs dist >= p.d + |p.right| / (tan(half fov) * FILL)
  function fitDistance() {
    const FILL = 0.84, d = [Math.cos(el) * Math.cos(az), Math.cos(el) * Math.sin(az), Math.sin(el)];
    const right = norm(cross([0, 0, 1], d)), upv = cross(d, right);
    const tv = Math.tan(FOV / 2), th = tv * canvas.width / Math.max(1, canvas.height);
    let need = 0;
    for (let k = 0; k < 8; k++) {
      const c = [k & 1 ? mesh.box[3] : mesh.box[0], k & 2 ? mesh.box[4] : mesh.box[1], k & 4 ? mesh.box[5] : mesh.box[2]];
      const p = sub(c, mesh.centre);
      need = Math.max(need, dot(p, d) + Math.abs(dot(p, right)) / (th * FILL), dot(p, d) + Math.abs(dot(p, upv)) / (tv * FILL));
    }
    return need;
  }
  const clampDist = d => Math.max(dist0 * 0.3, Math.min(dist0 * 3, d));

  async function load(v) {
    entry = v;
    let m = cache.get(v.mesh);
    if (!m) {
      btn.disabled = true; btn.textContent = `Loading ${v.mesh_kb} KB…`;
      try {
        const r = await fetch(v.mesh);
        if (!r.ok) throw new Error(r.status);
        m = parse(await r.arrayBuffer());
      } catch (err) {
        btn.disabled = false; btn.textContent = "3D view unavailable"; return false;
      }
      upload(m); cache.set(v.mesh, m);
      btn.disabled = false;
      btn.textContent = active ? "Back to the render" : "Rotate in 3D";
    }
    if (entry !== v) return false;
    mesh = m;
    az = az0 = v.azim * Math.PI / 180; el = el0 = v.elev * Math.PI / 180;
    canvas.setAttribute("aria-label", `${v.model}, interactive 3D view: arrow keys turn it, plus and minus zoom, 0 resets`);
    dist = dist0 = 1;
    resize();
    return true;
  }

  async function enter() {
    if (!entry || !entry.mesh) return;
    if (!canvas) setup();
    if (!(await load(entry))) return;
    active = true; vp.classList.add("is-3d");
    btn.textContent = "Back to the render"; btn.setAttribute("aria-pressed", "true");
    hint.hidden = false; redraw();
  }
  function leave() {
    active = false; vp.classList.remove("is-3d");
    btn.textContent = "Rotate in 3D"; btn.setAttribute("aria-pressed", "false"); hint.hidden = true;
  }
  btn.addEventListener("click", () => { want3d = !active; return active ? leave() : enter(); });

  // the choice of 3D carries across tabs: a tab without a mesh shows its render, the next one with a
  // mesh goes back to 3D
  vp.addEventListener("vpchange", async e => {
    const v = e.detail;
    entry = v;
    btn.hidden = !v.mesh;
    if (!v.mesh) { if (active) leave(); return; }
    if (active) { if (!(await load(v))) leave(); else redraw(); }
    else if (want3d) enter();
  });

  if (vp.vpEntry) { entry = vp.vpEntry; btn.hidden = !entry.mesh; }

  // for the page's own checks: draw without lighting, to compare the lit view with the true bands
  // (snap draws one frame and reads it back in the same task, so no preserved drawing buffer is needed)
  window.__m3d = {
    state: () => ({ active, az, el, dist }),
    snap: k => { lit = k; draw(); const url = canvas.toDataURL("image/png"); lit = 1; redraw(); return url; },
    turn: (daz, del) => { az += daz; el = Math.max(-1.5, Math.min(1.5, el + del)); draw(); },
  };
})();
