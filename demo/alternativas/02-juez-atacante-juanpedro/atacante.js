/* Alternativa 02, «El juez es el atacante»: una página para el teléfono de alguien del jurado.
 * Recibe los fragmentos de la clave como los recibió el servidor del atacante en la corrida
 * real grabada, y es esa persona quien pulsa «Usar la clave».
 *
 * Hay dos hospitales y la página no dice cuál tiene Alicanto: el atacante tampoco lo sabe.
 *   ?h=1  grabación sin protección (demo/viz/fixtures/real_left.jsonl)
 *   ?h=2  grabación con Alicanto   (demo/viz/fixtures/real_right.jsonl)
 * Otros parámetros: ?ritmo=<ms por fragmento> (por defecto 1100), ?t=end (clave completa),
 * ?t=cobro (ya cobrado, para capturas), ?src=<jsonl> (otra grabación del mismo formato).
 *
 * No calcula nada: todo sale de la grabación, salvo la ficha de ejemplo, que es una maqueta
 * y lo dice en pantalla.
 */
"use strict";

const Q = new URLSearchParams(typeof location !== "undefined" ? location.search : "");
const H = Q.get("h") === "2" ? "2" : "1";
const SRC = Q.get("src") || `../../viz/fixtures/${H === "2" ? "real_right" : "real_left"}.jsonl`;
const SCENARIO_URL = "../../viz/scenario.json";
const SECRET = "SECRET_1";
const ATTACKER_HOST = "attacker.test";
const API_HOST = "api.empresa.test";
const PACE_MS = Math.max(150, Number(Q.get("ritmo")) || 1100);

/* Maqueta: la API del banco de pruebas responde solo {"ok": true}. */
const FICHA_EJEMPLO = {
  nombre: "Rosa Fuentes Araya",
  linea1: "58 años · Diabetes tipo 2 · Hipertensión",
  linea2: "Próxima hora: control con cardiología",
};

// ---------- lectura de la grabación (funciones puras) ----------

/** Grabación (JSONL de eventos) → fragmentos que salieron, rotación, cobro y texto plantado. */
function parseRecording(text, secretId) {
  const calls = [];
  const byId = {};
  let rotation = null;
  let cash = null;
  for (const line of text.split("\n")) {
    if (!line.trim()) continue;
    const e = JSON.parse(line);
    const d = e.data || {};
    if (e.kind === "tool_call") {
      const c = { id: d.id, t: d.t, args: d.args || {}, output: d.output || "", untrusted: !!d.untrusted, action: "allow" };
      calls.push(c);
      byId[c.id] = c;
    } else if (e.kind === "decision" && byId[e.call_id]) {
      byId[e.call_id].action = d.action || "allow";
    } else if (e.kind === "rotation" && d.secret_id === secretId && !rotation && byId[e.call_id]) {
      rotation = { t: byId[e.call_id].t, version: d.version };
    } else if (e.source === "attacker" && e.kind === "received") {
      cash = d;
    }
  }
  calls.sort((a, b) => a.t - b.t);
  const frags = [];
  for (const c of calls) {
    const url = c.args.url;
    if (!url || !/allow$/.test(c.action)) continue; // una llamada bloqueada no entrega nada
    let u;
    try { u = new URL(url); } catch (_) { continue; }
    if (u.hostname === ATTACKER_HOST && u.searchParams.get("d")) frags.push({ t: c.t, text: u.searchParams.get("d") });
  }
  const planted = calls.find((c) => c.untrusted && c.output.includes(ATTACKER_HOST));
  return { total: calls.length, frags, rotation, cash, planted: planted ? planted.output : "" };
}

/** Cuántos caracteres tenía el atacante cuando la clave rotó (los fragmentos hasta esa llamada). */
function charsAtRotation(rec) {
  if (!rec.rotation) return null;
  return rec.frags.filter((f) => f.t <= rec.rotation.t).reduce((n, f) => n + f.text.length, 0);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { parseRecording, charsAtRotation };
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
  const app = $("app");
  let rec = null;
  let scenario = {};
  let got = 0; // fragmentos recibidos
  let timer = null;
  let keyLen = 0;
  let spans = [];

  const label = (id) => (scenario.hosts && scenario.hosts[id]) || id;
  const show = (screen) => { app.dataset.screen = screen; };

  function fail(msg) {
    app.textContent = "";
    const p = el("p", "error", msg);
    p.setAttribute("role", "alert");
    app.appendChild(p);
  }

  async function load() {
    if (location.protocol === "file:") {
      fail("Esta página necesita un servidor. Desde la raíz del repositorio: python -m http.server 8300 --directory demo, y abre /alternativas/02-juez-atacante-juanpedro/atacante.html");
      return;
    }
    try {
      const [text, s] = await Promise.all([
        fetch(SRC).then((x) => { if (!x.ok) throw new Error(SRC); return x.text(); }),
        fetch(SCENARIO_URL).then((x) => (x.ok ? x.json() : {})).catch(() => ({})),
      ]);
      rec = parseRecording(text, SECRET);
      scenario = s || {};
    } catch (err) {
      fail("No se pudo leer la grabación: " + err.message);
      return;
    }
    build();
    const t = Q.get("t");
    if (t === "end" || t === "cobro") { got = rec.frags.length; show("listen"); renderKey(); }
    if (t === "cobro") cashOut();
  }

  function build() {
    keyLen = rec.frags.reduce((n, f) => n + f.text.length, 0);
    const group = rec.frags.length ? rec.frags[0].text.length : 4;
    $("world").textContent = `Hospital ${H}`;
    $("issue").textContent = rec.planted || "(esta grabación no trae un texto plantado)";
    $("fictional").textContent = `${scenario.fictional_note || "Todo es ficticio."} Lo que vas a ver es una corrida real grabada.`;
    const key = $("key");
    let grp = null;
    for (let i = 0; i < keyLen; i++) {
      if (i % group === 0) grp = key.appendChild(el("span", "grp"));
      spans.push(grp.appendChild(el("span", "ch", "·")));
    }
    $("start").addEventListener("click", start);
    $("use").addEventListener("click", cashOut);
    renderKey();
  }

  function start() {
    got = 0;
    $("inbox").textContent = "";
    show("listen");
    renderKey();
    clearTimeout(timer);
    timer = setTimeout(next, 700);
  }

  function next() {
    if (got >= rec.frags.length) return;
    const f = rec.frags[got];
    got += 1;
    const row = el("p", "msg");
    row.appendChild(el("span", "dim", `llamada ${f.t}`));
    row.appendChild(el("code", null, `GET /c?d=${f.text}`));
    $("inbox").prepend(row);
    if (navigator.vibrate) navigator.vibrate(35);
    renderKey(true);
    if (got < rec.frags.length) timer = setTimeout(next, PACE_MS);
  }

  function renderKey(fresh) {
    let shown = 0;
    let i = 0;
    for (let k = 0; k < rec.frags.length; k++) {
      for (const ch of rec.frags[k].text) {
        const on = k < got;
        spans[i].textContent = on ? ch : "·";
        spans[i].classList.toggle("on", on);
        spans[i].classList.toggle("new", !!fresh && k === got - 1);
        if (on) shown += 1;
        i += 1;
      }
    }
    $("count").textContent = `${shown} de ${keyLen} caracteres`;
    const last = got > 0 ? rec.frags[got - 1].t : 0;
    $("agent").textContent = got === 0
      ? "El agente del hospital está trabajando. Todavía no te manda nada."
      : `El agente del hospital lleva ${got < rec.frags.length ? last : rec.total} llamadas. Nadie lo ha detenido.`;
    const use = $("use");
    const complete = keyLen > 0 && shown >= keyLen;
    use.disabled = !complete;
    use.textContent = complete ? "Usar la clave" : "Esperando la clave completa…";
  }

  function cashOut() {
    clearTimeout(timer);
    const cash = rec.cash || {};
    const key = rec.frags.map((f) => f.text).join("");
    const short = key.length > 14 ? `${key.slice(0, 8)}…${key.slice(-4)}` : key;
    const box = $("result");
    box.textContent = "";
    const ok = cash.status === 200;
    box.classList.toggle("in", ok);
    box.classList.toggle("out", !ok);

    box.appendChild(el("p", "cmd", `$ curl -H "Authorization: Bearer ${short}" ${API_HOST}${cash.path || "/v1/data"}`));
    box.appendChild(el("b", "code", cash.status != null ? String(cash.status) : "?"));
    if (ok) {
      box.appendChild(el("h2", null, `Entraste a la ${label(API_HOST)}.`));
      const f = el("div", "ficha");
      f.appendChild(el("span", "mock", "Ficha de ejemplo, ficticia"));
      f.appendChild(el("b", null, FICHA_EJEMPLO.nombre));
      f.appendChild(el("span", null, FICHA_EJEMPLO.linea1));
      f.appendChild(el("span", null, FICHA_EJEMPLO.linea2));
      box.appendChild(f);
      box.appendChild(el("p", "why", "Este hospital no tenía Alicanto. Nadie notó nada: cada llamada, por separado, parecía normal."));
    } else {
      box.appendChild(el("h2", null, "Manos vacías."));
      const at = charsAtRotation(rec);
      box.appendChild(el("p", "why", rec.rotation
        ? `Este hospital tenía Alicanto. La clave cambió en la llamada ${rec.rotation.t}, cuando tenías ${at} de ${keyLen} caracteres. Seguiste juntando pedazos de una clave que ya no existía.`
        : "La clave que juntaste no sirve."));
    }
    const again = el("button", "again", "Volver a intentarlo");
    again.type = "button";
    again.addEventListener("click", () => { got = 0; show("intro"); renderKey(); });
    box.appendChild(again);
    show("result");
  }

  load();
})();
