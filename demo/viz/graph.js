/* Grafo de archivos y camino de la decisión para la pantalla dividida (tarea 15e).
 *
 * Funciones puras (probadas con node): touchedUpTo, pathBoxes, resolveNode.
 * Dibujo (navegador, d3): GraphView y renderPath.
 */
"use strict";

/** Recursos tocados (tal como vienen en ToolCall.resources) por las llamadas con t <= t. */
function touchedUpTo(frames, t) {
  const out = new Set();
  for (const f of frames || []) {
    if (f.t > t) continue;
    for (const r of (f.call && f.call.resources) || []) out.add(r);
  }
  return out;
}

/** Cajas del camino de una decisión: [{id, tool, resource}] en el orden de decision.path. */
function pathBoxes(frames, decision) {
  const byId = new Map((frames || []).map((f) => [f.call.id, f.call]));
  return ((decision && decision.path) || []).map((id) => {
    const call = byId.get(id);
    return {
      id,
      tool: call ? call.tool : "?",
      resource: call && call.resources && call.resources.length ? call.resources[0] : "",
    };
  });
}

/** Nodo del grafo que corresponde a un recurso ('docs' -> 'docs/', '.' -> './'), o null. */
function resolveNode(nodeIds, resource) {
  if (resource == null) return null;
  const r = String(resource);
  if (r === "" || r === "." || r === "./") return nodeIds.has("./") ? "./" : null;
  if (nodeIds.has(r)) return r;
  const bare = r.replace(/\/+$/, "");
  if (nodeIds.has(bare + "/")) return bare + "/";
  if (nodeIds.has(bare)) return bare;
  return null;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { touchedUpTo, pathBoxes, resolveNode };
}

/* ------------------------------------------------------------------ dibujo */

if (typeof document !== "undefined") {
  /**
   * Dibuja el grafo una sola vez (disposición por fuerzas calculada de antemano,
   * no se mueve) y devuelve un objeto con update(nowSet, beforeSet).
   */
  function GraphView(el, graph) {
    el.innerHTML = "";
    const { width, height } = el.getBoundingClientRect();
    const W = Math.max(width, 300), H = Math.max(height, 160);
    const nodes = graph.nodes.map((n) => ({ ...n }));
    const ids = new Set(nodes.map((n) => n.id));
    const links = graph.edges.filter((e) => ids.has(e.source) && ids.has(e.target)).map((e) => ({ ...e }));

    const sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((d) => d.id).distance(34).strength(0.9))
      .force("charge", d3.forceManyBody().strength(-120))
      .force("x", d3.forceX(W / 2).strength(0.06))
      .force("y", d3.forceY(H / 2).strength(0.12))
      .force("collide", d3.forceCollide(12))
      .stop();
    // Semilla fija para que la disposición sea siempre la misma.
    nodes.forEach((n, i) => { n.x = W / 2 + 40 * Math.cos(i); n.y = H / 2 + 40 * Math.sin(i); });
    for (let i = 0; i < 400; i++) sim.tick();

    // Encajar en el recuadro.
    const pad = 18;
    const xs = d3.extent(nodes, (n) => n.x), ys = d3.extent(nodes, (n) => n.y);
    const sx = d3.scaleLinear().domain(xs[0] === xs[1] ? [xs[0] - 1, xs[1] + 1] : xs).range([pad, W - pad - 90]);
    const sy = d3.scaleLinear().domain(ys[0] === ys[1] ? [ys[0] - 1, ys[1] + 1] : ys).range([pad, H - pad]);

    const color = d3.interpolateRgb("#9aa3ae", "#d64545");
    const svg = d3.select(el).append("svg").attr("viewBox", `0 0 ${W} ${H}`);
    svg.append("g").attr("class", "g-links").selectAll("line").data(links).join("line")
      .attr("x1", (d) => sx(d.source.x)).attr("y1", (d) => sy(d.source.y))
      .attr("x2", (d) => sx(d.target.x)).attr("y2", (d) => sy(d.target.y));

    const g = svg.append("g").attr("class", "g-nodes").selectAll("g").data(nodes).join("g")
      .attr("transform", (d) => `translate(${sx(d.x)},${sy(d.y)})`);
    g.append("circle")
      .attr("r", (d) => (d.kind === "secret" ? 8 : d.kind === "host" ? 6 : 7))
      .style("fill", (d) => color(Math.max(0, Math.min(1, d.mu))))
      .attr("class", (d) => `node k-${d.kind}`);
    g.append("title").text((d) => `${typeof labelWithId === "function" ? labelWithId(d.id) : d.id}  μ=${d.mu.toFixed(2)}  (${d.kind})`);
    // Hosts y secretos con la etiqueta del escenario (scenario.js); archivos tal cual.
    // Los secretos llevan la etiqueta encima del nodo: a la derecha suelen tener un host
    // vecino (p. ej. SECRET_4 y hooks.empresa.test) y las etiquetas se montaban.
    const below = (d) => d.kind === "secret";
    const txt = g.append("text").attr("class", "node-label")
      .attr("x", (d) => (below(d) ? 0 : 10)).attr("y", (d) => (below(d) ? -12 : 4))
      .attr("text-anchor", (d) => (below(d) ? "middle" : "start"));
    // Etiquetas largas del escenario se acortan para no montarse sobre otros nodos;
    // el nombre completo queda en el tooltip (title).
    const short = (t) => (t.length > 22 ? `${t.slice(0, 21)}…` : t);
    txt.append("tspan").text((d) => short(typeof label === "function" ? label(d.id) : d.id));
    txt.filter((d) => typeof label === "function" && label(d.id) !== d.id)
      .append("tspan").attr("class", "tech-id").style("font-size", "8px").text((d) => ` (${d.id})`);

    // Leyenda de color.
    const lg = svg.append("g").attr("class", "g-legend").attr("transform", `translate(${W - 84},${H - 40})`);
    const grad = svg.append("defs").append("linearGradient").attr("id", "mu-grad");
    grad.append("stop").attr("offset", "0%").attr("stop-color", color(0));
    grad.append("stop").attr("offset", "100%").attr("stop-color", color(1));
    lg.append("rect").attr("width", 70).attr("height", 8).attr("fill", "url(#mu-grad)");
    lg.append("text").attr("y", 22).text("μ 0");
    lg.append("text").attr("x", 70).attr("y", 22).attr("text-anchor", "end").text("1");

    return {
      ids,
      update(now, before) {
        const nowN = new Set([...now].map((r) => resolveNode(ids, r)).filter(Boolean));
        const beforeN = new Set([...before].map((r) => resolveNode(ids, r)).filter(Boolean));
        g.classed("touched-now", (d) => nowN.has(d.id))
          .classed("touched-before", (d) => !nowN.has(d.id) && beforeN.has(d.id));
      },
    };
  }

  /** Cadena de cajas id · herramienta · recurso, unidas por flechas, y la razón debajo. */
  function renderPath(el, boxes, reason, action) {
    el.innerHTML = "";
    if (boxes.length) {
      const row = document.createElement("div");
      row.className = "path-row";
      boxes.forEach((b, i) => {
        if (i) {
          const arrow = document.createElement("span");
          arrow.className = "path-arrow";
          arrow.textContent = "→";
          row.appendChild(arrow);
        }
        const box = document.createElement("div");
        box.className = "path-box";
        const id = document.createElement("div"); id.className = "pb-id"; id.textContent = b.id;
        const tool = document.createElement("div"); tool.className = "pb-tool"; tool.textContent = b.tool;
        const res = document.createElement("div"); res.className = "pb-res"; res.textContent = b.resource || "—";
        box.append(id, tool, res);
        row.appendChild(box);
      });
      el.appendChild(row);
    }
    const p = document.createElement("p");
    p.className = "path-reason";
    if (action) {
      const tag = document.createElement("span");
      tag.className = `action ${actionClass(action)}`;
      tag.textContent = action;
      p.appendChild(tag);
    }
    p.appendChild(document.createTextNode(reason || "—"));
    el.appendChild(p);
  }

  window.GraphView = GraphView;
  window.renderPath = renderPath;
}
