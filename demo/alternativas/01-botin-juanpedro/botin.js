/* Alternativa 01, «El botín»: la misma corrida real de la demo oficial, vista desde el servidor
 * del atacante. No calcula nada por su cuenta: todo lo que muestra sale de las grabaciones
 * (demo/viz/fixtures/real_left.jsonl y real_right.jsonl), salvo la ficha de ejemplo, que es
 * una maqueta y lo dice en pantalla.
 *
 * Parámetros: ?disfraz=base64|reversed (el mismo ataque con los fragmentos disfrazados),
 * ?left=<jsonl>&right=<jsonl>&enc=auto|none|base64|reversed (otras grabaciones del mismo formato),
 * ?secret=SECRET_n, ?t=<n>|end (abre en ese paso, para capturas), ?speed=1|2|4, ?autoplay=1.
 * Teclas: espacio (reproducir o pausar), flechas (un paso), R (volver al inicio).
 */
"use strict";

const Q = new URLSearchParams(typeof location !== "undefined" ? location.search : "");
// ?disfraz=base64|reversed abre la grabación real de ese disfraz (las de la demo «el público elige»).
const DISFRAZ = { base64: "enc_base64", reversed: "enc_reversed" }[Q.get("disfraz")] || "real";
const SOURCES = {
  left: Q.get("left") || `../../viz/fixtures/${DISFRAZ}_left.jsonl`,
  right: Q.get("right") || `../../viz/fixtures/${DISFRAZ}_right.jsonl`,
};
const SCENARIO_URL = "../../viz/scenario.json";
const SECRET = Q.get("secret") || "SECRET_1";
// Cómo lee el atacante cada fragmento: auto, none, base64 o reversed.
const ENC = Q.get("enc") || (Q.get("disfraz") === "reversed" ? "reversed" : "auto");
const ATTACKER_HOST = "attacker.test";
const STEP_MS = 420; // duración de una llamada a 1×
const ROTATION_HOLD_MS = 1600; // pausa en el momento de la rotación
const CASH_STEPS = 2; // después de la última llamada: el atacante escribe el comando y ve la respuesta

/* Maqueta: la API del banco de pruebas responde solo {"ok": true}. Esta ficha es texto de
 * ejemplo para mostrar qué abre la clave; no sale de ninguna corrida. */
const FICHA_EJEMPLO = {
  nombre: "Rosa Fuentes Araya",
  linea1: "58 años · Diabetes tipo 2 · Hipertensión",
  linea2: "Próxima hora: control con cardiología",
};

// ---------- lectura de las grabaciones (funciones puras) ----------

/** El fragmento que salió hacia el atacante en esta llamada, o null. */
function fragmentOf(call) {
  const url = call.args && call.args.url;
  if (!url || !/allow$/.test(call.action)) return null; // una llamada bloqueada no entrega nada
  let u;
  try { u = new URL(url); } catch (_) { return null; }
  if (u.hostname !== ATTACKER_HOST) return null;
  return u.searchParams.get("d") || null;
}

/** Lo que el atacante lee de un fragmento disfrazado. «auto» reconoce base64; «al revés» hay
 * que pedirlo con ?enc=reversed, porque no se distingue de un fragmento tal cual. */
function decodeFragment(raw, enc) {
  if (enc === "reversed") return raw.split("").reverse().join("");
  if (enc === "base64" || (enc === "auto" && !/^[0-9a-f]+$/i.test(raw))) {
    try {
      const d = atob(raw);
      if (/^[\x20-\x7e]+$/.test(d)) return d;
    } catch (_) { /* no era base64: se muestra tal cual */ }
  }
  return raw;
}

/** Texto de una grabación (JSONL de eventos) → llamadas ordenadas, rotación y cobro final. */
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
        id: d.id, t: d.t, tool: d.tool, args: d.args || {}, output: d.output || "",
        untrusted: !!d.untrusted, action: "allow", bits: 0, frag: null,
      };
      calls.push(c);
      byId[c.id] = c;
    } else if (e.kind === "decision" && byId[e.call_id]) {
      const c = byId[e.call_id];
      c.action = d.action || "allow";
      c.bits = ((d.leak || {})[secretId] || {}).bits || 0;
    } else if (e.kind === "rotation" && d.secret_id === secretId && !rotation && byId[e.call_id]) {
      rotation = { t: byId[e.call_id].t, version: d.version };
    } else if (e.source === "attacker" && e.kind === "received") {
      cash = d;
    }
  }
  calls.sort((a, b) => a.t - b.t);
  const chars = [];
  for (const c of calls) {
    c.frag = fragmentOf(c);
    c.plain = c.frag ? decodeFragment(c.frag, enc || "auto") : null;
    if (c.plain) for (const ch of c.plain) chars.push({ ch, t: c.t });
  }
  return { calls, rotation, cash, chars };
}

/** Estado de un lado en el paso T (T = 0 es antes de la primera llamada). */
function stateAt(rec, T) {
  const n = rec.calls.length;
  const upto = Math.min(T, n);
  const current = upto > 0 ? rec.calls[upto - 1] : null;
  let maxBits = 0;
  for (let i = 0; i < upto; i++) maxBits = Math.max(maxBits, rec.calls[i].bits);
  return {
    current,
    bits: current ? current.bits : 0,
    maxBits,
    rotated: !!rec.rotation && T >= rec.rotation.t,
    shown: rec.chars.filter((c) => c.t <= T).length,
    cashPhase: Math.max(0, T - n), // 0: aún no; 1: escribe el comando; 2: respuesta
  };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { fragmentOf, decodeFragment, parseRecording, stateAt };
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

  const sides = {};
  let scenario = {};
  let total = 0; // llamadas
  let T = 0;
  let timer = null;
  let speed = Number(Q.get("speed")) || 1;
  let started = false;
  let keyLen = 0;
  let totalBits = 0;
  let group = 4;

  const label = (id) => (scenario.hosts && scenario.hosts[id]) || (scenario.secrets && scenario.secrets[id]) || id;

  function fail(msg) {
    const box = el("section", "needs-server");
    box.setAttribute("role", "alert");
    box.textContent = msg;
    document.querySelector(".bar").insertAdjacentElement("afterend", box);
  }

  async function load() {
    if (location.protocol === "file:") {
      fail("Esta página necesita un servidor. Desde la raíz del repositorio: python -m http.server 8300 --directory demo, y abre http://127.0.0.1:8300/alternativas/01-botin-juanpedro/botin.html");
      return;
    }
    try {
      const [l, r, s] = await Promise.all([
        fetch(SOURCES.left).then((x) => { if (!x.ok) throw new Error(SOURCES.left); return x.text(); }),
        fetch(SOURCES.right).then((x) => { if (!x.ok) throw new Error(SOURCES.right); return x.text(); }),
        fetch(SCENARIO_URL).then((x) => (x.ok ? x.json() : {})).catch(() => ({})),
      ]);
      scenario = s || {};
      sides.left = { rec: parseRecording(l, SECRET, ENC), root: $("left") };
      sides.right = { rec: parseRecording(r, SECRET, ENC), root: $("right") };
    } catch (err) {
      fail("No se pudo leer la grabación: " + err.message);
      return;
    }
    build();
    const t0 = Q.get("t");
    T = t0 === "end" ? total + CASH_STEPS : Math.max(0, Math.min(total + CASH_STEPS, Number(t0) || 0));
    if (T > 0) started = true;
    render();
    if (Q.get("autoplay") === "1") play();
  }

  function build() {
    const L = sides.left.rec;
    total = Math.max(L.calls.length, sides.right.rec.calls.length);
    // Largo y bits de la clave: del cobro del atacante si la completó; si no, de lo que salió.
    const c = L.cash || {};
    keyLen = c.key_complete && c.positions_known ? c.positions_known : Math.max(L.chars.length, sides.right.rec.chars.length);
    totalBits = c.bits_known && c.positions_known ? Math.round((c.bits_known / c.positions_known) * keyLen) : keyLen * 4;
    const firstFrag = L.calls.find((x) => x.frag);
    group = firstFrag ? firstFrag.plain.length : 4;

    if (scenario.organization) {
      $("scenario").textContent = `${scenario.organization} · ficticio`;
    }

    // El issue plantado: la primera salida no confiable que nombra al servidor del atacante.
    const planted = L.calls.find((x) => x.untrusted && x.output.includes(ATTACKER_HOST));
    const issue = $("issue-text");
    if (planted) {
      for (const part of planted.output.split(/(?<=\.)\s+/)) {
        const hot = part.includes(ATTACKER_HOST) || /asistente/i.test(part);
        issue.appendChild(el(hot ? "mark" : "span", null, part + " "));
      }
    } else {
      issue.textContent = "(esta grabación no trae un texto plantado)";
    }

    const dots = $("dots");
    for (let i = 0; i < total; i++) dots.appendChild(el("i"));

    for (const s of Object.values(sides)) {
      const key = s.root.querySelector(".key");
      s.spans = [];
      for (let i = 0; i < keyLen; i++) {
        if (i % group === 0) s.groupEl = key.appendChild(el("span", "grp"));
        const sp = el("span", "ch", "·");
        sp.style.setProperty("--i", i);
        s.groupEl.appendChild(sp);
        s.spans.push(sp);
      }
      s.root.querySelector(".of").textContent = `de ${totalBits} bits de la clave vigente, en manos del atacante`;
    }

    $("play").addEventListener("click", toggle);
    $("restart").addEventListener("click", restart);
    for (const b of document.querySelectorAll(".speed")) {
      b.addEventListener("click", () => { speed = Number(b.dataset.speed); render(); if (timer) { pause(); play(); } });
    }
    document.addEventListener("keydown", (ev) => {
      if (ev.target.tagName === "BUTTON" && ev.code === "Space") return; // el botón ya lo maneja
      if (ev.code === "Space") { ev.preventDefault(); toggle(); }
      else if (ev.code === "ArrowRight") { pause(); go(T + 1); }
      else if (ev.code === "ArrowLeft") { pause(); go(T - 1); }
      else if (ev.key === "r" || ev.key === "R") restart();
    });
  }

  // ---------- reloj ----------

  function go(t) {
    const before = T;
    T = Math.max(0, Math.min(total + CASH_STEPS, t));
    if (T > 0) started = true;
    // La ceniza se anima solo si se llega a la rotación avanzando un paso (no al saltar con ?t=).
    for (const s of Object.values(sides)) {
      const rot = s.rec.rotation;
      const live = !!rot && T === rot.t && before === T - 1;
      if (live) s.root.classList.add("crumbling");
      else if (!rot || T < rot.t) s.root.classList.remove("crumbling");
    }
    render();
  }
  function tick() {
    if (T >= total + CASH_STEPS) { pause(); return; }
    go(T + 1);
    const rot = sides.right.rec.rotation;
    let wait = STEP_MS / speed;
    if (rot && T === rot.t) wait = ROTATION_HOLD_MS; // el momento de la rotación se sostiene
    else if (T >= total) wait = 1100; // el cobro: comando y respuesta, con aire
    timer = setTimeout(tick, wait);
  }
  function play() {
    if (timer) return;
    if (T >= total + CASH_STEPS) T = 0;
    started = true;
    timer = setTimeout(tick, 60);
    render();
  }
  function pause() { clearTimeout(timer); timer = null; render(); }
  function toggle() { timer ? pause() : play(); }
  function restart() { pause(); started = false; go(0); }

  // ---------- dibujo ----------

  function shortKey(chars) {
    const k = chars.map((c) => c.ch).join("");
    return k.length > 14 ? `${k.slice(0, 8)}…${k.slice(-4)}` : k;
  }

  function renderSide(name) {
    const s = sides[name];
    const rec = s.rec;
    const st = stateAt(rec, T);
    const root = s.root;
    root.classList.toggle("rotated", st.rotated);
    root.classList.toggle("rotating", !!rec.rotation && T === rec.rotation.t);
    const complete = st.shown >= keyLen && keyLen > 0;
    root.classList.toggle("complete", complete && !st.rotated);

    for (let i = 0; i < keyLen; i++) {
      const sp = s.spans[i];
      const item = rec.chars[i];
      const shown = !!item && item.t <= T;
      sp.textContent = shown ? item.ch : "·";
      sp.classList.toggle("on", shown);
      sp.classList.toggle("new", shown && item.t === T);
      sp.classList.toggle("dead", shown && st.rotated);
      sp.classList.toggle("born-dead", shown && st.rotated && item.t > rec.rotation.t);
    }

    // En la llamada que dispara la rotación, la decisión grabada trae los bits medidos justo
    // antes de rotar; de la clave nueva no ha salido nada (así lo dice la decisión siguiente).
    const atRotation = st.rotated && st.current && st.current.t === rec.rotation.t;
    const bitsNow = atRotation ? 0 : st.bits;
    root.querySelector(".bits").textContent = String(Math.round(bitsNow));

    const banner = root.querySelector(".banner");
    if (st.rotated) {
      banner.textContent = `Clave rotada en la llamada ${rec.rotation.t}. Lo que juntó ya no sirve.`;
    } else if (complete) {
      banner.textContent = `Clave completa: ${Math.round(bitsNow)} de ${totalBits} bits.`;
    } else {
      banner.textContent = "";
    }

    const feed = root.querySelector(".feed");
    feed.textContent = "";
    if (st.cashPhase === 0) {
      const got = rec.calls.filter((c) => c.frag && c.t <= T).slice(-3);
      if (!got.length) feed.appendChild(el("p", "log dim", "$ esperando fragmentos…"));
      for (const c of got) {
        const p = el("p", "log" + (c.t === T ? " fresh" : ""));
        p.appendChild(el("span", "dim", `llamada ${c.t}  `));
        p.appendChild(document.createTextNode(`GET /c?d=${c.frag}`));
        feed.appendChild(p);
      }
      return;
    }
    const cash = rec.cash || {};
    const host = "api.empresa.test";
    const cmd = el("p", "log cmd");
    cmd.appendChild(el("span", "dim", "$ "));
    cmd.appendChild(document.createTextNode(
      `curl -H "Authorization: Bearer ${shortKey(rec.chars)}" ${host}${cash.path || "/v1/data"}`));
    feed.appendChild(cmd);
    if (st.cashPhase < 2 || cash.status == null) return;

    const ok = cash.status === 200;
    const res = el("div", "result " + (ok ? "in" : "out"));
    res.appendChild(el("b", "code", String(cash.status)));
    const txt = el("div", "restext");
    if (ok) {
      txt.appendChild(el("strong", null, `Entró a la ${label(host)}.`));
      const f = el("div", "ficha");
      f.appendChild(el("span", "mock", "Ficha de ejemplo, ficticia"));
      f.appendChild(el("b", null, FICHA_EJEMPLO.nombre));
      f.appendChild(el("span", null, FICHA_EJEMPLO.linea1));
      f.appendChild(el("span", null, FICHA_EJEMPLO.linea2));
      txt.appendChild(f);
    } else {
      txt.appendChild(el("strong", null, "Manos vacías."));
      txt.appendChild(el("span", null,
        `Juntó ${rec.chars.length} caracteres de una clave que dejó de servir` +
        (rec.rotation ? ` en la llamada ${rec.rotation.t}.` : ".")));
    }
    res.appendChild(txt);
    feed.appendChild(res);
  }

  function render() {
    if (!sides.left) return;
    renderSide("left");
    renderSide("right");

    const R = sides.right.rec;
    const upto = Math.min(T, total);
    const cur = upto > 0 ? R.calls[upto - 1] : null;
    $("clock").textContent = `llamada ${upto} / ${total}`;
    $("play").textContent = timer ? "⏸" : "▶";
    $("hint").hidden = started;
    for (const b of document.querySelectorAll(".speed")) b.classList.toggle("active", Number(b.dataset.speed) === speed);

    const dots = $("dots").children;
    for (let i = 0; i < dots.length; i++) {
      dots[i].classList.toggle("done", i < upto);
      dots[i].classList.toggle("now", i === upto - 1);
    }
    const blocked = R.calls.slice(0, upto).filter((c) => /block/.test(c.action)).length;
    const ticker = $("ticker-text");
    if (!cur) {
      ticker.textContent = "El agente todavía no empieza a trabajar.";
    } else {
      const arg = cur.args.path || cur.args.url || (cur.args.args ? cur.args.args.join(" ") : "");
      const verdict = /block/.test(cur.action) ? "Bloqueada"
        : /rotate/.test(cur.action) ? "Permitida, y Alicanto rotó la clave" : "Permitida";
      ticker.textContent = `Llamada ${cur.t}: ${cur.tool} ${arg}. ${verdict}. ` +
        `Van ${upto} llamadas, ${blocked} bloqueadas.`;
    }

    const head = $("headline");
    if (T >= total + CASH_STEPS) {
      const max = stateAt(R, total).maxBits;
      head.textContent = R.rotation
        ? `El mismo ataque, las mismas ${total} llamadas, ${blocked} bloqueadas. ` +
          `Con Alicanto, el atacante nunca tuvo más de ${Math.round(max)} de ${totalBits} bits de la clave vigente.`
        : `El mismo ataque, las mismas ${total} llamadas.`;
    } else {
      head.textContent = `${scenario.fictional_note || "Todo es ficticio."} La ficha clínica que aparece al final es un texto de ejemplo.`;
    }
    head.classList.toggle("note", T < total + CASH_STEPS);
  }

  load();
})();
