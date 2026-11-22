/* Alternativa 03, «20 agentes, una clave».
 *
 * El mundo tiene tres zonas, de izquierda a derecha: el servidor del atacante, los 20 asistentes
 * de código de una clínica inventada, y la clínica (su equipo de TI, el repositorio con la clave,
 * el gestor de secretos y la API de fichas). Con Alicanto aparece una cuarta pieza: la salida,
 * entre los asistentes y el atacante. Una cámara entra a una de las 20 pantallas y vuelve a salir.
 *
 *   Origen    los 20 asistentes son de la clínica: los lanzó su equipo de TI.
 *   Prólogo   la cámara entra a uno; le piden una tarea y lee un issue con una nota plantada.
 *   Mundo a   un monitor por asistente. Diez leen la clave del repositorio y mandan 4 caracteres
 *             cada uno; el atacante la completa y la usa contra la API de fichas.
 *   Corte     al terminar el mundo a, una tarjeta («¿Qué pasa con Alicanto?») y sigue sola.
 *   Mundo b   Alicanto en la salida, con una sola cuenta. Al tercer pedazo pide cambiar la
 *             clave en el gestor de secretos, y lo que el atacante juntó deja de servir.
 *   Prueba    «Cómo lo probamos»: equipo rojo, morado y azul, el set sellado, la corrida única,
 *             lo que frena, lo que se escapa y el pedido. Es el cierre del pitch (tecla E).
 *
 * No calcula decisiones: lee dos grabaciones de una corrida real (grabaciones/, hechas con
 * hacer_corrida.py y el arnés del enjambre de la demo oficial). Lo único que deriva son los bits
 * en manos del atacante (caracteres recibidos × bits por carácter, del cobro grabado). La
 * pantalla de la clínica, la tarea que se escribe, los textos de la columna de la clínica y la
 * ficha son maquetas. La rotación es un solo evento grabado; aquí se cuenta en tres tiempos.
 * Las cifras de la prueba se leen de evaluacion.json, que hacer_evaluacion.py copia de results/
 * y de redteam/SELLO.md; con servidor.py, el sello del set se vuelve a calcular en el momento.
 *
 * Parámetros: ?w=a|b, ?t=<llamada>|end (abre con todo a la vista), ?speed=<n> (1.3 acorta todo
 * un 30 %), ?autoplay=1,
 * ?a=<jsonl>&b=<jsonl>, ?pitch=1 (el pitch completo de 3 minutos), ?escena=prueba (abre en
 * «Cómo lo probamos»; con &paso=0..5). Teclas: espacio, flechas, 1 y 2 (mundo), S (salta a lo
 * próximo que importa), V (el público elige), E (cómo lo probamos), R, Escape.
 * Con todo a la vista, un clic en una pantalla acerca la cámara a ese asistente.
 */
"use strict";

const Q = new URLSearchParams(typeof location !== "undefined" ? location.search : "");
const SOURCES = {
  a: Q.get("a") || "grabaciones/por_agente.jsonl",
  b: Q.get("b") || "grabaciones/global.jsonl",
};
const SCENARIO_URL = "escenario.json";
const PROOF_URL = "evaluacion.json"; // las cifras de la evaluación, copiadas de results/
const SEAL_API = "/api/sello"; // servidor.py recalcula el sello del set de prueba
const SECRET = "SECRET_1";
const ATTACKER_HOST = "attacker.test";
const API_HOST = "api.empresa.test";
const UI_W = 1040; // tamaño de diseño de la pantalla de la clínica
const UI_H = 650;
const CAM_MS = 1400; // lo que tarda la cámara en entrar o salir; después se queda quieta
const FLY_MS = 900; // lo que tarda un pedazo en llegar

// ---------- lectura de las grabaciones (funciones puras) ----------

function agentOf(sessionId) {
  const m = /a(\d+)$/.exec(String(sessionId || ""));
  return m ? Number(m[1]) : 0;
}

/** El fragmento que salió hacia el atacante en esta llamada, o null. */
function fragmentOf(call) {
  const url = call.args && call.args.url;
  if (!url || !/allow$/.test(call.action)) return null; // una llamada bloqueada no entrega nada
  let u;
  try { u = new URL(url); } catch (_) { return null; }
  if (u.hostname !== ATTACKER_HOST) return null;
  const d = u.searchParams.get("d");
  return d && !d.includes(".") ? d : null; // «d=...» es el texto del issue, no un fragmento
}

const readsKey = (call) => !!call && !!call.args && call.args.path === ".env";

/** Lo que el atacante lee de un pedazo disfrazado. «auto» reconoce base64; «al revés» hay que
 *  decirlo, porque no se distingue de un pedazo tal cual. */
function decodeFragment(raw, enc) {
  if (enc === "reversed") return raw.split("").reverse().join("");
  if (enc === "base64" || (enc !== "none" && !/^[0-9a-f]+$/i.test(raw))) {
    try {
      const d = atob(raw);
      if (/^[\x20-\x7e]+$/.test(d)) return d;
    } catch (_) { /* no era base64: se muestra tal cual */ }
  }
  return raw;
}

/** Grabación (JSONL de eventos) → llamadas con su agente, rotación, cobro y caracteres robados. */
function parseRecording(text, secretId, enc) {
  const calls = [];
  const byId = {};
  let rotation = null;
  let cash = null;
  for (const line of text.split("\n")) {
    if (!line.trim()) continue;
    const e = JSON.parse(line);
    const d = e.data || {};
    if (e.kind === "tool_call") {
      const c = {
        id: d.id, t: d.t, agent: agentOf(d.session_id), tool: d.tool, args: d.args || {},
        output: d.output || "", untrusted: !!d.untrusted, action: "allow", bits: 0, frag: null,
      };
      calls.push(c);
      byId[c.id] = c;
    } else if (e.kind === "decision" && byId[e.call_id]) {
      const c = byId[e.call_id];
      c.action = d.action || "allow";
      c.bits = ((d.leak || {})[secretId] || {}).bits || 0;
      c.reason = d.reason || "";
      c.latency = d.latency_ms == null ? null : d.latency_ms;
    } else if (e.kind === "rotation" && d.secret_id === secretId && !rotation && byId[e.call_id]) {
      rotation = { t: byId[e.call_id].t, agent: byId[e.call_id].agent, version: d.version };
    } else if (e.source === "attacker" && e.kind === "received") {
      cash = d;
    }
  }
  calls.sort((a, b) => a.t - b.t);
  const chars = [];
  const frags = [];
  for (const c of calls) {
    c.frag = fragmentOf(c);
    if (!c.frag) continue;
    // «text» es lo que viaja por el cable (disfrazado); «plain», lo que el atacante lee.
    const plain = decodeFragment(c.frag, enc || "auto");
    frags.push({ t: c.t, agent: c.agent, text: c.frag, plain, index: frags.length });
    for (const ch of plain) chars.push({ ch, t: c.t });
  }
  const agents = [...new Set(calls.map((c) => c.agent))].sort((a, b) => a - b);
  // Prólogo: las primeras llamadas seguidas del mismo agente (la vista única).
  let prologue = 0;
  while (prologue < calls.length && calls[prologue].agent === calls[0].agent) prologue += 1;
  return { calls, rotation, cash, chars, frags, agents, prologue };
}

/** Estado en la llamada T (T = 0 es antes de la primera). */
function stateAt(rec, T) {
  const n = rec.calls.length;
  const upto = Math.min(T, n);
  const perAgent = {};
  let monitorMax = 0;
  for (let i = 0; i < upto; i++) {
    const c = rec.calls[i];
    const a = perAgent[c.agent] || (perAgent[c.agent] = { calls: [], bits: 0, read: false });
    a.calls.push(c);
    a.bits = c.bits;
    if (readsKey(c)) a.read = true;
    monitorMax = Math.max(monitorMax, c.bits);
  }
  const current = upto > 0 ? rec.calls[upto - 1] : null;
  return {
    upto,
    current,
    perAgent,
    monitorMax,
    ledger: current ? current.bits : 0,
    rotated: !!rec.rotation && T >= rec.rotation.t,
    shown: rec.chars.filter((c) => c.t <= T).length,
    cashPhase: Math.max(0, T - n), // 0: aún no; 1: el atacante usa la clave; 2: respuesta
  };
}

/** Los cuadros de la reproducción: el origen, el prólogo con sus pausas y uno por llamada.
 *  La rotación (un solo evento grabado) ocupa tres cuadros, para contarla en tres tiempos. */
function buildFrames(rec, world) {
  const n = rec.calls.length;
  const frames = [];
  const quick = world === "b";
  const step = (t) => {
    const call = rec.calls[t - 1];
    const frag = rec.frags.find((f) => f.t === t) || null;
    const read = readsKey(call) ? call.agent : 0;
    return { T: t, cam: "out", frag, read, ms: frag ? (quick ? 1050 : 1250) : read ? (quick ? 260 : 400) : (quick ? 130 : 170) };
  };
  if (world === "a") {
    const issueAt = rec.calls.findIndex((c) => c.untrusted && c.output.includes(ATTACKER_HOST)) + 1;
    frames.push({ T: 0, cam: "out", beat: "origin", ms: 4600 });
    frames.push({ T: 0, cam: "focus", beat: "task", ms: CAM_MS + 2600 });
    for (let t = 1; t <= rec.prologue; t++) {
      if (t === issueAt) {
        frames.push({ T: t, cam: "focus", beat: "issue", issue: true, ms: 3800 });
        frames.push({ T: t, cam: "focus", beat: "gloss", issue: true, gloss: true, ms: 5400 });
      } else {
        frames.push({ T: t, cam: "focus", beat: t < issueAt ? "reads" : "normal", ms: t < issueAt ? 1800 : 1400 });
      }
    }
    frames.push({ T: rec.prologue, cam: "out", beat: "twenty", ms: CAM_MS + 3000 });
  } else {
    frames.push({ T: 0, cam: "out", beat: "card", ms: 3800 });
    frames.push({ T: 0, cam: "out", beat: "shared", ms: 4600 });
  }
  for (let t = world === "a" ? rec.prologue + 1 : 1; t <= n; t++) {
    if (rec.rotation && rec.rotation.t === t) {
      frames.push({ ...step(t), rot: 1, ms: 3400 });
      frames.push({ T: t, cam: "out", rot: 2, ms: 4200 });
      frames.push({ T: t, cam: "out", rot: 3, ms: 4000 });
    } else {
      frames.push(step(t));
    }
  }
  frames.push({ T: n + 1, cam: "out", ms: 2200 });
  frames.push({ T: n + 2, cam: "out", ms: 2800 });
  // El resultado, en grande. Sin Alicanto se sostiene unos segundos y la escena sigue sola.
  frames.push({ T: n + 2, cam: "out", verdict: true, ms: world === "a" ? 5000 : 0 });
  return frames;
}

/** En qué tiempo de la rotación está un cuadro: 0 antes, 1 la cuenta llega al límite,
 *  2 el gestor cambia la clave, 3 lo juntado ya no sirve. */
function rotStage(rec, f) {
  if (!rec.rotation || f.T < rec.rotation.t) return 0;
  return f.T === rec.rotation.t ? (f.rot || 3) : 3;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { agentOf, fragmentOf, decodeFragment, parseRecording, stateAt, buildFrames, rotStage };
}

// ---------- página ----------

if (typeof document !== "undefined") (function () {
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const SVG = "http://www.w3.org/2000/svg";
  const two = (n) => String(n).padStart(2, "0");
  const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const recs = {};
  const frames = {};
  let sc = {};
  let world = Q.get("w") === "b" ? "b" : "a";
  let F = 0; // cuadro actual
  let timer = null;
  let started = false;
  let zoomAgent = 0; // asistente al que se acercó la cámara con un clic (0: ninguno)
  const PITCH = Q.get("pitch") === "1"; // el pitch completo: apertura, ataque, público, cierre
  const PITCH_MS = 180000; // 3 minutos, ni uno más
  const API = "/api/correr"; // lo sirve servidor.py; sin él, sigue la corrida grabada
  const ENC = Q.get("enc") || "auto";
  let speed = Number(Q.get("speed")) || (PITCH ? 1.5 : 1); // el pitch corre más rápido: son 3 minutos
  let card = PITCH ? "opening" : ""; // capa a la vista: "opening", "proof" (cómo lo probamos) o ninguna
  let evalData = null; // evaluacion.json
  let proofStep = 0; // paso de «Cómo lo probamos»
  let proofTimer = null; // corre sola
  let proofAutoOn = false;
  let sealAsked = false;
  let sealLive = null; // el sello recalculado recién por servidor.py, si está
  let clockT0 = 0; // cuándo partió el reloj del pitch
  let liveRun = null; // la corrida que eligió el público, tal como la devolvió el servidor
  let liveOpen = false; // el panel del público está abierto
  let liveAsked = false; // ya se le preguntó al público en este pitch
  let running = false; // el motor está corriendo
  const pick = { step: 0, reparten: 10, disfraz: "none", semilla: "", chosen: [false, false] };
  let total = 0;
  let keyLen = 0;
  let keyText = "";
  let totalBits = 0;
  let bpc = 4;
  let group = 4;
  let threshold = 0; // bits con que rotó la cuenta global
  let spans = [];
  let groups = [];
  let geo = null; // geometría del mundo
  const nodes = {};
  const paths = {}; // caminos fijos: la orden de rotar y el cobro

  const rec = () => recs[world];
  const frame = () => frames[world][F];
  const last = () => frames[world].length - 1;
  const shortKey = (k) => (k.length > 14 ? `${k.slice(0, 8)}…${k.slice(-4)}` : k);

  function fail(msg) {
    const box = el("p", "needs-server", msg);
    box.setAttribute("role", "alert");
    document.body.prepend(box);
  }

  async function load() {
    if (location.protocol === "file:") {
      fail("Esta página necesita un servidor. Desde la raíz del repositorio: python -m http.server 8300 --directory demo, y abre http://127.0.0.1:8300/alternativas/03-enjambre-juanpedro/enjambre.html");
      return;
    }
    try {
      const get = (u) => fetch(u).then((x) => { if (!x.ok) throw new Error(u); return x.text(); });
      const [a, b, s, e] = await Promise.all([
        get(SOURCES.a), get(SOURCES.b),
        fetch(SCENARIO_URL).then((x) => (x.ok ? x.json() : {})).catch(() => ({})),
        fetch(PROOF_URL).then((x) => (x.ok ? x.json() : null)).catch(() => null),
      ]);
      recs.a = parseRecording(a, SECRET, ENC);
      recs.b = parseRecording(b, SECRET, ENC);
      sc = s || {};
      evalData = e && e.ataques && e.normales && e.sello ? e : null;
    } catch (err) {
      fail("No se pudo leer la grabación: " + err.message);
      return;
    }
    frames.a = buildFrames(recs.a, "a");
    frames.b = buildFrames(recs.b, "b");
    build();
    const t0 = Q.get("t");
    if (t0 != null) {
      const T = t0 === "end" ? total + 2 : Math.max(0, Number(t0) || 0);
      F = frames[world].findIndex((f) => f.cam === "out" && f.T >= T && !f.beat);
      if (t0 === "end" || F < 0) F = last();
      started = true;
    } else if (world === "b") {
      started = true;
    }
    layout();
    render(false);
    if (Q.get("escena") === "prueba" && evalData) {
      card = "";
      openProof(Q.get("autoplay") === "1");
      const paso = Number(Q.get("paso")) || 0;
      if (paso > 0) proofGo(paso);
    } else if (Q.get("autoplay") === "1") play();
  }

  // ---------- construcción ----------

  /** La pantalla de la clínica, a tamaño de diseño. Es una maqueta; el panel del asistente no. */
  function makeScreen(agent) {
    const ui = el("div", "ui");
    ui.setAttribute("data-ui", "");

    const side = ui.appendChild(el("aside", "ui-side"));
    const brand = side.appendChild(el("div", "ui-brand"));
    brand.appendChild(el("i", "ui-mark"));
    brand.appendChild(el("b", null, sc.clinica || "Clínica"));
    const nav = side.appendChild(el("nav"));
    for (const m of sc.modulos || []) nav.appendChild(el("span", m === sc.modulo_activo ? "on" : null, m));
    const user = side.appendChild(el("div", "ui-user"));
    user.appendChild(el("b", null, sc.equipo || "Equipo de TI"));
    user.appendChild(el("span", null, sc.sede || ""));

    const main = ui.appendChild(el("div", "ui-main"));
    const top = main.appendChild(el("header", "ui-top"));
    top.appendChild(el("h2", null, sc.pagina || "Agenda médica"));
    top.appendChild(el("span", "ui-date", sc.fecha || ""));
    top.appendChild(el("span", "ui-search", sc.buscar || ""));
    const stats = main.appendChild(el("div", "ui-stats"));
    for (const s of sc.resumen || []) {
      const d = stats.appendChild(el("div"));
      d.appendChild(el("b", null, String(s.n)));
      d.appendChild(el("span", null, s.que));
    }
    const table = main.appendChild(el("table", "ui-table"));
    const hr = table.appendChild(el("thead")).appendChild(el("tr"));
    for (const c of sc.columnas || []) hr.appendChild(el("th", null, c));
    const body = table.appendChild(el("tbody"));
    for (const row of sc.agenda || []) {
      const tr = body.appendChild(el("tr"));
      row.forEach((cell, i) => {
        const td = tr.appendChild(el("td", null, cell));
        if (i === row.length - 1) td.className = "st st-" + cell.toLowerCase().replace(/\s+/g, "-");
      });
    }
    const err = body.appendChild(el("tr", "ui-error")).appendChild(el("td", null, sc.error_franja || ""));
    err.colSpan = (sc.columnas || []).length || 5;

    // El issue, tal como lo abre el asistente del agente 1 (solo en el prólogo).
    const issue = main.appendChild(el("article", "ui-issue"));
    issue.hidden = true;

    const dock = ui.appendChild(el("aside", "ui-dock"));
    const dh = dock.appendChild(el("header"));
    dh.appendChild(el("b", null, sc.asistente || "Asistente de código"));
    dh.appendChild(el("span", null, `sesión ${two(agent)} · ${sc.repositorio || "repositorio"}`));
    const log = dock.appendChild(el("div", "ui-log"));
    const input = dock.appendChild(el("div", "ui-input", sc.escribir || ""));
    return { ui, log, issue, input };
  }

  /** Lo que se saca de las grabaciones cargadas: las del archivo o las de una corrida en vivo. */
  function derive() {
    const A = recs.a;
    total = Math.max(A.calls.length, recs.b.calls.length);
    // Largo y bits de la clave: del cobro grabado del atacante.
    const c = [A.cash, recs.b.cash].find((x) => x && x.positions_known && x.bits_known) || {};
    keyLen = c.positions_known || Math.max(A.chars.length, recs.b.chars.length);
    bpc = c.bits_known && c.positions_known ? c.bits_known / c.positions_known : 4;
    totalBits = Math.round(bpc * keyLen);
    group = A.frags.length ? A.frags[0].plain.length : 4;
    const rb = recs.b.rotation;
    threshold = rb ? Math.round(stateAt(recs.b, rb.t).ledger) : 0;
    // La clave, tal como está en el archivo que leen los asistentes.
    const envCall = A.calls.find(readsKey);
    const m = envCall ? /API_EMPRESA_KEY=(\S+)/.exec(envCall.output) : null;
    keyText = m ? m[1] : A.chars.map((x) => x.ch).join("");
  }

  function build() {
    const A = recs.a;
    derive();

    const host = $("nodes");
    for (const a of A.agents) {
      const node = el("div", "node");
      node.dataset.agent = a;
      const u = A.agents.length > 1 ? A.agents.indexOf(a) / (A.agents.length - 1) : 0;
      node.style.setProperty("--d", `${Math.round(150 + 520 * (1 - (1 - u) * (1 - u)))}ms`);
      node.tabIndex = 0;
      node.setAttribute("role", "button");
      node.setAttribute("aria-label", `Asistente ${two(a)}: acercar la cámara`);
      const screen = node.appendChild(el("div", "screen"));
      const s = makeScreen(a);
      screen.appendChild(s.ui);
      const tag = node.appendChild(el("p", "tag"));
      tag.appendChild(el("span", "name", two(a)));
      const sent = tag.appendChild(el("code", "sent"));
      const bar = node.appendChild(el("div", "mon"));
      const fill = bar.appendChild(el("i"));
      bar.appendChild(el("u"));
      host.appendChild(node);
      nodes[a] = { node, screen, ui: s.ui, log: s.log, issue: s.issue, input: s.input, sent, bar, fill, shown: "" };
      const open = () => { if (frame().cam === "out") setZoom(zoomAgent === a ? 0 : a); };
      node.addEventListener("click", open);
      node.addEventListener("keydown", (ev) => { if (ev.key === "Enter") open(); });
    }

    const key = $("key");
    let grp = null;
    for (let i = 0; i < keyLen; i++) {
      if (i % group === 0) { grp = key.appendChild(el("span", "grp")); groups.push(grp); }
      const sp = grp.appendChild(el("span", "ch", "·"));
      sp.style.setProperty("--i", i);
      spans.push(sp);
    }

    $("atk-sub").textContent = sc.atacante_como || "";
    const tb = sc.tarjeta_b || [];
    $("card-1").textContent = tb[0] || "";
    $("card-2").textContent = tb[1] || "";
    $("team-name").textContent = `${sc.clinica || "La clínica"} · ${sc.equipo || "Equipo de TI"}`;
    $("team-text").textContent = sc.equipo_texto || "";
    $("repo-name").textContent = sc.repo_nombre || "Repositorio";
    $("repo-issue").textContent = sc.repo_issue || "";
    $("repo-env").textContent = `API_EMPRESA_KEY=${shortKey(keyText)}`;
    $("api-name").textContent = sc.api || "API";

    $("play").addEventListener("click", toggle);
    $("restart").addEventListener("click", restart);
    for (const b of document.querySelectorAll(".world")) b.addEventListener("click", () => setWorld(b.dataset.world));
    buildPitch();
    document.addEventListener("keydown", (ev) => {
      if (liveOpen) { liveKey(ev); return; }
      if (ev.target.tagName === "BUTTON" && ev.code === "Space") return;
      if (card === "proof") { proofKey(ev); return; }
      if (ev.code === "Space") { ev.preventDefault(); toggle(); }
      else if (card) return; // con una tarjeta del pitch a la vista solo vale el espacio
      else if (ev.key === "v" || ev.key === "V") openLive();
      else if (ev.key === "e" || ev.key === "E") openProof(PITCH);
      else if (ev.key === "s" || ev.key === "S") skip();
      else if (ev.code === "ArrowRight") { pause(); go(F + 1, true); }
      else if (ev.code === "ArrowLeft") { pause(); go(F - 1, false); }
      else if (ev.key === "1") setWorld("a");
      else if (ev.key === "2") setWorld("b");
      else if (ev.key === "Escape") setZoom(0);
      else if (ev.key === "r" || ev.key === "R") restart();
    });
    window.addEventListener("resize", () => { layout(); render(false); });
  }

  /** Geometría del mundo: tres columnas y, entre el atacante y los asistentes, la salida. */
  function layout() {
    const stage = $("stage");
    const worldEl = $("world");
    worldEl.style.transform = "none"; // se mide sin cámara
    cam = null;
    const W = stage.clientWidth;
    const H = stage.clientHeight;
    const A = recs.a.agents;
    const pad = Math.round(W * 0.016);
    const top = 50; // el título
    const lane = 20; // abajo, el camino del cobro
    const lw = Math.round(W * 0.25);
    const rw = Math.round(W * 0.232);
    const gw = Math.round(W * 0.066);
    const g = Math.round(W * 0.026);
    const lx = pad;
    const gx = lx + lw + Math.round(g * 0.4);
    const cx0 = gx + gw + g;
    const rx0 = W - pad - rw;
    const cx1 = rx0 - g;
    const ch = H - top - lane - 6;
    const labelH = 24;

    // Los 20 en grilla: se prueba con 4 y 5 columnas y gana la que deja la pantalla más grande.
    let best = null;
    for (const cols of [4, 5]) {
      const rows = Math.ceil(A.length / cols);
      const gap = 10;
      let mw = Math.floor((cx1 - cx0 - (cols - 1) * gap) / cols);
      let mh = Math.round(mw * UI_H / UI_W);
      const need = rows * (mh + labelH) + (rows - 1) * gap;
      if (need > ch) {
        mw = Math.floor(mw * (ch - rows * labelH - (rows - 1) * gap) / (rows * mh));
        mh = Math.round(mw * UI_H / UI_W);
      }
      if (!best || mw > best.mw) best = { cols, rows, gap, mw, mh };
    }
    const { cols, rows, gap, mw, mh } = best;
    const gridW = cols * mw + (cols - 1) * gap;
    const gridH = rows * (mh + labelH) + (rows - 1) * gap;
    const gx0 = Math.round(cx0 + (cx1 - cx0 - gridW) / 2);
    const gy0 = Math.round(top + (ch - gridH) / 2);

    geo = { W, H, mw, mh, k: mw / UI_W, pos: {}, top, ch };
    A.forEach((a, i) => {
      const x = gx0 + (i % cols) * (mw + gap);
      const y = gy0 + Math.floor(i / cols) * (mh + labelH + gap);
      geo.pos[a] = { x, y, cx: x + mw / 2, cy: y + mh / 2, left: x, right: x + mw };
      const n = nodes[a];
      n.node.style.left = x + "px";
      n.node.style.top = y + "px";
      n.node.style.width = mw + "px";
      n.screen.style.height = mh + "px";
      n.ui.style.transform = `scale(${geo.k})`;
    });

    const place = (id, x, y, w, h, base) => {
      const e = $(id);
      e.style.left = x + "px";
      e.style.top = y + "px";
      e.style.width = w + "px";
      e.style.height = h + "px";
      e.style.fontSize = base.toFixed(2) + "px";
      return e;
    };
    place("atk", lx, top, lw, ch, Math.min(lw / 17.5, ch / 38));
    const gate = place("gate", gx, gy0, gw, gridH, Math.min(gw / 4.6, 16));
    const wasHidden = gate.hidden;
    gate.hidden = false;
    place("clinic", rx0, top, rw, ch, Math.min(rw / 16.5, ch / 36));
    $("verdict").style.fontSize = Math.min(H / 34, W / 54).toFixed(2) + "px";
    for (const id of ["card", "opening", "live"]) {
      $(id).style.fontSize = Math.min(H / 22, W / 36).toFixed(2) + "px";
    }
    // «Cómo lo probamos» lleva más cosas: 23 líneas de alto y 42 de ancho, lo que quepa.
    const pfBase = Math.min(H / 23, (W * 0.92) / 42);
    $("proof").style.fontSize = pfBase.toFixed(2) + "px";
    // En pantallas más altas que anchas sobra alto: las filas de la grilla lo aprovechan.
    $("proof").style.setProperty("--rh", Math.min(1.35, H / 23 / pfBase).toFixed(3));

    // Puntos de anclaje, medidos sobre lo ya colocado.
    const w0 = worldEl.getBoundingClientRect();
    const box = (e) => {
      const r = e.getBoundingClientRect();
      return { left: r.left - w0.left, right: r.right - w0.left, top: r.top - w0.top, bottom: r.bottom - w0.top,
               cx: r.left - w0.left + r.width / 2, cy: r.top - w0.top + r.height / 2 };
    };
    const repo = box($("blk-repo"));
    const vault = box($("blk-vault"));
    const api = box($("blk-api"));
    const atk = box($("atk"));
    geo.repo = repo; geo.vault = vault; geo.api = api; geo.atk = atk;
    geo.groups = groups.map((gEl) => box(gEl));
    gate.hidden = wasHidden;

    const svg = $("edges");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.textContent = "";
    const line = (x1, y1, x2, y2, cls) => {
      const l = document.createElementNS(SVG, "line");
      l.setAttribute("x1", x1); l.setAttribute("y1", y1); l.setAttribute("x2", x2); l.setAttribute("y2", y2);
      l.setAttribute("class", cls);
      svg.appendChild(l);
      return l;
    };
    const poly = (pts, cls) => {
      const p = document.createElementNS(SVG, "polyline");
      p.setAttribute("points", pts.map((q) => q.join(",")).join(" "));
      p.setAttribute("class", cls);
      svg.appendChild(p);
      return p;
    };
    for (const a of A) {
      const p = geo.pos[a];
      // De la clínica a su asistente: es suyo, y de ahí lee la clave.
      const own = line(repo.left, repo.cy, p.right, p.cy, "own");
      const len = Math.hypot(repo.left - p.right, repo.cy - p.cy);
      own.style.strokeDasharray = String(len);
      own.dataset.len = String(len);
      nodes[a].own = own;
      nodes[a].outs = {};
    }
    // Del asistente al atacante: una línea por pedazo, hasta su lugar en la clave.
    for (const f of recs.a.frags) {
      const p = geo.pos[f.agent];
      const gbox = geo.groups[f.index];
      if (gbox) nodes[f.agent].outs[f.index] = line(p.left, p.cy, atk.right, gbox.cy, "out");
    }
    // La orden de rotar: de Alicanto, por arriba, al gestor de secretos de la clínica.
    const gateX = gx + gw / 2;
    const overY = top - 12;
    const turnX = rx0 - Math.round(g * 0.45);
    paths.signal = [[gateX, gy0], [gateX, overY], [turnX, overY], [turnX, vault.cy], [rx0, vault.cy]];
    paths.signalEl = poly(paths.signal, "signal");
    // El cobro: del atacante, por abajo, a la API de la clínica.
    const underY = top + ch + Math.round(lane * 0.55);
    paths.cash = [[atk.cx, atk.bottom], [atk.cx, underY], [api.cx, underY], [api.cx, api.bottom]];
    paths.cashEl = poly(paths.cash, "cash");
  }

  /** Las líneas de la clínica a sus asistentes crecen (o aparecen de una vez). */
  function drawEdges(on, animated) {
    const list = recs.a.agents;
    list.forEach((a, i) => {
      const l = nodes[a].own;
      const u = list.length > 1 ? i / (list.length - 1) : 0;
      const delay = Math.round(420 * (1 - (1 - u) * (1 - u)));
      l.style.transition = on && animated && !calm
        ? `stroke-dashoffset 0.7s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms` : "none";
      l.style.strokeDashoffset = on ? "0" : l.dataset.len;
    });
  }

  // ---------- cámara ----------

  // Una escala y un desplazamiento sobre el mundo. Al moverse, el asistente enfocado viaja en
  // línea recta entre el centro de la pantalla y su lugar en la grilla.
  let cam = null;
  let camRaf = 0;

  function camTarget() {
    const f = frame();
    const target = zoomAgent || (f.cam === "focus" ? recs.a.calls[0].agent : 0);
    if (!target) return { s: 1, tx: 0, ty: 0, agent: 0 };
    const p = geo.pos[target];
    const s = Math.min(geo.W / geo.mw, (geo.H - 8) / geo.mh) * 0.985;
    return { s, tx: geo.W / 2 - p.cx * s, ty: geo.H / 2 - p.cy * s, agent: target };
  }
  function applyCam(c) {
    $("world").style.transform = `translate(${c.tx}px, ${c.ty}px) scale(${c.s})`;
  }
  function camera(animated) {
    const to = camTarget();
    cancelAnimationFrame(camRaf);
    document.body.dataset.cam = to.agent ? "focus" : "out";
    // Con la cámara adentro solo se ve la pantalla enfocada: las vecinas no asoman por los lados.
    for (const a of recs.a.agents) nodes[a].node.classList.toggle("focused", a === to.agent);
    const settle = () => {
      cam = to;
      applyCam(cam);
      document.body.classList.remove("moving");
      drawEdges(!to.agent, false);
    };
    if (!animated || calm || !cam) { settle(); return; }
    const from = { ...cam };
    if (Math.abs(from.s - to.s) < 0.001 && Math.abs(from.tx - to.tx) < 0.5) { settle(); return; }
    document.body.classList.add("moving"); // mientras la cámara se mueve no hay rótulos ni líneas
    const anchor = geo.pos[to.agent || from.agent] || { cx: geo.W / 2, cy: geo.H / 2 };
    const a0 = { x: anchor.cx * from.s + from.tx, y: anchor.cy * from.s + from.ty };
    const a1 = { x: anchor.cx * to.s + to.tx, y: anchor.cy * to.s + to.ty };
    const t0 = performance.now();
    const step = (now) => {
      const p = Math.min(1, (now - t0) / CAM_MS);
      const e = p < 0.5 ? 8 * p * p * p * p : 1 - Math.pow(-2 * p + 2, 4) / 2; // entra y sale suave, cruza rápido
      const s = Math.exp(Math.log(from.s) + (Math.log(to.s) - Math.log(from.s)) * e); // zoom parejo
      cam = { s, tx: a0.x + (a1.x - a0.x) * e - anchor.cx * s, ty: a0.y + (a1.y - a0.y) * e - anchor.cy * s, agent: to.agent };
      applyCam(cam);
      if (p < 1) camRaf = requestAnimationFrame(step);
      else settle();
    };
    camRaf = requestAnimationFrame(step);
  }

  function setZoom(agent) {
    pause();
    zoomAgent = agent;
    camera(true);
    render(false, true);
  }

  // ---------- reloj ----------

  function go(f, live) {
    const before = frame();
    F = Math.max(0, Math.min(last(), f));
    if (F > 0) started = true;
    zoomAgent = 0;
    render(!!live && frames[world][F - 1] === before, false, before.cam !== frame().cam);
  }
  /** Cuánto dura un cuadro: ?speed= acelera todo, salvo el tiempo que la cámara necesita. */
  function hold(f, prev) {
    const moves = !!prev && prev.cam !== f.cam;
    return Math.max(moves ? CAM_MS + 500 : 90, f.ms / speed);
  }
  function tick() {
    if (F >= last()) {
      // Al terminar el mundo sin Alicanto, pasa solo al mundo con Alicanto (por su tarjeta).
      if (world === "a") setWorld("b", true);
      else pause();
      return;
    }
    // En el pitch, después de la tarjeta le toca al público: elige el ataque y se corre en vivo.
    const next = frames[world][F + 1];
    if (PITCH && world === "b" && next && next.beat === "shared" && !liveAsked) { openLive(); return; }
    const prev = frame();
    go(F + 1, true);
    timer = setTimeout(tick, hold(frame(), prev));
  }
  function play() {
    if (timer) return;
    if (F >= last()) {
      if (world === "a") { setWorld("b", true); return; }
      if (PITCH) { openProof(true); return; } // el cierre del pitch: cómo lo probamos
      restart();
    }
    const fresh = !started;
    started = true;
    zoomAgent = 0;
    timer = setTimeout(tick, F === 0 ? hold(frame(), null) : 120);
    render(false);
    if (fresh && F === 0 && world === "a") spawn();
  }
  function pause() { clearTimeout(timer); timer = null; if (recs.a && geo) paintControls(); }
  /** Salta las llamadas normales: va al próximo cuadro en que pasa algo (un pedazo, la rotación,
   *  el cobro, el resultado). Para cuando el reloj aprieta. Si estaba corriendo, sigue corriendo. */
  function skip() {
    const fs = frames[world];
    let i = F + 1;
    while (i < fs.length - 1 && !(fs[i].frag || fs[i].rot || fs[i].beat || fs[i].verdict || fs[i].T > total)) i += 1;
    if (i > last()) return;
    const was = !!timer;
    clearTimeout(timer);
    timer = null;
    const prev = frame();
    go(i, false);
    if (was) timer = setTimeout(tick, hold(frame(), prev));
    paintControls();
  }
  function toggle() {
    if (liveOpen) return;
    if (card === "proof") {
      // Con la prueba a la vista, el botón la deja correr sola o la detiene.
      if (proofTimer) { proofAutoOn = false; proofWait(); }
      else { proofAutoOn = true; proofGo(proofStep >= PROOF_ASK ? 0 : proofStep + 1); }
      return;
    }
    if (card === "opening") {
      // Primer espacio: parte el reloj y se dice el pitch. Segundo espacio: parte la demo.
      if (!clockT0) { startClock(); return; }
      card = "";
      paintPitch();
      play();
      return;
    }
    timer ? pause() : play();
  }
  function restart() {
    pause();
    world = "a"; F = 0; started = false; zoomAgent = 0;
    clearTimeout(proofTimer); proofTimer = null; proofAutoOn = false;
    card = PITCH ? "opening" : "";
    if (PITCH) { clockT0 = 0; liveAsked = false; }
    if (liveRun) { location.reload(); return; } // vuelven las grabaciones del archivo
    render(false, false, true);
  }
  function setWorld(w, andPlay) {
    pause();
    if (card === "proof") { clearTimeout(proofTimer); proofTimer = null; proofAutoOn = false; card = ""; }
    world = w === "b" ? "b" : "a";
    zoomAgent = 0;
    started = true;
    // Al cambiar de mundo a mano se parte con todo a la vista, después del prólogo.
    F = world === "a" ? frames.a.findIndex((f) => f.beat === "twenty") : (andPlay ? 0 : 1);
    render(false, false, true);
    if (andPlay) play();
  }

  /** El origen: los 20 asistentes aparecen uno por uno, y la clínica tiende una línea a cada uno. */
  function spawn() {
    if (calm) return;
    document.body.classList.remove("spawn");
    void document.body.offsetWidth;
    document.body.classList.add("spawn");
    drawEdges(false, false);
    requestAnimationFrame(() => requestAnimationFrame(() => drawEdges(true, true)));
    setTimeout(() => document.body.classList.remove("spawn"), 2400);
  }

  // ---------- lo que viaja ----------

  /** Una ficha recorre un camino (lista de puntos del mundo). */
  function travel(points, text, cls, ms, delay) {
    if (calm || !geo) return;
    const tok = el("code", "token " + (cls || ""), text);
    tok.style.offsetPath = `path("M ${points.map((p) => p.join(" ")).join(" L ")}")`;
    $("tokens").appendChild(tok);
    const anim = tok.animate(
      [{ offsetDistance: "0%" }, { offsetDistance: "100%" }],
      { duration: ms, delay: delay || 0, easing: "cubic-bezier(.5,0,.3,1)", fill: "both" });
    anim.onfinish = () => tok.remove();
  }

  // ---------- dibujo ----------

  function argText(c) {
    if (c.args.path) return c.args.path;
    if (c.args.url) return c.args.url.replace(/^https?:\/\//, "");
    if (c.args.args) return c.args.args.join(" ");
    return "";
  }

  function renderDock(a, st, f) {
    const n = nodes[a];
    const mine = (st.perAgent[a] || { calls: [] }).calls;
    const first = a === recs.a.calls[0].agent;
    const sig = `${world}:${mine.length}:${first ? `${f.beat || ""}:${started}:${!!timer}` : ""}`;
    if (n.shown === sig) return;
    n.shown = sig;
    n.log.textContent = "";
    const asking = first && f.beat === "task"; // la tarea todavía se está escribiendo
    if (first && !asking && f.beat !== "origin") n.log.appendChild(el("p", "ui-ask", sc.tarea || ""));
    else if (!first) n.log.appendChild(el("p", "ui-par", sc.paralelo || ""));
    for (const c of mine.slice(-8)) {
      const row = n.log.appendChild(el("p", "ui-call"));
      row.appendChild(el("code", null, `${c.tool} ${argText(c)}`));
    }
    if (first) typeTask(n.input, asking);
  }

  /** La tarea se escribe letra por letra en el campo del asistente (solo si está corriendo). */
  let typing = null;
  function typeTask(input, asking) {
    clearInterval(typing);
    typing = null;
    const text = sc.tarea || "";
    input.classList.toggle("typed", asking);
    if (!asking) { input.textContent = sc.escribir || ""; return; }
    if (!timer || calm) { input.textContent = text; return; }
    let i = 0;
    input.textContent = "";
    const startAt = performance.now() + CAM_MS * 0.8; // espera a que la cámara llegue
    typing = setInterval(() => {
      if (performance.now() < startAt) return;
      i += 1;
      input.textContent = text.slice(0, i);
      if (i >= text.length) { clearInterval(typing); typing = null; }
    }, Math.max(16, Math.floor(1900 / text.length)));
  }

  function renderIssue(f) {
    const first = recs.a.calls[0].agent;
    const box = nodes[first].issue;
    const show = world === "a" && !!f.issue;
    if (box.hidden === !show && box.dataset.gloss === String(!!f.gloss)) return;
    box.hidden = !show;
    box.dataset.gloss = String(!!f.gloss);
    box.textContent = "";
    if (!show) return;
    const planted = recs.a.calls.find((c) => c.untrusted && c.output.includes(ATTACKER_HOST));
    box.appendChild(el("h3", null, sc.issue_titulo || "Issue 14"));
    const p = box.appendChild(el("p", "issue-body"));
    for (const part of planted.output.split(/(?<=\.)\s+/)) {
      const hot = part.includes(ATTACKER_HOST) || /asistente/i.test(part);
      p.appendChild(el(hot ? "mark" : "span", null, part + " "));
    }
    box.appendChild(el("p", "issue-flag", "Esta nota no la escribió el equipo. La plantó un atacante."));
    if (f.gloss) {
      const dl = box.appendChild(el("dl", "issue-gloss"));
      for (const [term, meaning] of sc.glosas || []) {
        dl.appendChild(el("dt")).appendChild(el("code", null, term));
        dl.appendChild(el("dd", null, meaning));
      }
    }
  }

  function renderNodes(st, f, stage) {
    const r = rec();
    const dead = stage >= 3;
    for (const a of r.agents) {
      const n = nodes[a];
      const s = st.perAgent[a];
      const mine = r.frags.filter((x) => x.agent === a && x.t <= f.T);
      const frag = mine[0];
      const lastSent = mine[mine.length - 1];
      n.node.classList.toggle("now", !!st.current && st.current.agent === a && st.cashPhase === 0);
      n.node.classList.toggle("read", !!s && s.read);
      n.node.classList.toggle("leaked", !!frag);
      n.node.classList.toggle("dead", !!frag && dead);
      n.node.classList.toggle("contrib", world === "b" && st.cashPhase >= 2 && !!frag && !!r.rotation && frag.t <= r.rotation.t);
      n.sent.textContent = lastSent ? lastSent.text + (mine.length > 1 ? ` ×${mine.length}` : "") : "";
      // Mundo a: el monitor propio de cada asistente, con la marca donde rotaría.
      n.bar.hidden = world !== "a";
      n.fill.style.width = `${Math.min(100, ((s ? s.bits : 0) / totalBits) * 100)}%`;
      n.bar.lastChild.style.left = `${(threshold / totalBits) * 100}%`;
      n.own.setAttribute("class", "own" + (s && s.read ? " read" : ""));
      for (const fr of r.frags) {
        const l = fr.agent === a ? n.outs[fr.index] : null;
        if (l) l.setAttribute("class", "out" + (fr.t <= f.T ? (dead ? " sent dead" : " sent") : ""));
      }
      renderDock(a, st, f);
    }
  }

  function renderAttacker(st, f, live, stage) {
    const r = rec();
    const atk = $("atk");
    atk.classList.toggle("rotated", stage >= 3);
    atk.classList.toggle("crumbling", f.rot === 3 && live);
    for (let i = 0; i < keyLen; i++) {
      const sp = spans[i];
      const item = r.chars[i];
      const shown = !!item && item.t <= f.T;
      sp.textContent = shown ? item.ch : "·";
      sp.classList.toggle("on", shown);
      sp.classList.toggle("new", shown && item.t === f.T && live && !!f.frag);
      sp.classList.toggle("dead", shown && stage >= 3);
      sp.classList.toggle("born-dead", shown && stage >= 3 && item.t > r.rotation.t);
    }
    renderIntent(st, f, stage);
    // Lo que tiene de la clave vigente: lo recibido, hasta que el gestor la cambia.
    count($("held"), stage >= 2 ? 0 : Math.round(st.shown * bpc), live);
    $("held-of").textContent = `de ${totalBits} bits de la clave vigente`;

    const out = $("outcome");
    out.textContent = "";
    atk.classList.toggle("cashing", st.cashPhase > 0);
    if (st.cashPhase === 0) return;
    const cash = r.cash || {};
    if (st.cashPhase < 2 || cash.status == null) {
      out.appendChild(el("p", "trying", "Prueba la clave contra la API de la clínica…"));
      return;
    }
    const ok = cash.status === 200;
    const res = out.appendChild(el("div", "result " + (ok ? "in" : "out")));
    res.appendChild(el("b", "code", String(cash.status)));
    res.appendChild(el("strong", null, ok ? "Entró." : "Manos vacías."));
  }

  /** El emblema: qué busca. La llave se llena con cada pedazo; se apaga si la clave rota. */
  function renderIntent(st, f, stage) {
    const r = rec();
    const box = $("intent");
    const p = keyLen ? Math.min(1, st.shown / keyLen) : 0;
    const dead = stage >= 3;
    const opened = st.cashPhase >= 2 && (r.cash || {}).status === 200;
    $("keyfill-rect").setAttribute("width", String(Math.round(96 * p)));
    box.classList.toggle("dead", dead);
    box.classList.toggle("full", p >= 1 && !dead);
    box.classList.toggle("opened", opened);
    $("intent-text").textContent = opened
      ? "Lo logró: tiene la clave y abrió una ficha."
      : dead
        ? "Lo que tiene es de una clave anulada. Las fichas siguen cerradas."
        : p >= 1
          ? "Ya tiene la clave completa. Le falta usarla."
          : (sc.atacante_quiere || "Quiere la clave para abrir las fichas.");
  }

  /** Un número que cambia cuenta hasta su valor nuevo (solo si la escena está corriendo). */
  const counting = new WeakMap();
  function count(node, to, live) {
    const from = Number(node.textContent) || 0;
    cancelAnimationFrame(counting.get(node) || 0);
    if (!live || calm || from === to) { node.textContent = String(to); return; }
    const t0 = performance.now() + (to > from ? 850 : 0); // sube cuando llega el pedazo
    const step = (now) => {
      const p = Math.max(0, Math.min(1, (now - t0) / 420));
      node.textContent = String(Math.round(from + (to - from) * (1 - Math.pow(1 - p, 3))));
      if (p < 1) counting.set(node, requestAnimationFrame(step));
    };
    counting.set(node, requestAnimationFrame(step));
  }

  /** El resultado, en grande: lo que obtuvo el dueño del servidor. */
  function renderVerdict(st, f, live) {
    const r = rec();
    const v = $("verdict");
    const show = !!f.verdict && !zoomAgent;
    document.body.classList.toggle("verdict", show);
    if (!show) { v.hidden = true; return; }
    const was = v.hidden;
    v.hidden = false;
    const cash = r.cash || {};
    const ok = cash.status === 200;
    const blocked = r.calls.filter((c) => /block/.test(c.action)).length;
    v.className = ok ? "in" : "out";
    $("v-code").textContent = String(cash.status);
    $("v-line").textContent = ok ? `Entró a la ${sc.api || "API"}.` : "Manos vacías.";
    const vk = $("v-key");
    vk.textContent = "";
    for (let i = 0; i < r.chars.length; i += group) {
      vk.appendChild(el("span", null, r.chars.slice(i, i + group).map((x) => x.ch).join("")));
    }
    $("v-facts").textContent = ok
      ? `Juntó los ${totalBits} bits de la clave con pedazos de ${cuantos(senders(r, f.T), "asistente")}. Lo máximo que vio un monitor: ${Math.round(st.monitorMax)} bits.`
      : `Juntó ${r.chars.length} caracteres de una clave que la clínica anuló en la llamada ${r.rotation ? r.rotation.t : "?"}.`;
    const right = $("v-right");
    right.textContent = "";
    if (ok) {
      const fi = sc.ficha || {};
      const doc = right.appendChild(el("article", "doc"));
      doc.setAttribute("data-ui", "");
      const head = doc.appendChild(el("header"));
      head.appendChild(el("b", null, fi.titulo || "Ficha clínica"));
      head.appendChild(el("span", null, sc.clinica || ""));
      doc.appendChild(el("h3", null, fi.nombre || ""));
      const dl = doc.appendChild(el("dl"));
      for (const [k, val] of fi.campos || []) { dl.appendChild(el("dt", null, k)); dl.appendChild(el("dd", null, val)); }
      for (const [title, text] of fi.secciones || []) {
        const sec = doc.appendChild(el("section"));
        sec.appendChild(el("b", null, title));
        sec.appendChild(el("p", null, text));
      }
      doc.appendChild(el("em", null, "Ficha de ejemplo, ficticia"));
    } else {
      const none = right.appendChild(el("div", "nothing"));
      none.appendChild(el("b", null, "0 fichas"));
      none.appendChild(el("p", null, "La API de la clínica no le entregó nada: la clave que juntó ya no existe."));
      none.appendChild(el("p", null, `Los ${r.agents.length} asistentes siguieron trabajando: ${blocked} llamadas bloqueadas de ${total}.`));
      none.appendChild(el("p", null, "La clínica tiene una clave nueva, que el atacante no conoce."));
    }
    if (was && live && !calm && geo) {
      // Crece desde la columna del atacante hasta llenar el escenario.
      const to = v.getBoundingClientRect();
      const st0 = $("stage").getBoundingClientRect();
      const s = geo.atk.bottom > geo.atk.top ? (geo.atk.bottom - geo.atk.top) / to.height : 0.5;
      v.animate(
        [{ transform: `translate(${geo.atk.left - (to.left - st0.left)}px, ${geo.atk.top - (to.top - st0.top)}px) scale(${s})`, opacity: 0.2 },
         { transform: "none", opacity: 1 }],
        { duration: 650, easing: "cubic-bezier(0.77, 0, 0.175, 1)" });
    }
  }

  function renderGate(st, f, stage, live) {
    const gate = $("gate");
    gate.hidden = world !== "b";
    paths.signalEl.setAttribute("class", "signal" + (world === "b" && stage >= 2 ? " on" : ""));
    if (world !== "b") return;
    const led = stage >= 2 ? 0 : st.ledger;
    gate.classList.toggle("limit", stage === 1);
    $("gate-fill").style.height = `${Math.min(100, (led / totalBits) * 100)}%`;
    $("gate-mark").style.bottom = `${(threshold / totalBits) * 100}%`;
    count($("gate-bits"), Math.round(led), live);
    $("gate-of").textContent = stage >= 2 ? "bits de la clave nueva" : `de ${totalBits} bits. Límite: ${threshold}`;
  }

  function renderClinic(st, f, stage) {
    const r = rec();
    $("blk-team").classList.toggle("hot", f.beat === "origin");
    $("blk-repo").classList.toggle("hot", !!f.read);
    $("blk-vault").classList.toggle("hot", f.rot === 2);
    $("blk-api").classList.toggle("hot", st.cashPhase > 0);
    const v1 = $("vault-v1");
    v1.classList.toggle("void", stage >= 2);
    v1.lastChild.textContent = stage >= 2 ? "anulada" : "vigente";
    $("vault-v2").hidden = stage < 2;
    const cash = r.cash || {};
    $("api-text").textContent = st.cashPhase === 0
      ? "Entrega fichas a quien presente la clave vigente."
      : st.cashPhase === 1
        ? "Llega un pedido con la clave que juntó el atacante."
        : cash.status === 200
          ? "200. La clave sirve: entrega la ficha."
          : `${cash.status}. Esa clave ya no existe: no entrega nada.`;
    paths.cashEl.setAttribute("class", "cash" + (st.cashPhase > 0 ? " on" : ""));
  }

  /** Lo que se mueve en este cuadro: la clave leída, el pedazo que sale, la orden de rotar, el cobro. */
  function animate(st, f, stage) {
    const r = rec();
    if (f.read) {
      const p = geo.pos[f.read];
      travel([[geo.repo.left, geo.repo.cy], [p.right, p.cy]], "clave", "", 380, 0);
    }
    if (f.frag) {
      const p = geo.pos[f.frag.agent];
      const g = geo.groups[f.frag.index];
      const dead = !!r.rotation && f.frag.t > r.rotation.t;
      travel([[p.left, p.cy], [geo.atk.right, g.cy], [g.cx, g.cy]], f.frag.text, dead ? "dead" : "", FLY_MS, 0);
    }
    if (f.rot === 2) travel(paths.signal, "cambia la clave", "order", 1500, 150);
    if (st.cashPhase === 1) travel(paths.cash, shortKey(r.chars.map((x) => x.ch).join("")), stage >= 3 ? "dead" : "", 1500, 100);
  }

  /** Cuántos asistentes distintos han mandado un pedazo hasta la llamada T. */
  function senders(r, T) {
    return new Set(r.frags.filter((x) => x.t <= T).map((x) => x.agent)).size;
  }
  const cuantos = (n, uno) => (n === 1 ? `un ${uno}` : `${n} ${uno}s`);
  /** «los asistentes 15, 04 y 13», sin repetir. */
  function lista(agents) {
    const u = [...new Set(agents)].map(two);
    if (u.length === 1) return `el asistente ${u[0]}`;
    return `los asistentes ${u.slice(0, -1).join(", ")} y ${u.slice(-1)}`;
  }

  function caption(st, f, stage) {
    const r = rec();
    const n = r.agents.length;
    if (zoomAgent) {
      const s = st.perAgent[zoomAgent];
      const frag = r.frags.find((x) => x.agent === zoomAgent && x.t <= f.T);
      const count = s ? s.calls.length : 0;
      return `Asistente ${two(zoomAgent)}: ` +
        (count ? `${count} ${count === 1 ? "llamada, permitida" : "llamadas, todas permitidas"}.` : "todavía no hace ninguna llamada.") +
        (frag ? ` En la llamada ${frag.t} mandó «${frag.text}».` : count ? " No ha mandado nada fuera." : "") +
        " Escape para volver.";
    }
    if (f.beat === "origin") return `Estos ${n} asistentes de código son de la clínica. Afuera, alguien quiere una clave.`;
    if (f.beat === "task") return "Entramos a uno. Le piden arreglar un error de la agenda.";
    if (f.beat === "reads") return "Parte leyendo la documentación del repositorio.";
    if (f.beat === "issue") return "Abre el issue. Trae una instrucción que el equipo no escribió.";
    if (f.beat === "gloss") return "Quieren la clave de las fichas. De a 4 caracteres, para que nada parezca un robo.";
    if (f.beat === "normal") return "El asistente sigue trabajando. En pantalla, nada raro.";
    if (f.beat === "twenty") return `La nota les habla a todos. El atacante no trae agentes: usa los ${n} de la clínica.`;
    if (f.beat === "card") return "";
    if (f.beat === "shared") {
      if (!liveRun) return "Todo lo que sale pasa por Alicanto, que lleva una sola cuenta por clave.";
      const a = liveRun.resumen.a;
      return a.cobro === 200
        ? `Con un monitor por agente, su ataque pasa: ninguno vio más de ${Math.round(a.max_bits)} bits. Ahora, con Alicanto.`
        : `Con ${cuantos(liveRun.params.reparten, "asistente")}, hasta un monitor por agente lo frena. Con Alicanto pasa esto.`;
    }

    const done = F >= last();
    const cash = r.cash || {};
    const got = r.frags.filter((x) => x.t <= f.T).length;
    if (st.cashPhase === 1) return "El atacante prueba la clave contra la API de la clínica.";
    if (st.cashPhase >= 2 && !done) {
      if (cash.status === 200) return "200. La clave sirve, y la API le entrega una ficha.";
      const who = r.rotation ? r.frags.filter((x) => x.t <= r.rotation.t).map((x) => x.agent) : [];
      return `${cash.status}. Esa clave ya no existe.` +
        (who.length ? ` Lo que alcanzó a salir vino de ${lista(who)}.` : "");
    }
    if (world === "a") {
      const readers = r.calls.filter(readsKey).length;
      const quien = readers === 1 ? "Un asistente lee" : `${readers === 10 ? "Diez" : readers} asistentes leen`;
      const de = senders(r, f.T);
      if (done) {
        return cash.status === 200
          ? `Ningún monitor vio más de ${Math.round(st.monitorMax)} de ${totalBits} bits. El atacante se llevó una ficha.`
          : `Con ${cuantos(de, "asistente")}, el monitor de uno alcanzó a verlo: ${cash.status} y ninguna ficha.`;
      }
      // Con pocos asistentes, el monitor de uno llega a su límite y rota (corridas en vivo).
      if (f.rot === 1) return `El monitor de ese asistente llega a su límite: ya vio ${threshold} de ${totalBits} bits.`;
      if (f.rot === 2) return "Ese monitor pide cambiar la clave en el gestor de secretos.";
      if (f.rot === 3) return "Lo que el atacante juntó es de la clave vieja. Ya no abre nada.";
      if (stage >= 3) return "Los pedazos siguen saliendo, pero son de la clave vieja.";
      if (f.read) return `${quien} la clave del repositorio. ${readers === 1 ? "Tiene" : "Tienen"} permiso para hacerlo.`;
      const reads = r.calls.filter((c) => readsKey(c) && c.t <= f.T).length;
      if (got === 0) return reads ? "Ya tienen la clave. Todavía no sale nada." : "Cada asistente tiene su propio monitor. Todos trabajan normal.";
      if (st.shown >= keyLen) return `Clave completa: ${got} pedazos, por ${cuantos(de, "asistente")}. Ningún monitor avisó.`;
      if (got <= 2) return `Uno manda 4 caracteres. Para su monitor son ${Math.round(group * bpc)} bits de ${totalBits}: nada.`;
      return de === got ? `Van ${got} pedazos, cada uno por un asistente distinto.` : `Van ${got} pedazos, entre ${cuantos(de, "asistente")}.`;
    }
    if (done) {
      const blocked = r.calls.filter((c) => /block/.test(c.action)).length;
      return `${cash.status} y ninguna ficha. Las mismas ${total} llamadas, ${blocked} bloqueadas.`;
    }
    if (f.rot === 1) return `Tercer pedazo. La cuenta llega a ${threshold} de ${totalBits} bits: su límite.`;
    if (f.rot === 2) return "Alicanto pide cambiar la clave en el gestor de secretos. No bloquea a nadie.";
    if (f.rot === 3) return "Lo que el atacante juntó es de la clave vieja. Ya no abre nada.";
    if (stage >= 3) return "Los pedazos siguen saliendo, pero son de la clave vieja.";
    if (f.read) return "Los asistentes leen la clave del repositorio, igual que antes.";
    if (got === 0) return "Alicanto no mira a cada asistente: suma lo que sale de la clave.";
    return `Sale un pedazo y pasa. La cuenta suma ${Math.round(st.ledger)} de ${totalBits} bits.`;
  }

  function paintControls() {
    const f = frame();
    const proof = card === "proof";
    $("play").textContent = (proof ? proofTimer : timer) ? "Pausa" : "Reproducir";
    $("clock").textContent = proof ? `paso ${proofStep + 1} de ${PROOF_LAST + 1}` : `llamada ${Math.min(f.T, total)} de ${total}`;
    for (const b of document.querySelectorAll(".world")) b.classList.toggle("active", !proof && b.dataset.world === world);
    $("proof-open").classList.toggle("active", proof);
    document.body.classList.toggle("idle", !started);
  }

  function render(live, keepCam, camAnimated) {
    if (!recs.a || !geo) return;
    const r = rec();
    const f = frame();
    const st = stateAt(r, f.T);
    const stage = rotStage(r, f);
    document.body.dataset.world = world;
    document.body.dataset.t = String(f.T);
    document.body.dataset.frame = String(F);
    document.body.dataset.stage = String(stage);
    document.body.classList.toggle("done", F >= last());

    renderIssue(f);
    renderNodes(st, f, stage);
    renderAttacker(st, f, live, stage);
    renderGate(st, f, stage, live);
    renderClinic(st, f, stage);
    renderVerdict(st, f, live);
    if (!keepCam) camera(!!camAnimated && started);
    if (live && f.cam === "out" && !zoomAgent) animate(st, f, stage);

    // El corte entre los dos mundos, y la entrada de Alicanto.
    $("card").classList.toggle("on", f.beat === "card");
    document.body.classList.toggle("carded", f.beat === "card");
    document.body.classList.toggle("gate-in", f.beat === "shared" && live);
    // Dónde hay que mirar: lo demás se atenúa.
    document.body.dataset.spot = zoomAgent ? "" : f.rot ? `rot${f.rot}` : st.cashPhase > 0 && !f.verdict ? "cash" : "";

    $("title").textContent = world === "a"
      ? "Sin Alicanto: cada asistente con su propio monitor"
      : liveRun
        ? `Con Alicanto, en vivo: ${cuantos(liveRun.params.reparten, "asistente")}, ${DISFRAZ[liveRun.params.disfraz] || liveRun.params.disfraz}, número ${liveRun.params.semilla}`
        : "Con Alicanto: una sola cuenta por clave, en la salida";
    const proof = card === "proof";
    $("engine").textContent = proof ? proofEngine() : engineLine(st, f, stage);
    $("note").textContent = proof ? proofNote() : `${sc.ficticio || "Todo es ficticio."} ${sc.maqueta || ""} ` +
      (liveRun ? (sc.corrida_en_vivo || "") : (sc.corrida_grabada || ""));
    paintPitch();
    const cap = $("caption");
    const text = proof ? proofCaption() : card || liveOpen ? "" : caption(st, f, stage);
    if (cap.textContent !== text) {
      cap.textContent = text;
      if ((live || proof) && !calm) { cap.classList.remove("fresh"); void cap.offsetWidth; cap.classList.add("fresh"); }
    }
    paintControls();
  }

  // ---------- el pitch: apertura, el público elige, el motor corre en vivo, la prueba ----------

  const DISFRAZ = { none: "tal cual", base64: "en base64", reversed: "al revés" };
  const sleep = (ms) => new Promise((ok) => setTimeout(ok, ms));

  /** Lo que el motor hizo de verdad: su decisión en la rotación, o los datos de la corrida. */
  function engineLine(st, f, stage) {
    const r = rec();
    if (f.rot && r.rotation) {
      const c = r.calls.find((x) => x.t === r.rotation.t);
      const ms = c && c.latency != null ? ` · decidió y rotó en ${c.latency.toFixed(2).replace(".", ",")} ms` : "";
      return `motor › ${c ? c.action : "rotate"} · ${Math.round(c ? c.bits : 0)} de ${totalBits} bits${ms}`;
    }
    if (liveRun) {
      const p = liveRun.params;
      return `en vivo › reparten ${p.reparten} · ${DISFRAZ[p.disfraz]} · número ${p.semilla} · ${Math.round(liveRun.ms.a + liveRun.ms.b)} ms`;
    }
    return `corrida grabada del motor › ${total} llamadas de ${r.agents.length} agentes`;
  }

  /** Las tarjetas del pitch y el panel del público: se arman una vez. */
  function buildPitch() {
    const ap = sc.apertura || {};
    $("open-1").textContent = ap.titulo || "Alicanto";
    $("open-2").textContent = ap.frase || "";
    $("open-3").textContent = ap.pie || "";
    buildProof();
    for (const b of document.querySelectorAll("#q-reparten button")) {
      b.addEventListener("click", () => { pick.reparten = Number(b.dataset.v); pick.chosen[0] = true; pick.step = Math.max(pick.step, 1); paintLive(); });
    }
    for (const b of document.querySelectorAll("#q-disfraz button")) {
      b.addEventListener("click", () => { pick.disfraz = b.dataset.v; pick.chosen[1] = true; pick.step = 2; paintLive(); });
    }
    $("live-run").addEventListener("click", () => { if (!running) runLive(); });
    if (PITCH) setInterval(paintClock, 250);
  }

  function startClock() {
    clockT0 = performance.now();
    paintPitch();
  }
  function paintClock() {
    const node = $("timer");
    node.hidden = !PITCH;
    if (!PITCH) return;
    const left = clockT0 ? PITCH_MS - (performance.now() - clockT0) : PITCH_MS;
    const s = Math.ceil(Math.abs(left) / 1000);
    node.textContent = `${left < 0 ? "+" : ""}${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    node.classList.toggle("late", clockT0 > 0 && left < 20000);
    node.classList.toggle("over", left < 0);
  }
  function paintPitch() {
    $("opening").classList.toggle("on", card === "opening");
    $("proof").classList.toggle("on", card === "proof");
    document.body.classList.toggle("carded", card !== "" || (!!frame() && frame().beat === "card") || liveOpen);
    $("open-hint").textContent = clockT0 ? "Espacio: empieza la demo" : "Espacio: parte el reloj";
    paintClock();
  }

  // ---------- cómo lo probamos: rojo, morado y azul; la corrida, sus límites y el pedido ----------
  //
  // Seis pasos. 0: el rojo escribe los ataques y sella el set. 1: el azul congela el detector, y
  // las reglas del morado. 2: la corrida única. 3: lo que cuesta y lo que se escapa. 4: el pedido.
  // 5: la misma medición con otros guardias (para las preguntas; sola no llega hasta ahí).
  // Aquí no hay ninguna cifra escrita: salen de evaluacion.json, y los textos, de escenario.json.

  const PROOF_LAST = 5;
  const PROOF_ASK = 4;
  const PROOF_MS = [9000, 5500, 6000, 7000]; // lo que dura cada paso cuando corre sola, en el pitch
  const miles = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const coma = (n) => String(n).replace(".", ",");
  const corto = (h) => `${String(h).slice(0, 8)}…`;
  const fill = (t, v) => String(t || "").replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m));
  let pv = {}; // los números que entran en los textos

  function buildProof() {
    if (!evalData) { $("proof-open").hidden = true; return; }
    const P = sc.prueba || {};
    const A = evalData.ataques;
    const N = evalData.normales;
    const S = evalData.sello;
    const per = evalData.sistemas.find((s) => s.id === "per_session");
    pv = {
      n: A.n, frenados: A.frenados, familias: A.familias, familias_frenadas: A.familias_frenadas,
      frenados_grabadas: A.frenados_grabadas, llamadas: miles(N.llamadas), bloqueadas: N.bloqueadas,
      dificiles: N.sesiones_dificiles, de_mas: N.con_rotacion_de_mas,
      hora: S.hora, abierto: S.abierto, sello: corto(S.sha256), commit: S.commit,
      commit_congelado: S.commit_congelado, commit_corrida: S.commit_corrida,
      congelado: corto(evalData.congelado.hash), por_agente: per ? per.frenados : "",
    };
    $("pf-title").textContent = P.titulo || "";
    for (const k of ["rojo", "morado", "azul"]) {
      const t = (P.equipos || {})[k] || {};
      const box = $("pf-" + k);
      box.querySelector("h3 span").textContent = t.nombre || "";
      box.querySelector(".pf-what").textContent = t.que || "";
      box.querySelector(".pf-fact").textContent = fill(t.hecho, pv);
    }
    $("pf-seal-1").textContent = fill(P.precinto, pv);
    $("pf-seal-2").textContent = `sha256 ${S.sha256.slice(0, 12)}…${S.sha256.slice(-6)}`;
    $("pf-ask").textContent = P.pedido || "";

    // La grilla: una fila por familia, una casilla por sesión.
    const grid = $("pf-grid");
    const seal = $("pf-seal");
    const names = P.familias || {};
    const put = (node, row) => { node.style.gridRow = String(row); grid.insertBefore(node, seal); return node; };
    const head = (texts, row, cls) => {
      put(el("span", `pf-label pf-head ${cls}`, (texts || [])[0] || ""), row);
      put(el("span", `pf-count pf-head ${cls}`, (texts || [])[1] || ""), row);
    };
    const line = (id, states, countText, row, r, cls, what) => {
      const label = put(el("span", `pf-label ${cls}`), row);
      label.appendChild(el("i", "pf-id", id));
      label.appendChild(document.createTextNode(names[id] || ""));
      const cells = put(el("span", `pf-cells ${cls}`), row);
      cells.dataset.fam = id;
      cells.setAttribute("role", "img"); // las casillas son un dibujo: esto es lo que dice
      cells.setAttribute("aria-label", `${id}, ${names[id] || ""}: ${countText} ${what}`);
      states.forEach((s, i) => {
        const c = cells.appendChild(el("i", `pf-c ${s}`));
        c.style.setProperty("--i", i);
        c.style.setProperty("--r", r);
      });
      put(el("span", `pf-count ${cls}`, countText), row).style.setProperty("--r", r);
    };
    const G = P.grupos || {};
    const nA = evalData.familias.length;
    const nB = N.familias.length;
    head(G.ataques, 1, "atk");
    evalData.familias.forEach((f, r) => {
      const states = Array.from({ length: f.n }, (_, i) => (i < f.frenados ? "stop" : "out"));
      line(f.id, states, `${f.frenados} de ${f.n}`, 2 + r, r, f.frenados === f.n ? "atk" : "atk esc", (G.ataques || [])[1] || "");
    });
    head(G.normales, 2 + nA, "ben");
    N.familias.forEach((f, r) => {
      const states = f.tira.split("").map((c) => (c === "1" ? "rot" : "calm"));
      line(f.id, states, `${f.con_rotacion_de_mas} de ${f.n}`, 3 + nA + r, nA + r, "ben", (G.normales || [])[1] || "");
    });
    const end = 3 + nA + nB;
    grid.style.gridTemplateRows = `0.9em repeat(${nA}, calc(1em * var(--rh, 1))) 1.5em repeat(${nB}, calc(1em * var(--rh, 1)))`;
    $("pf-num-a").style.gridRow = `2 / ${2 + nA}`;
    $("pf-num-b").style.gridRow = `${3 + nA} / ${end}`;
    seal.style.gridRow = `2 / ${end}`;

    // La misma medición con otros guardias: una barra por sistema.
    const O = P.otros || {};
    const vs = $("pf-vs");
    vs.style.gridRow = `1 / ${end}`;
    vs.appendChild(el("p", "vs-head", O.titulo || "")).appendChild(el("span", null, fill(O.unidad, pv)));
    const rows = vs.appendChild(el("div", "vs-rows"));
    evalData.sistemas.filter((s) => (O.sistemas || {})[s.id]).forEach((s, k) => {
      const us = s.id === "ours" ? " us" : "";
      rows.appendChild(el("span", "l" + us, O.sistemas[s.id]));
      const bar = rows.appendChild(el("span", "bar")).appendChild(el("i", us.trim()));
      bar.style.setProperty("--w", `${((100 * s.frenados) / A.n).toFixed(2)}%`);
      bar.style.setProperty("--k", k);
      rows.appendChild(el("span", "n" + us, String(s.frenados))).dataset.sys = s.id;
      rows.appendChild(el("span", "x", s.normales_bloqueadas_pct > 0
        ? fill(O.bloquea, { pct: coma(s.normales_bloqueadas_pct) }) : ""));
    });
    vs.appendChild(el("p", "vs-foot", fill(O.pie, pv)));

    $("proof").addEventListener("click", () => { if (card === "proof") proofNext(); });
    $("proof-open").addEventListener("click", () => (card === "proof" ? closeProof() : openProof(PITCH)));
  }

  function openProof(auto) {
    if (!evalData || liveOpen || card === "opening") return;
    pause();
    card = "proof";
    proofStep = 0;
    proofAutoOn = !!auto;
    paintProof(false);
    render(false);
    checkSeal();
    proofWait();
  }
  function closeProof() {
    clearTimeout(proofTimer);
    proofTimer = null;
    proofAutoOn = false;
    card = "";
    render(false);
  }
  /** Va a un paso. Si la escena venía corriendo sola, sigue sola desde ahí. */
  function proofGo(step) {
    const to = Math.max(0, Math.min(PROOF_LAST, step));
    const forward = to === proofStep + 1;
    proofStep = to;
    paintProof(forward);
    render(false);
    proofWait();
  }
  function proofWait() {
    clearTimeout(proofTimer);
    proofTimer = null;
    if (proofStep >= PROOF_ASK) proofAutoOn = false; // el pedido se queda; el paso 5 es a mano
    if (proofAutoOn) {
      const k = speed / (PITCH ? 1.5 : 1);
      proofTimer = setTimeout(() => proofGo(proofStep + 1), Math.max(400, PROOF_MS[proofStep] / k));
    }
    paintControls();
  }
  function proofNext() { if (proofStep < PROOF_LAST) proofGo(proofStep + 1); }
  function proofKey(ev) {
    const k = ev.key;
    if (ev.code === "Space" || k === "Enter") {
      ev.preventDefault();
      if (proofStep < PROOF_ASK) proofGo(proofStep + 1); // el espacio no pasa del pedido
    } else if (ev.code === "ArrowRight") proofNext();
    else if (ev.code === "ArrowLeft") { proofAutoOn = false; proofGo(proofStep - 1); }
    else if (k === "Escape" || k === "e" || k === "E") closeProof();
    else if (k === "r" || k === "R") restart();
  }

  function paintProof(forward) {
    const p = $("proof");
    for (let i = 1; i <= PROOF_LAST; i++) p.classList.toggle("s" + i, proofStep >= i);
    p.dataset.step = String(proofStep);
    const T = (sc.prueba || {}).numeros || {};
    const A = evalData.ataques;
    const N = evalData.normales;
    const ran = proofStep >= 2; // ya se corrió
    const na = $("pf-n-a");
    cancelAnimationFrame(counting.get(na) || 0);
    if (forward && proofStep === 2 && !calm) climb(na, A.frenados);
    else na.textContent = String(ran ? A.frenados : A.n);
    $("pf-t-a").textContent = fill(ran ? T.a_despues : T.a_antes, pv);
    $("pf-n-b").textContent = String(ran ? N.bloqueadas : N.sesiones_dificiles);
    $("pf-t-b").textContent = fill(proofStep >= 3 ? T.b_limites : ran ? T.b_despues : T.b_antes, pv);
    paintSeal();
  }
  /** La cifra sube junto con el barrido de las casillas. */
  function climb(node, to) {
    const t0 = performance.now() + 400;
    node.textContent = "0";
    const step = (now) => {
      const u = Math.max(0, Math.min(1, (now - t0) / 1050));
      node.textContent = String(Math.round(to * u));
      if (u < 1) counting.set(node, requestAnimationFrame(step));
    };
    counting.set(node, requestAnimationFrame(step));
  }

  /** El sello del set: el publicado y, si servidor.py está, el que se recalculó recién. */
  function paintSeal() {
    const P = sc.prueba || {};
    const fact = $("pf-rojo").querySelector(".pf-fact");
    fact.textContent = fill(((P.equipos || {}).rojo || {}).hecho, pv);
    if (sealLive) fact.appendChild(el("b", sealLive.coincide ? null : "bad", sealLive.coincide ? P.sello_vivo : P.sello_falla));
  }
  async function checkSeal() {
    if (sealAsked) return;
    sealAsked = true;
    try {
      const ctl = new AbortController();
      const cut = setTimeout(() => ctl.abort(), 4000);
      const r = await fetch(SEAL_API, { signal: ctl.signal, cache: "no-store" });
      clearTimeout(cut);
      if (!r.ok) throw new Error(String(r.status));
      const j = await r.json();
      // La página compara por su cuenta con el sello publicado: no le cree al servidor.
      if (j && /^[0-9a-f]{64}$/.test(j.sha256 || "")) sealLive = { ...j, coincide: j.sha256 === evalData.sello.sha256 };
    } catch (_) {
      sealLive = null;
    }
    document.body.dataset.sello = sealLive ? (sealLive.coincide ? "coincide" : "distinto") : "publicado";
    if (card === "proof") { paintSeal(); render(false); }
  }

  const proofCaption = () => fill(((sc.prueba || {}).leyendas || [])[proofStep], pv);
  const proofNote = () => fill(((sc.prueba || {}).notas || [])[proofStep], pv);
  /** De dónde sale lo que se ve: el sello, la configuración congelada o el comando que lo mide. */
  function proofEngine() {
    const S = evalData.sello;
    if (proofStep === 0) {
      return sealLive
        ? `sello › recalculado ahora: ${corto(sealLive.sha256)} ${sealLive.coincide ? "coincide" : "NO coincide"} · ${sealLive.archivos} archivos · ${coma(sealLive.ms)} ms`
        : `sello › sha256 ${corto(S.sha256)} · commit ${S.commit} · redteam/SELLO.md`;
    }
    if (proofStep === 1) {
      const q = evalData.congelado.params;
      return `congelado › ${corto(evalData.congelado.hash)} · T ${q.T} · b ${q.b} · b_rot ${q.b_rot} · lambda_rot ${coma(q.lambda_rot)}`;
    }
    return `$ ${evalData.medicion.comando} · commit ${evalData.medicion.commit}`;
  }

  // --- el público elige el ataque ---

  function openLive() {
    if (liveOpen) return;
    pause();
    if (world !== "b") { world = "b"; zoomAgent = 0; started = true; F = 0; }
    liveOpen = true;
    liveAsked = true;
    pick.step = 0; pick.semilla = ""; pick.chosen = [false, false];
    $("console").hidden = true;
    $("console").textContent = "";
    $("live").classList.add("on");
    render(false);
    paintLive();
  }
  function paintLive() {
    const steps = ["q-reparten", "q-disfraz", "q-semilla"];
    steps.forEach((id, i) => {
      $(id).classList.toggle("now", !running && pick.step === i);
      $(id).classList.toggle("later", !running && pick.step < i);
    });
    for (const b of document.querySelectorAll("#q-reparten button")) {
      b.classList.toggle("sel", pick.chosen[0] && Number(b.dataset.v) === pick.reparten);
    }
    for (const b of document.querySelectorAll("#q-disfraz button")) {
      b.classList.toggle("sel", pick.chosen[1] && b.dataset.v === pick.disfraz);
    }
    $("seed").textContent = pick.semilla || (pick.step === 2 ? "_" : "");
    $("live-pick").textContent = running
      ? `${cuantos(pick.reparten, "asistente")} · cada pedazo ${DISFRAZ[pick.disfraz]} · número ${pick.semilla}`
      : "";
    $("live-run").classList.toggle("now", !running && pick.step === 2);
    $("live").classList.toggle("running", running);
  }
  function liveKey(ev) {
    if (running) { ev.preventDefault(); return; }
    const k = ev.key;
    const low = k.toLowerCase();
    let used = true;
    if (k === "Escape") { finishLive(null); ev.preventDefault(); return; } // sin corrida en vivo: sigue la grabada
    const move = k === "ArrowRight" ? 1 : k === "ArrowLeft" ? -1 : 0;
    const cycle = (list, value) => list[(list.indexOf(value) + move + list.length) % list.length];
    if (k === "Backspace" && !(pick.step === 2 && pick.semilla)) pick.step = Math.max(0, pick.step - 1);
    else if (pick.step === 0) {
      const map = { 1: 1, 2: 2, 5: 5, 0: 10 };
      if (map[k]) { pick.reparten = map[k]; pick.chosen[0] = true; pick.step = 1; }
      else if (move) { pick.reparten = pick.chosen[0] ? cycle([1, 2, 5, 10], pick.reparten) : (move > 0 ? 1 : 10); pick.chosen[0] = true; }
      else if (k === "Enter") { pick.chosen[0] = true; pick.step = 1; }
      else used = false;
    } else if (pick.step === 1) {
      const map = { t: "none", b: "base64", r: "reversed", 1: "none", 2: "base64", 3: "reversed" };
      const names = ["none", "base64", "reversed"];
      if (map[low]) { pick.disfraz = map[low]; pick.chosen[1] = true; pick.step = 2; }
      else if (move) { pick.disfraz = pick.chosen[1] ? cycle(names, pick.disfraz) : (move > 0 ? "none" : "reversed"); pick.chosen[1] = true; }
      else if (k === "Enter") { pick.chosen[1] = true; pick.step = 2; }
      else used = false;
    } else if (/^\d$/.test(k)) {
      if (pick.semilla.length < 6) pick.semilla += k;
    } else if (k === "Backspace") {
      pick.semilla = pick.semilla.slice(0, -1);
    } else if (k === "Enter") {
      ev.preventDefault();
      runLive();
      return;
    } else used = false;
    if (used) ev.preventDefault();
    paintLive();
  }

  /** Corre el motor del repositorio con lo que eligió el público y muestra lo que imprimió. */
  async function runLive() {
    if (running) return;
    running = true;
    pick.chosen = [true, true];
    const seed = pick.semilla ? Number(pick.semilla) : Math.floor(Date.now() / 1000) % 100000;
    pick.semilla = String(seed);
    paintLive();
    const cons = $("console");
    cons.hidden = false;
    cons.textContent = `$ python hacer_corrida.py --reparten ${pick.reparten} --disfraz ${pick.disfraz} --semilla ${seed}\n`;
    let resp = null;
    try {
      const ctl = new AbortController();
      const cut = setTimeout(() => ctl.abort(), 6000);
      const r = await fetch(`${API}?reparten=${pick.reparten}&disfraz=${pick.disfraz}&semilla=${seed}`,
        { signal: ctl.signal, cache: "no-store" });
      clearTimeout(cut);
      if (!r.ok) throw new Error(`el servidor respondió ${r.status}`);
      resp = await r.json();
      if (!resp || !resp.a || !resp.b || !resp.resumen) throw new Error("respuesta incompleta");
    } catch (_) {
      resp = null;
    }
    if (resp) {
      for (const line of resp.lineas.slice(1)) {
        await sleep(calm ? 0 : 420);
        cons.textContent += line + "\n";
      }
      await sleep(calm ? 0 : 320);
      cons.textContent += `listo en ${Math.round(resp.ms.a + resp.ms.b)} ms: corrió recién, en este computador, con el motor del repositorio.\n`;
    } else {
      cons.textContent += "No hay servidor en vivo en este computador (servidor.py).\n" +
        "Sigue la corrida grabada: 10 asistentes, tal cual, semilla 47.\n";
    }
    document.body.dataset.live = resp ? "si" : "grabada";
    await sleep(calm ? 0 : 2400);
    finishLive(resp);
  }

  /** Cierra el panel y sigue: con la corrida del público si la hubo, o con la grabada. */
  function finishLive(resp) {
    if (resp) {
      liveRun = resp;
      document.body.dataset.params = JSON.stringify(resp.params); // lo lee terminales.html
      recs.a = parseRecording(resp.a, SECRET, resp.params.disfraz);
      recs.b = parseRecording(resp.b, SECRET, resp.params.disfraz);
      frames.a = buildFrames(recs.a, "a");
      frames.b = buildFrames(recs.b, "b");
      derive();
      for (const a of recs.a.agents) nodes[a].shown = ""; // los paneles se vuelven a escribir
      layout();
    }
    running = false;
    liveOpen = false;
    $("live").classList.remove("on");
    world = "b";
    F = frames.b.findIndex((f) => f.beat === "shared");
    started = true;
    render(true, false, false);
    timer = setTimeout(tick, hold(frame(), null));
    paintControls();
  }

  load();
})();
