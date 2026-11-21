/* Escenario de la demo (tarea 15j): etiquetas legibles para hosts y secretos.
 *
 * Lee scenario.json (copia de demo/scenario.json junto a las páginas, para el sitio
 * estático; en local también prueba ../scenario.json). Si no carga, todo sigue
 * funcionando con los identificadores técnicos. Los registros nunca se modifican.
 */
"use strict";

let SCENARIO = null;

function setScenario(s) {
  SCENARIO = s && typeof s === "object" ? s : null;
}

/** Etiqueta del escenario para un host o un SECRET_n; si no existe, el mismo id. */
function label(id) {
  const s = SCENARIO || {};
  return (s.hosts && s.hosts[id]) || (s.secrets && s.secrets[id]) || id;
}

/** «<etiqueta> (<id>)» si hay etiqueta; si no, el id solo. */
function labelWithId(id) {
  const l = label(id);
  return l === id ? String(id) : `${l} (${id})`;
}

/** Nodo DOM: etiqueta y, en chico, el id técnico. */
function labelNode(id) {
  const span = document.createElement("span");
  const l = label(id);
  span.textContent = l;
  if (l !== id) {
    const small = document.createElement("small");
    small.className = "tech-id";
    small.textContent = ` (${id})`;
    span.appendChild(small);
  }
  return span;
}

function fillScenarioHeader() {
  if (typeof document === "undefined" || !SCENARIO) return;
  const put = (id, text) => { const el = document.getElementById(id); if (el && text) el.textContent = text; };
  put("scenario-org", SCENARIO.organization);
  put("scenario-system", SCENARIO.system);
  put("scenario-note", SCENARIO.fictional_note);
}

function loadScenario(urls = ["scenario.json", "../scenario.json"]) {
  const tryAt = (i) => {
    if (i >= urls.length) return Promise.resolve(null);
    return fetch(urls[i])
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .catch(() => tryAt(i + 1));
  };
  return tryAt(0).then((s) => { setScenario(s); fillScenarioHeader(); return SCENARIO; });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { label, labelWithId, setScenario };
}

// En el navegador: una sola carga; las páginas re-dibujan cuando termina.
var scenarioReady = (typeof window !== "undefined" && typeof fetch !== "undefined")
  ? loadScenario() : Promise.resolve(null);
