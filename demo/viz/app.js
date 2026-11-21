/* Visor del registro de eventos (tarea 15a).
 *
 * Entrada: JSONL con un Event de contracts por línea (lo que escribe
 * python -m eval.replay ... --out x.jsonl). Usa tool_call, decision y rotation;
 * cualquier otro kind se ignora.
 */
"use strict";

/* ------------------------------------------------------------------ datos */

function parseJsonl(text) {
  const events = [];
  text.split(/\r?\n/).forEach((line, i) => {
    line = line.trim();
    if (!line) return;
    try {
      events.push(JSON.parse(line));
    } catch (err) {
      throw new Error(`línea ${i + 1}: JSON inválido (${err.message})`);
    }
  });
  return events;
}

/**
 * Función pura: eventos -> lista ordenada por t de {t, call, decision, rotations}.
 * La decisión se une a su llamada por call_id. Una rotación se asigna a la
 * llamada de su call_id o, si no lo trae, a la última llamada anterior en el archivo.
 */
function buildFrames(events) {
  const byId = new Map();
  const order = [];
  let lastId = null;
  const pendingDecisions = [];
  const pendingRotations = [];

  for (const ev of events || []) {
    if (!ev || typeof ev !== "object") continue;
    if (ev.kind === "tool_call" && ev.data) {
      const id = ev.call_id || ev.data.id;
      if (!byId.has(id)) {
        byId.set(id, { t: ev.data.t, call: ev.data, decision: null, rotations: [] });
        order.push(id);
      }
      lastId = id;
    } else if (ev.kind === "decision") {
      pendingDecisions.push(ev);
    } else if (ev.kind === "rotation") {
      pendingRotations.push({ ev, fallback: lastId });
    }
  }

  for (const ev of pendingDecisions) {
    const frame = byId.get(ev.call_id);
    if (frame) frame.decision = ev.data;
  }
  for (const { ev, fallback } of pendingRotations) {
    const frame = byId.get(ev.call_id) || byId.get(fallback);
    if (frame) frame.rotations.push(ev.data);
  }

  return order.map((id) => byId.get(id)).sort((a, b) => a.t - b.t);
}

function secretIds(frames) {
  const ids = new Set();
  for (const f of frames) {
    for (const k of Object.keys((f.decision && f.decision.leak) || {})) ids.add(k);
    for (const r of f.rotations) if (r && r.secret_id) ids.add(r.secret_id);
  }
  return [...ids].sort();
}

function bitsAt(frame, sid) {
  const l = frame.decision && frame.decision.leak && frame.decision.leak[sid];
  return l ? l.bits : 0;
}

function actionClass(action) {
  if (action === "block") return "a-block";
  if (action === "rotate+allow" || action === "rotate+block") return "a-rotate";
  return "a-allow";
}

function summarizeArgs(args, max = 80) {
  let s;
  if (!args || typeof args !== "object") s = String(args ?? "");
  else {
    const vals = Object.entries(args)
      .filter(([, v]) => v !== "" && v !== null && !(typeof v === "object" && !Object.keys(v).length))
      .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`);
    s = vals.join(" ");
  }
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { parseJsonl, buildFrames, secretIds, bitsAt, actionClass, summarizeArgs };
}

/* ------------------------------------------------------------------ página */

// La página del visor solo arranca si su HTML está presente: split.html carga
// este archivo para reutilizar buildFrames sin levantar el visor simple.
if (typeof document !== "undefined" && document.getElementById("call-list")) {
  const BASE_MS = 700;
  const state = { frames: [], idx: -1, speed: 1, timer: null, secrets: [] };
  const $ = (id) => document.getElementById(id);
  const color = (sid) => d3.schemeTableau10[state.secrets.indexOf(sid) % 10];
  const lbl = (id) => (typeof labelWithId === "function" ? labelWithId(id) : id);

  function load(text) {
    stop();
    state.frames = buildFrames(parseJsonl(text));
    // Solo los secretos que alguna vez tienen bits (el detector reporta todos, casi siempre en 0).
    const withBits = secretIds(state.frames).filter((sid) => state.frames.some((f) => bitsAt(f, sid) > 0));
    state.secrets = withBits.length ? withBits : secretIds(state.frames);
    state.idx = state.frames.length ? 0 : -1;
    renderList();
    render();
  }

  function loadUrl(url) {
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.text();
      })
      .then(load)
      .catch((err) => showError(`No se pudo cargar ${url}: ${err.message}`));
  }

  function showError(msg) {
    $("detail").innerHTML = "";
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = msg;
    $("detail").appendChild(p);
  }

  /* ---- lista */

  function renderList() {
    const ol = $("call-list");
    ol.innerHTML = "";
    state.frames.forEach((f, i) => {
      const li = document.createElement("li");
      li.dataset.i = i;
      li.className = actionClass(f.decision && f.decision.action);
      li.innerHTML =
        `<span class="t"></span><span class="tool"></span><span class="args"></span><span class="marks"></span>`;
      li.children[0].textContent = f.t;
      li.children[1].textContent = f.call.tool;
      const summary = summarizeArgs(f.call.args);
      li.children[2].textContent = summary;
      li.children[2].title = summary;
      if (f.call.is_sink) li.children[3].insertAdjacentHTML("beforeend", `<span class="mark sink">sumidero</span>`);
      if (f.call.untrusted)
        li.children[3].insertAdjacentHTML("beforeend", `<span class="mark untrusted">no confiable</span>`);
      li.addEventListener("click", () => { stop(); state.idx = i; render(); });
      ol.appendChild(li);
    });
  }

  function updateList() {
    const items = $("call-list").children;
    for (let i = 0; i < items.length; i++) {
      items[i].hidden = i > state.idx; // no se muestra el futuro
      items[i].classList.toggle("current", i === state.idx);
    }
    const cur = items[state.idx];
    if (cur) cur.scrollIntoView({ block: "nearest" });
  }

  /* ---- curvas */

  function chart(el, series, yLabel, opts = {}) {
    el.innerHTML = "";
    const { width, height } = el.getBoundingClientRect();
    if (!width || !height || !state.frames.length) return;
    const m = { top: 22, right: 12, bottom: 22, left: 40 };
    const w = width - m.left - m.right;
    const h = height - m.top - m.bottom;
    const svg = d3.select(el).append("svg").attr("viewBox", `0 0 ${width} ${height}`);
    const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);

    const tMin = state.frames[0].t;
    const tMax = state.frames[state.frames.length - 1].t;
    const x = d3.scaleLinear().domain([tMin, Math.max(tMax, tMin + 1)]).range([0, w]);
    const yMax = d3.max(series, (s) => d3.max(s.all, (p) => p.y)) || 1;
    const y = d3.scaleLinear().domain([0, yMax * 1.1]).nice().range([h, 0]);

    g.append("g").attr("class", "gridline").call(d3.axisLeft(y).ticks(4).tickSize(-w).tickFormat(""))
      .call((s) => s.select(".domain").remove());
    g.append("g").attr("class", "axis").attr("transform", `translate(0,${h})`)
      .call(d3.axisBottom(x).ticks(Math.min(10, tMax - tMin)).tickFormat(d3.format("d")));
    g.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(4));
    g.append("text").attr("x", -m.left + 4).attr("y", -9)
      .style("fill", "var(--muted)").style("font-size", "11px").text(yLabel);

    const shown = state.frames.slice(0, state.idx + 1);
    if (opts.rotations) {
      for (const f of shown) {
        for (const r of f.rotations) {
          g.append("line").attr("class", "rotation-line")
            .attr("x1", x(f.t)).attr("x2", x(f.t)).attr("y1", 0).attr("y2", h);
          g.append("text").attr("class", "rotation-label").attr("x", x(f.t) + 3).attr("y", 10)
            .text(`rotación ${r.secret_id}`);
        }
      }
    }
    if (shown.length) {
      const cx = x(shown[shown.length - 1].t);
      g.append("line").attr("class", "cursor-line").attr("x1", cx).attr("x2", cx).attr("y1", 0).attr("y2", h);
    }

    const line = d3.line().x((p) => x(p.t)).y((p) => y(p.y)).curve(d3.curveStepAfter);
    series.forEach((s) => {
      const pts = s.all.slice(0, state.idx + 1);
      g.append("path").datum(pts).attr("fill", "none").style("stroke", s.color).attr("stroke-width", 2)
        .attr("d", line);
      if (pts.length)
        g.append("circle").attr("r", 3).style("fill", s.color)
          .attr("cx", x(pts[pts.length - 1].t)).attr("cy", y(pts[pts.length - 1].y));
    });

    if (series.length > 1 || opts.legend) {
      // Leyenda horizontal en el margen superior, para no tapar curvas ni rotaciones.
      // Etiquetas del escenario (scenario.js) cuando existen; si no, el id.
      const names = series.map((s) => (typeof labelWithId === "function" ? labelWithId(s.name) : s.name));
      const widths = names.map((n) => 24 + n.length * 6.2);
      const total = widths.reduce((a, b) => a + b, 0);
      const lg = g.append("g").attr("class", "legend")
        .attr("transform", `translate(${Math.max(0, w - total)},-18)`);
      let xoff = 0;
      series.forEach((s, i) => {
        const row = lg.append("g").attr("transform", `translate(${xoff},0)`);
        xoff += widths[i];
        row.append("rect").attr("width", 10).attr("height", 10).attr("y", -1).style("fill", s.color);
        row.append("text").attr("x", 14).attr("y", 8).text(names[i]);
      });
    }
  }

  function renderCharts() {
    const bits = state.secrets.map((sid) => ({
      name: sid, color: color(sid), all: state.frames.map((f) => ({ t: f.t, y: bitsAt(f, sid) })),
    }));
    chart($("chart-bits"), bits, "bits", { rotations: true, legend: true });
    const s = [{ name: "S", color: "var(--current)", all: state.frames.map((f) => ({ t: f.t, y: (f.decision && f.decision.S) || 0 })) }];
    chart($("chart-s"), s, "S");
  }

  /* ---- detalle */

  function renderDetail() {
    const f = state.frames[state.idx];
    const el = $("detail");
    el.innerHTML = "";
    if (!f) return;
    const d = f.decision || {};
    const head = document.createElement("div");
    const tag = document.createElement("span");
    tag.className = `action ${actionClass(d.action)}`;
    tag.textContent = d.action || "sin decisión";
    head.appendChild(tag);
    head.appendChild(document.createTextNode(`t=${f.t} · ${f.call.tool}`));
    el.appendChild(head);

    const dl = document.createElement("dl");
    const add = (k, v) => {
      const dt = document.createElement("dt"); dt.textContent = k;
      const dd = document.createElement("dd"); dd.textContent = v;
      dl.append(dt, dd);
    };
    add("razón", d.reason || "—");
    add("camino", (d.path && d.path.length) ? d.path.join(" → ") : "—");
    if (f.rotations.length) add("rotación", f.rotations.map((r) => `${lbl(r.secret_id)} → v${r.version}`).join(", "));
    el.appendChild(dl);
  }

  function render() {
    const n = state.frames.length;
    $("position").textContent = n ? `${state.idx + 1} / ${n}` : "—";
    updateList();
    renderCharts();
    renderDetail();
  }

  /* ---- controles */

  function step(delta) {
    if (!state.frames.length) return;
    state.idx = Math.max(0, Math.min(state.frames.length - 1, state.idx + delta));
    render();
  }

  function tick() {
    if (state.idx >= state.frames.length - 1) return stop();
    step(1);
    state.timer = setTimeout(tick, BASE_MS / state.speed);
  }

  function play() {
    if (state.timer || !state.frames.length) return;
    if (state.idx >= state.frames.length - 1) state.idx = -1;
    $("btn-play").classList.add("active");
    tick();
  }

  function stop() {
    clearTimeout(state.timer);
    state.timer = null;
    $("btn-play").classList.remove("active");
  }

  $("btn-play").addEventListener("click", play);
  $("btn-pause").addEventListener("click", stop);
  $("btn-fwd").addEventListener("click", () => { stop(); step(1); });
  $("btn-back").addEventListener("click", () => { stop(); step(-1); });
  $("btn-start").addEventListener("click", () => { stop(); state.idx = state.frames.length ? 0 : -1; render(); });
  document.querySelectorAll("[data-speed]").forEach((b) =>
    b.addEventListener("click", () => {
      state.speed = Number(b.dataset.speed);
      document.querySelectorAll("[data-speed]").forEach((o) => o.classList.toggle("active", o === b));
    }));
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT") return;
    if (e.key === " ") { e.preventDefault(); state.timer ? stop() : play(); }
    if (e.key === "ArrowRight") { stop(); step(1); }
    if (e.key === "ArrowLeft") { stop(); step(-1); }
  });
  $("file").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    file.text().then(load).catch((err) => showError(`No se pudo leer el archivo: ${err.message}`));
  });
  window.addEventListener("resize", () => renderCharts());

  const params = new URLSearchParams(location.search);
  // Sin ?log=, el registro real del panel derecho (para el sitio estático).
  const DEFAULT_LOG = "fixtures/real_right.jsonl";
  const log = params.get("log") || DEFAULT_LOG;
  if (log) loadUrl(log);
  if (typeof scenarioReady !== "undefined") scenarioReady.then(() => { if (state.frames.length) render(); });
  if (params.get("t")) {
    // ?t=N salta a la llamada N una vez cargado (útil para capturas).
    const target = Number(params.get("t"));
    const wait = setInterval(() => {
      if (!state.frames.length) return;
      clearInterval(wait);
      const i = state.frames.findIndex((f) => f.t >= target);
      state.idx = i < 0 ? state.frames.length - 1 : i;
      render();
    }, 50);
  }
}
