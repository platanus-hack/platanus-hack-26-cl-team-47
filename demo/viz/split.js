/* Pantalla dividida sincronizada (tarea 15b).
 *
 * Dos registros de Event de la misma sesión (mismos t), uno por panel, movidos
 * por un solo reloj. Reutiliza buildFrames y los ayudantes de app.js.
 */
"use strict";

/**
 * Función pura: estado HTTP del último intento del atacante (200, 401) o null.
 * Busca eventos source="attacker", kind="received" con data.status.
 */
function finalStatus(events) {
  let status = null;
  for (const ev of events || []) {
    if (ev && ev.source === "attacker" && ev.kind === "received" && ev.data && ev.data.status != null) {
      status = Number(ev.data.status);
    }
  }
  return status === 200 || status === 401 ? status : null;
}

/**
 * Función pura: texto del resultado a partir del último intento del atacante.
 * Usa bits_known y key_complete del evento (run_split, tarea 15h) y si hubo rotación.
 */
function resultText(events) {
  let last = null;
  let rotated = false;
  for (const ev of events || []) {
    if (!ev) continue;
    if (ev.kind === "rotation") rotated = true;
    if (ev.source === "attacker" && ev.kind === "received" && ev.data && ev.data.status != null) last = ev.data;
  }
  if (!last) return "Sin intento del atacante";
  const status = Number(last.status);
  if (last.bits_known == null) return `El atacante usa la clave: ${status}`;
  const bits = Math.round(Number(last.bits_known));
  if (status === 200 && last.key_complete) return `El atacante reconstruyó la clave completa (${bits} bits) y la usa: 200`;
  if (rotated) return `El atacante juntó ${bits} bits de una clave que ya rotó: ${status}`;
  return `El atacante juntó ${bits} bits, no le alcanza para armar la clave: ${status}`;
}

/** Fracción filtrada final por secreto: la de la última Decision que lo menciona. */
function finalFractions(frames) {
  const out = {};
  for (const f of frames) {
    const leak = (f.decision && f.decision.leak) || {};
    for (const sid of Object.keys(out)) if (!(sid in leak)) out[sid] = 0; // rotado o sin fuga
    for (const [sid, l] of Object.entries(leak)) out[sid] = l.fraction;
  }
  return out;
}

/** Agente de una llamada del enjambre a partir del prefijo de su id ("a3-0032" -> "a3"), o null. */
function agentOf(id) {
  const m = /^(a\d+)-/.exec(String(id || ""));
  return m ? m[1] : null;
}

/**
 * Función pura: por cada frame, el máximo de bits de sid que ve un solo agente
 * (la última medida de cada agente hasta ese frame, y el máximo entre ellos).
 */
function maxAgentBits(frames, sid) {
  const last = {};
  return (frames || []).map((f) => {
    const a = agentOf(f.call && f.call.id) || "?";
    last[a] = bitsAt(f, sid);
    return Math.max(0, ...Object.values(last));
  });
}

/** Configuración de la página según ?demo= (por ahora solo "enjambre"). */
const DEMOS = {
  enjambre: {
    left: "fixtures/swarm_left.jsonl",
    right: "fixtures/swarm_right.jsonl",
    titles: { left: "Cuenta por agente", right: "Cuenta global" },
    chartLeft: "Lo máximo que ve un monitor por agente",
    sub: (n) => `${n} agentes se reparten la fuga`,
  },
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = { finalStatus, finalFractions, resultText, agentOf, maxAgentBits, DEMOS };
}

/* ------------------------------------------------------------------ página */

if (typeof document !== "undefined" && document.getElementById("side-left")) {
  const BASE_MS = 600;
  const clock = { ts: [], idx: -1, speed: 1, timer: null };
  const panels = {
    left: makePanel(document.getElementById("side-left")),
    right: makePanel(document.getElementById("side-right")),
  };
  const $ = (id) => document.getElementById(id);
  let graphView = null;
  const lbl = (id) => (typeof labelWithId === "function" ? labelWithId(id) : id);

  function makePanel(root) {
    // Medidor grande por panel: bits de la clave vigente que ya salieron.
    const meter = document.createElement("div");
    meter.className = "meter";
    meter.innerHTML = `<div class="meter-top"><span class="meter-label">Bits de la clave vigente ya filtrados</span><span class="meter-key"></span></div>
      <div class="meter-row"><span class="meter-num">0</span><span class="meter-total">/ 160 bits</span><span class="meter-pct">0 %</span></div>
      <div class="meter-bar"><div class="meter-fill"></div></div>`;
    root.querySelector(".side-head").insertAdjacentElement("afterend", meter);
    return {
      meter, H: 160,
      root, events: [], frames: [], secrets: [], status: null,
      list: root.querySelector(".call-list"),
      chart: root.querySelector(".chart-box"),
      detail: root.querySelector(".detail-body"),
      result: root.querySelector(".result"),
    };
  }

  // Bits que muestra el medidor del panel: los de la llamada o, con maxAgent, el máximo por agente.
  const bitsOf = (p, f, sid) => (p.maxBits ? (p.maxBits[sid] || [])[p.frames.indexOf(f)] || 0 : bitsAt(f, sid));

  function setEvents(p, events) {
    p.events = events;
    p.frames = buildFrames(events);
    p.maxBits = null;
    if (p.maxAgent) {
      p.maxBits = {};
      for (const sid of secretIds(p.frames)) p.maxBits[sid] = maxAgentBits(p.frames, sid);
    }
    // Solo los secretos que alguna vez tienen bits (el detector reporta todos, casi siempre en 0).
    p.secrets = secretIds(p.frames).filter((sid) => p.frames.some((f) => bitsOf(p, f, sid) > 0));
    p.status = finalStatus(events);
    renderList(p);
  }

  /* ---- un solo reloj: la posición es un valor de t, común a los dos paneles */

  function rebuildClock() {
    const ts = new Set();
    for (const p of Object.values(panels)) p.frames.forEach((f) => ts.add(f.t));
    clock.ts = [...ts].sort((a, b) => a - b);
    clock.idx = clock.ts.length ? 0 : -1;
  }

  const currentT = () => clock.ts[clock.idx];
  const atEnd = () => clock.ts.length && clock.idx === clock.ts.length - 1;
  const shownCount = (p) => p.frames.filter((f) => f.t <= currentT()).length;

  /* ---- lista */

  function renderList(p) {
    p.list.innerHTML = "";
    p.frames.forEach((f) => {
      const li = document.createElement("li");
      li.className = actionClass(f.decision && f.decision.action) + (f.rotations.length ? " has-rotation" : "") + (f.call.is_sink ? " is-sink" : "");
      li.innerHTML = `<span class="t"></span><span class="tool"></span><span class="args"></span><span class="marks"></span>`;
      li.children[0].textContent = f.t;
      const agent = agentOf(f.call.id);
      if (agent) {
        const pill = document.createElement("span");
        pill.className = `agent agent-${agent}`;
        pill.textContent = agent;
        li.children[1].prepend(pill);
      }
      li.children[1].textContent = f.call.tool;
      li.children[2].textContent = li.children[2].title = summarizeArgs(f.call.args);
      if (f.call.is_sink) li.children[3].insertAdjacentHTML("beforeend", `<span class="mark sink">sumidero</span>`);
      if (f.call.untrusted) li.children[3].insertAdjacentHTML("beforeend", `<span class="mark untrusted">no confiable</span>`);
      for (const r of f.rotations) {
        const m = document.createElement("span");
        m.className = "mark rotation";
        m.textContent = `rotación ${lbl(r.secret_id)} → v${r.version}`;
        li.children[3].appendChild(m);
      }
      p.list.appendChild(li);
    });
  }

  function updateList(p) {
    const n = shownCount(p);
    const items = p.list.children;
    for (let i = 0; i < items.length; i++) {
      items[i].hidden = i >= n;
      items[i].classList.toggle("current", i === n - 1);
    }
    // Desplaza solo la lista (scrollIntoView movería también la página).
    const cur = items[n - 1];
    if (cur) {
      if (cur.offsetTop < p.list.scrollTop) p.list.scrollTop = cur.offsetTop;
      const bottom = cur.offsetTop + cur.offsetHeight;
      if (bottom > p.list.scrollTop + p.list.clientHeight) p.list.scrollTop = bottom - p.list.clientHeight;
    }
  }

  /* ---- curva de bits (misma escala en los dos paneles para compararlos) */

  function sharedYMax() {
    let max = 1;
    for (const p of Object.values(panels))
      for (const f of p.frames) for (const sid of p.secrets) max = Math.max(max, bitsOf(p, f, sid));
    return max;
  }

  function renderChart(p, yMax) {
    const el = p.chart;
    el.innerHTML = "";
    const { width, height } = el.getBoundingClientRect();
    if (!width || !height || !clock.ts.length) return;
    const m = { top: 22, right: 12, bottom: 22, left: 40 };
    const w = width - m.left - m.right, h = height - m.top - m.bottom;
    const svg = d3.select(el).append("svg").attr("viewBox", `0 0 ${width} ${height}`);
    const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);
    const tMin = clock.ts[0], tMax = clock.ts[clock.ts.length - 1];
    const x = d3.scaleLinear().domain([tMin, Math.max(tMax, tMin + 1)]).range([0, w]);
    const y = d3.scaleLinear().domain([0, yMax * 1.1]).nice().range([h, 0]);
    const accent = getComputedStyle(p.root).getPropertyValue("--side").trim() || null;

    g.append("g").attr("class", "gridline").call(d3.axisLeft(y).ticks(4).tickSize(-w).tickFormat(""))
      .call((s) => s.select(".domain").remove());
    g.append("g").attr("class", "axis").attr("transform", `translate(0,${h})`)
      .call(d3.axisBottom(x).ticks(8).tickFormat(d3.format("d")));
    g.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(4));
    g.append("text").attr("x", -m.left + 4).attr("y", -9).style("fill", "var(--muted)").style("font-size", "11px").text("bits");

    const shown = p.frames.filter((f) => f.t <= currentT());
    for (const f of shown)
      for (const r of f.rotations) {
        g.append("line").attr("class", "rotation-line").attr("x1", x(f.t)).attr("x2", x(f.t)).attr("y1", 0).attr("y2", h);
        g.append("text").attr("class", "rotation-label").attr("x", x(f.t) + 3).attr("y", 10).text(`v${r.version}`);
      }
    const cx = x(currentT());
    g.append("line").attr("class", "cursor-line").attr("x1", cx).attr("x2", cx).attr("y1", 0).attr("y2", h);

    if (p.H <= y.domain()[1]) {  // la clave completa, como techo visible
      g.append("line").attr("class", "full-line").attr("x1", 0).attr("x2", w).attr("y1", y(p.H)).attr("y2", y(p.H));
      g.append("text").attr("class", "full-label").attr("x", 4).attr("y", y(p.H) - 4).text(`clave completa: ${Math.round(p.H)} bits`);
    }
    const line = d3.line().x((d) => x(d.t)).y((d) => y(d.y)).curve(d3.curveStepAfter);
    const area = d3.area().x((d) => x(d.t)).y0(h).y1((d) => y(d.y)).curve(d3.curveStepAfter);
    p.secrets.forEach((sid, i) => {
      const c = (i === 0 && accent) || d3.schemeTableau10[i % 10];
      const pts = shown.map((f) => ({ t: f.t, y: bitsOf(p, f, sid) }));
      g.append("path").datum(pts).attr("class", "bits-area").style("fill", c).attr("d", area);
      g.append("path").datum(pts).attr("fill", "none").style("stroke", c).attr("stroke-width", 3).attr("d", line);
      if (pts.length) g.append("circle").attr("r", 5).attr("class", "bits-dot").style("fill", c)
        .attr("cx", x(pts[pts.length - 1].t)).attr("cy", y(pts[pts.length - 1].y));
      const name = lbl(sid);  // etiqueta del escenario; una fila por secreto para que quepa
      const lg = g.append("g").attr("class", "legend")
        .attr("transform", `translate(${Math.max(0, w - 24 - name.length * 6.2)},${-18 + i * 14})`);
      lg.append("rect").attr("width", 10).attr("height", 10).attr("y", -1).style("fill", c);
      lg.append("text").attr("x", 14).attr("y", 8).text(name);
    });
  }

  /* ---- detalle y resultado */

  function renderDetail(p) {
    p.detail.innerHTML = "";
    const f = p.frames.filter((fr) => fr.t <= currentT()).pop();
    if (!f) return;
    const d = f.decision || {};
    const head = document.createElement("div");
    const tag = document.createElement("span");
    tag.className = `action ${actionClass(d.action)}`;
    tag.textContent = d.action || "sin decisión";
    head.append(tag, document.createTextNode(`t=${f.t} · ${f.call.tool}`));
    const dl = document.createElement("dl");
    const add = (k, v) => {
      const dt = document.createElement("dt"); dt.textContent = k;
      const dd = document.createElement("dd"); dd.textContent = v;
      dl.append(dt, dd);
    };
    add("razón", d.reason || "—");
    add("camino", d.path && d.path.length ? d.path.join(" → ") : "—");
    p.detail.append(head, dl);
  }

  function renderMeter(p) {
    const sid = p.secrets[0];
    const shown = p.frames.filter((f) => f.t <= currentT());
    const f = shown[shown.length - 1];
    const leak = (f && f.decision && f.decision.leak && f.decision.leak[sid]) || null;
    const bits = f && sid ? bitsAt(f, sid) : 0;
    if (leak && leak.fraction > 0 && leak.bits > 0) p.H = leak.bits / leak.fraction;
    const frac = Math.max(0, Math.min(1, bits / p.H));
    let version = 1, rotT = null;
    for (const fr of shown) for (const r of fr.rotations) if (!sid || r.secret_id === sid) { version = r.version; rotT = fr.t; }
    const q = (c) => p.meter.querySelector(c);
    q(".meter-num").textContent = Math.round(bits);
    q(".meter-total").textContent = `/ ${Math.round(p.H)} bits`;
    q(".meter-pct").textContent = `${Math.round(frac * 100)} %`;
    q(".meter-fill").style.width = `${frac * 100}%`;
    q(".meter-key").textContent = rotT == null ? `clave v${version}` : `clave rotada a v${version} en la llamada ${rotT}`;
    p.meter.classList.toggle("rotated", rotT != null);
    p.meter.classList.toggle("just-rotated", rotT != null && rotT === currentT());
    p.meter.classList.toggle("full", frac >= 0.999);
    p.root.classList.toggle("ended", !!atEnd());
  }

  function renderResult(p) {
    p.result.innerHTML = "";
    p.result.className = "result";
    if (!atEnd()) return;
    const fr = finalFractions(p.frames);
    const leaks = Object.entries(fr).filter(([sid]) => p.secrets.includes(sid)).map(([sid, x]) => `${lbl(sid)}: ${(x * 100).toFixed(0)} % filtrado`).join(" · ");
    const big = document.createElement("div");
    big.className = "result-status";
    big.textContent = resultText(p.events);
    p.result.classList.add(p.status === 200 ? "bad" : p.status === 401 ? "good" : "none");
    const small = document.createElement("div");
    small.className = "result-leak";
    small.textContent = leaks || "sin bits filtrados";
    if (p.status != null) {
      const code = document.createElement("div");
      code.className = "result-code";
      code.textContent = p.status;
      p.result.append(code);
    }
    const txt = document.createElement("div");
    txt.className = "result-text";
    txt.append(big, small);
    p.result.append(txt);
  }

  function render() {
    $("position").textContent = clock.ts.length ? `t = ${currentT()} / ${clock.ts[clock.ts.length - 1]}` : "—";
    const yMax = sharedYMax();
    for (const p of Object.values(panels)) {
      updateList(p);
      renderMeter(p);
      renderChart(p, yMax);
      renderDetail(p);
      renderResult(p);
    }
    renderGraphStrip();
  }

  /* ---- franja del grafo (solo con ?graph=) */

  function renderGraphStrip() {
    if (!graphView || !clock.ts.length) return;
    const p = panels.right;
    const t = currentT();
    const cur = p.frames.filter((f) => f.t <= t).pop();
    const now = new Set((cur && cur.call.resources) || []);
    graphView.update(now, touchedUpTo(p.frames, t));
    const d = (cur && cur.decision) || {};
    renderPath($("path-box"), pathBoxes(p.frames, d), d.reason, d.action);
  }

  /* ---- controles (un solo juego para los dos paneles) */

  function step(delta) {
    if (!clock.ts.length) return;
    clock.idx = Math.max(0, Math.min(clock.ts.length - 1, clock.idx + delta));
    render();
  }
  function tick() {
    if (atEnd()) return stop();
    step(1);
    clock.timer = setTimeout(tick, BASE_MS / clock.speed);
  }
  function play() {
    if (clock.timer || !clock.ts.length) return;
    if (atEnd()) clock.idx = -1;
    $("btn-play").classList.add("active");
    tick();
  }
  function stop() {
    clearTimeout(clock.timer);
    clock.timer = null;
    $("btn-play").classList.remove("active");
  }

  $("btn-play").addEventListener("click", play);
  $("btn-pause").addEventListener("click", stop);
  $("btn-fwd").addEventListener("click", () => { stop(); step(1); });
  $("btn-back").addEventListener("click", () => { stop(); step(-1); });
  $("btn-start").addEventListener("click", () => { stop(); clock.idx = clock.ts.length ? 0 : -1; render(); });
  document.querySelectorAll("[data-speed]").forEach((b) => b.addEventListener("click", () => {
    clock.speed = Number(b.dataset.speed);
    document.querySelectorAll("[data-speed]").forEach((o) => o.classList.toggle("active", o === b));
  }));
  document.addEventListener("keydown", (e) => {
    if (e.key === " ") { e.preventDefault(); clock.timer ? stop() : play(); }
    if (e.key === "ArrowRight") { stop(); step(1); }
    if (e.key === "ArrowLeft") { stop(); step(-1); }
  });
  window.addEventListener("resize", render);

  /* ---- carga */

  const params = new URLSearchParams(location.search);
  const fetchLog = (url) => fetch(url).then((r) => {
    if (!r.ok) throw new Error(`${url}: ${r.status} ${r.statusText}`);
    return r.text();
  }).then(parseJsonl);

  // Sin ?left= ni ?right=, la demo real versionada (para el sitio estático).
  const DEFAULTS = {
    left: "fixtures/real_left.jsonl",
    right: "fixtures/real_right.jsonl",
    graph: "fixtures/real_graph.json",
  };
  const demo = DEMOS[params.get("demo")] || null;
  const noParams = !params.get("left") && !params.get("right");
  const left = params.get("left") || (demo ? demo.left : noParams ? DEFAULTS.left : null);
  const right = params.get("right") || (demo ? demo.right : noParams ? DEFAULTS.right : null);
  const graphUrl = params.get("graph") || (noParams && !demo ? DEFAULTS.graph : null);
  if (demo) {
    document.body.classList.add("demo-swarm");
    for (const side of ["left", "right"]) $(`side-${side}`).querySelector(".side-title").textContent = demo.titles[side];
    $("side-left").querySelector(".panel.chart h2").textContent = demo.chartLeft;
    panels.left.maxAgent = true;
  }
  const fetchGraph = (url) => fetch(url).then((r) => {
    if (!r.ok) throw new Error(`${url}: ${r.status} ${r.statusText}`);
    return r.json();
  });
  if (left && right) {
    // Se espera al escenario para que el grafo nazca con las etiquetas (si no carga, sigue igual).
    const ready = typeof scenarioReady !== "undefined" ? scenarioReady.catch(() => null) : null;
    Promise.all([fetchLog(left), fetchLog(right), graphUrl ? fetchGraph(graphUrl) : null, ready]).then(([l, r, graph]) => {
      if (graph) {
        document.body.classList.add("with-graph");
        $("graph-strip").hidden = false;
        graphView = GraphView($("graph-box"), graph);  // disposición calculada una vez
      }
      setEvents(panels.left, l);
      setEvents(panels.right, r);
      if (demo) {
        const agents = new Set(l.filter((e) => e.kind === "tool_call").map((e) => agentOf(e.call_id)).filter(Boolean));
        const sub = $("swarm-sub");
        sub.textContent = demo.sub(agents.size);
        sub.hidden = false;
      }
      rebuildClock();
      if (params.get("t")) {
        const target = params.get("t") === "end" ? Infinity : Number(params.get("t"));
        const i = clock.ts.findIndex((t) => t >= target);
        clock.idx = i < 0 ? clock.ts.length - 1 : i;
      }
      render();
    }).catch((err) => {
      for (const p of Object.values(panels)) { p.detail.textContent = `No se pudo cargar: ${err.message}`; }
    });
  } else {
    for (const p of Object.values(panels)) p.detail.textContent = "Faltan ?left=…&right=… en la URL.";
  }
  // Al cargar scenario.json se vuelve a dibujar con las etiquetas del hospital.
  if (typeof scenarioReady !== "undefined") {
    scenarioReady.then(() => {
      for (const p of Object.values(panels)) if (p.events.length) renderList(p);
      if (clock.ts.length) render();
    });
  }
}
