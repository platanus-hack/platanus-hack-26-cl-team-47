/* Informe de incidente por secreto (tarea 15i). Lee report.json de demo/incident_report.py. */
"use strict";

const DEFAULT_REPORT = "fixtures/real_report.json";

/** Función pura: marcas de la línea de tiempo de un secreto, con posición 0..1 según t. */
function timelineMarks(secret) {
  const marks = [];
  if (secret.exposed_at) marks.push({ kind: "exposed", t: secret.exposed_at.t, label: `exposición t${secret.exposed_at.t}` });
  for (const c of secret.leak_calls || []) marks.push({ kind: "leak", t: c.t, label: `t${c.t}` });
  for (const r of secret.rotations || []) marks.push({ kind: "rotation", t: r.t, label: `rotación t${r.t}` });
  for (const b of secret.blocked_calls || []) marks.push({ kind: "blocked", t: b.t, label: `bloqueo t${b.t}` });
  const maxT = Math.max(1, ...marks.map((m) => m.t || 0));
  return marks.map((m) => ({ ...m, x: (m.t || 0) / maxT }));
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { timelineMarks, DEFAULT_REPORT };
}

if (typeof document !== "undefined" && document.getElementById("secrets")) {
  const el = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  };

  const lbl = (id) => (typeof labelWithId === "function" ? labelWithId(id) : id);

  function renderSecret(s) {
    const box = el("section", "secret");
    const h2 = el("h2");
    h2.append(typeof labelNode === "function" ? labelNode(s.secret_id) : document.createTextNode(s.secret_id));
    box.append(h2, el("p", "statement", s.statement));

    box.append(el("div", "legend", "● exposición  ● envío con bits  ● rotación  ● bloqueo"));
    const tl = el("div", "timeline");
    for (const m of timelineMarks(s)) {
      const mk = el("div", `mark ${m.kind}`);
      mk.style.left = `${(m.x * 96 + 2).toFixed(1)}%`;
      mk.append(el("span", "dot"));
      if (m.kind !== "leak") mk.append(el("span", "lbl", m.label));
      mk.title = m.label;
      tl.append(mk);
    }
    box.append(tl);

    const table = el("table");
    const head = el("tr");
    for (const h of ["Llamada", "t", "Herramienta", "Destino", "Bits después", "Decisión"]) head.append(el("th", null, h));
    table.append(head);
    for (const c of s.leak_calls || []) {
      const tr = el("tr");
      for (const v of [c.call_id, c.t, c.tool, c.destination ? lbl(c.destination) : "—", c.bits_after, c.action]) tr.append(el("td", null, String(v)));
      table.append(tr);
    }
    box.append(table);

    const lines = [`Destinos: ${(s.destinations || []).map(lbl).join(", ") || "—"}`];
    if (s.exposed_at) lines.push(`Expuesto en la llamada ${s.exposed_at.t} (${s.exposed_at.tool} ${s.exposed_at.resource || ""})`);
    for (const r of s.rotations || []) lines.push(`Rotación en la llamada ${r.t}, versión ${r.version}: ${r.reason}`);
    if (s.final_status != null) lines.push(`Intento final del atacante con la clave: ${s.final_status}`);
    for (const l of lines) box.append(el("p", "final", l));
    return box;
  }

  const params = new URLSearchParams(location.search);
  const url = params.get("report") || DEFAULT_REPORT;
  const ready = typeof scenarioReady !== "undefined" ? scenarioReady : Promise.resolve(null);
  ready.then(() => fetch(url))
    .then((r) => { if (!r.ok) throw new Error(`${url}: ${r.status}`); return r.json(); })
    .then((rep) => {
      document.getElementById("meta").textContent =
        `Sesión ${rep.session_id} · generado desde ${rep.generated_from || "—"}`;
      const main = document.getElementById("secrets");
      if (!rep.secrets.length) main.append(el("p", null, "Sin fugas medidas ni rotaciones."));
      for (const s of rep.secrets) main.append(renderSecret(s));
    })
    .catch((err) => { document.getElementById("meta").textContent = `No se pudo cargar el informe: ${err.message}`; });
}
