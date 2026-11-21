/* Página de resultados (16f, #180): lee fixtures/results.json, copia de results/test, results/proxy_flags y results/adaptive. */
"use strict";

const SOURCE = "fixtures/results.json";

/** Una frase por sistema; las réplicas se marcan como réplicas. */
const SYSTEMS = {
  ours: ["Alicanto", "La configuración congelada: cuenta de bits por clave, evidencia de comportamiento y rotación."],
  no_rotation: ["Sin rotación (ablación)", "Alicanto con la rotación apagada; los bloqueos siguen."],
  per_session: ["Cuenta por sesión (ablación)", "Alicanto sin la cuenta compartida entre sesiones."],
  no_evidence: ["Sin modelo de evidencia (ablación)", "Solo el contador de bits y las reglas."],
  allowlist: ["Lista de destinos", "Línea de base: solo deja salir a dominios aprobados."],
  detect_secrets: ["detect-secrets", "Línea de base: expresiones regulares y entropía sobre cada envío."],
  combined: ["Lista de destinos + detect-secrets", "Línea de base: bloquea si cualquiera de las dos bloquea."],
  budget: ["Presupuesto de bits (réplica)", "Réplica simplificada nuestra de un presupuesto acumulado por sesión; no es el producto."],
  reassembly: ["Reensamblado por sesión (réplica)", "Réplica simplificada nuestra, inspirada en Pipelock y AgentBrake; no es su código."],
  taint_rule: ["Regla simple", "Línea de base: «leyó un secreto y esta llamada sale hacia un destino no confiable»: rota lo leído; nunca bloquea."],
};

function pct(x, nd = 1) {
  return x == null ? "—" : `${(x * 100).toFixed(nd).replace(".", ",")} %`;
}

function ci(c, nd = 1) {
  return c ? `[${pct(c[0], nd)}, ${pct(c[1], nd)}]` : "";
}

function stopped(r) {
  if (!r || r.prevented_rate == null) return "—";
  const n = r.n_attack_units;
  const head = n ? `${Math.round(r.prevented_rate * n)} de ${n}` : pct(r.prevented_rate);
  return `${head} ${ci(r.prevented_ci)}`;
}

/** Función pura: filas de la tabla de sistemas. Con proxyFlags (copia de results/proxy_flags/systems.json),
 *  una fila por sistema de la variante «grabadas» (incluye la regla simple) y, al lado, la variante «proxy». */
function systemRows(systems, proxyFlags) {
  const recorded = (proxyFlags && proxyFlags.grabadas) || systems || [];
  const live = {};
  for (const r of (proxyFlags && proxyFlags.proxy) || []) live[r.system] = r;
  return recorded.map((r) => {
    const [name, what] = SYSTEMS[r.system] || [r.system, ""];
    return {
      system: r.system, name, what,
      proxy: stopped(live[r.system]),
      prevented: stopped(r),
      falseAlarms: `${pct(r.false_alarm_rate, 2)} ${ci(r.false_alarm_ci, 2)}`,
      rotations: r.benign_rotations_per_1000 == null ? "—" : r.benign_rotations_per_1000.toFixed(2).replace(".", ","),
      bits: r.median_max_bits_true == null ? "—" : String(Math.round(r.median_max_bits_true)),
    };
  });
}

/** Función pura: filas del atacante adaptativo (set de prueba). */
function adaptiveRows(adaptive) {
  const test = (adaptive || {}).test || {};
  return Object.entries(test).map(([system, a]) => {
    const o = a.overall || {};
    return {
      system, name: (SYSTEMS[system] || [system])[0],
      prevented: `${o.prevented} de ${o.rewritten}`,
      maxBits: o.max_max_bits == null ? "—" : String(Math.round(o.max_max_bits)),
      escalated: pct(o.escalated_fraction, 0),
    };
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { SYSTEMS, SOURCE, systemRows, adaptiveRows, pct, stopped };
}

/* ------------------------------------------------------------------ página */

if (typeof document !== "undefined" && document.getElementById("systems-table")) {
  const cell = (tr, text, cls) => {
    const td = document.createElement("td");
    td.textContent = text;
    if (cls) td.className = cls;
    tr.appendChild(td);
    return td;
  };

  fetch(SOURCE).then((r) => {
    if (!r.ok) throw new Error(`${SOURCE}: ${r.status}`);
    return r.json();
  }).then((data) => {
    const body = document.querySelector("#systems-table tbody");
    for (const row of systemRows(data.systems, data.proxy_flags)) {
      const tr = document.createElement("tr");
      if (row.system === "ours") tr.className = "ours";
      const th = document.createElement("th");
      th.innerHTML = `<span class="sys-name"></span><span class="sys-what"></span>`;
      th.children[0].textContent = row.name;
      th.children[1].textContent = row.what;
      tr.appendChild(th);
      cell(tr, row.proxy);
      cell(tr, row.prevented);
      cell(tr, row.falseAlarms);
      cell(tr, row.rotations);
      cell(tr, row.bits);
      body.appendChild(tr);
    }

    const t = (data.report || {}).tests || {};
    const holm = (data.report || {}).holm || {};
    const verdict = (k) => (holm[k] ? (holm[k].reject ? "rechaza H₀" : "no rechaza H₀") : "sin dato");
    document.getElementById("tests-line").textContent =
      `Pruebas con corrección de Holm, con las marcas de las grabaciones: T1, falsas alarmas: ${verdict("T1")}; T2, ataques prevenidos: ${verdict("T2")}; ` +
      `T3, contra lista de destinos + detect-secrets (${t.T3 ? `${t.T3.b} contra ${t.T3.c}` : "—"}): ${verdict("T3")}; ` +
      `T4, efecto de la rotación: ${verdict("T4")}. T5 y T6 no se calcularon.`;

    const ab = document.querySelector("#adaptive-table tbody");
    for (const row of adaptiveRows(data.adaptive)) {
      const tr = document.createElement("tr");
      if (row.system === "ours") tr.className = "ours";
      const th = document.createElement("th");
      th.textContent = row.name;
      tr.appendChild(th);
      cell(tr, row.prevented);
      cell(tr, row.maxBits);
      cell(tr, row.escalated);
      ab.appendChild(tr);
    }

    const run = data.run || {};
    const dl = document.getElementById("hashes");
    for (const [k, v] of [
      ["Sello del set de prueba (sha256)", data.seal],
      ["Configuración congelada (hash de frozen.json)", run.frozen_hash],
      ["Parámetros", run.params ? Object.entries(run.params).map(([a, b]) => `${a} ${b}`).join(", ") : "—"],
      ["Modelo (sha256)", run.model_sha256],
      ["Commit de la corrida", run.commit],
      ["Unidades evaluadas", run.n_units != null ? `${run.n_units} (${run.n_sessions} sesiones)` : "—"],
    ]) {
      const dt = document.createElement("dt"); dt.textContent = k;
      const dd = document.createElement("dd"); dd.textContent = v || "—";
      dl.append(dt, dd);
    }
  }).catch((err) => {
    document.querySelector("#systems-table tbody").innerHTML = "";
    document.getElementById("tests-line").textContent = `No se pudieron cargar los resultados: ${err.message}`;
  });
}
