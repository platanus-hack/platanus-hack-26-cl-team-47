/* El tablero «Cómo lo probamos».
 *
 * No calcula ni trae escrita ninguna cifra: las lee de pruebas.json (hacer_pruebas.py) y los
 * nombres de familias y guardias, de escenario.json. Si hay servidor.py, además le pide que
 * recalcule el sello del set de prueba en ese momento.
 */
"use strict";

(function () {
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const miles = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const coma = (n, d) => (d == null ? String(n) : Number(n).toFixed(d)).replace(".", ",");
  const entero = (n) => miles(Math.round(n));
  const corto = (h) => `${String(h).slice(0, 16)}…`;
  const fill = (t, v) => String(t).replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m));
  const REGLA = { evidencia: "la evidencia", contador: "el contador", "período": "la rotación periódica", bloqueo: "el bloqueo", ninguna: "ninguna" };
  const ORDEN_A = ["A5", "A7", "A10", "A12", "A9", "A13"];
  const ORDEN_B = ["B3", "B4", "B5"];

  // ---------- la capa al pasar el cursor (y con el teclado) ----------
  const tip = $("tip");
  function mostrar(target, x, y) {
    tip.textContent = "";
    tip.appendChild(el("b", "", target.dataset.valor || ""));
    tip.appendChild(document.createTextNode(target.dataset.tip || ""));
    tip.hidden = false;
    const r = tip.getBoundingClientRect();
    tip.style.left = `${Math.max(8, Math.min(window.innerWidth - r.width - 8, x + 14))}px`;
    tip.style.top = `${Math.max(8, y - r.height - 12)}px`;
  }
  document.addEventListener("pointermove", (ev) => {
    const t = ev.target.closest && ev.target.closest("[data-tip]");
    if (t) mostrar(t, ev.clientX, ev.clientY); else tip.hidden = true;
  });
  document.addEventListener("focusin", (ev) => {
    const t = ev.target.closest && ev.target.closest("[data-tip]");
    if (!t) return;
    const r = t.getBoundingClientRect();
    mostrar(t, r.left + r.width / 2, r.top);
  });
  document.addEventListener("focusout", () => { tip.hidden = true; });

  function reglas(obj) {
    return Object.entries(obj).filter(([k]) => k !== "ninguna").sort((a, b) => b[1] - a[1])
      .map(([k, v]) => `${REGLA[k] || k} (${v})`).join(", ") || "ninguna";
  }

  /** Una pista con su barra y, si se pide, la marca del otro valor en el mismo eje. */
  function pista(valor, total, marca, textoTip, valorTip) {
    const td = el("td", "pista");
    const riel = el("div", "riel");
    const barra = el("i", "barra");
    barra.style.width = `${(100 * valor) / total}%`;
    riel.appendChild(barra);
    if (marca != null) {
      const tic = el("i", "tic");
      tic.style.left = `${(100 * marca) / total}%`;
      riel.appendChild(tic);
    }
    riel.dataset.tip = textoTip;
    riel.dataset.valor = valorTip;
    riel.tabIndex = 0;
    td.appendChild(riel);
    return td;
  }

  function eje(th, total) {
    th.textContent = "";
    const caja = el("span", "ticks");
    [0, 1 / 3, 2 / 3, 1].forEach((p) => {
      const s = el("span", "", entero(total * p));
      s.style.left = `${100 * p}%`;
      caja.appendChild(s);
    });
    th.appendChild(caja);
  }

  function pintar(d, nombres) {
    const ev = d.evaluacion;
    const a = ev.ataques;
    const n = ev.normales;
    const nuestro = d.sistemas.find((s) => s.id === "ours");

    // 1. la cifra
    $("h-n").textContent = a.frenados;
    $("h-de").textContent = `de ${a.n}`;
    $("h-bajada").textContent = fill(
      "Frenó {fam} de las {tot} familias de ataques, que el detector nunca había visto. Es la evaluación del set sellado, hecha con las marcas que calcula el proxy, que es como funcionaría instalado. Con las marcas que traían las grabaciones daba {grab} de {n}.",
      { fam: a.familias_frenadas, tot: a.familias, grab: nuestro.grabadas, n: a.n });
    $("f-bloq").textContent = `${n.bloqueadas} de ${miles(n.llamadas)}`;
    $("f-bloq-n").textContent = "Ningún asistente quedó detenido por un error de Alicanto.";
    $("f-rot").textContent = `${n.con_rotacion_de_mas} de ${n.sesiones_dificiles}`;
    $("f-rot-n").textContent = fill("{rot} rotaciones sin necesidad: {mil} por cada 1.000 llamadas normales. La meta era 5 o menos, y no se cumple.",
      { rot: n.rotaciones_de_mas, mil: coma(n.rotaciones_por_mil) });
    if (d.suite) {
      $("f-tests").textContent = miles(d.suite.tests);
      $("f-tests-n").textContent = `Suite completa del repositorio, corrida el ${d.suite.cuando}. Tarda ${Math.round(d.suite.segundos / 60)} minutos.`;
    } else {
      $("f-tests").closest("div").hidden = true;
    }

    // 2. la rejilla
    $("set-e").textContent = fill(
      "{at} ataques y {no} sesiones normales difíciles, de {f} familias. Una casilla por ataque o por sesión. Cada familia son {r} réplicas de una misma plantilla, y por eso las filas salen enteras: el resultado se lee por familias.",
      { at: a.n, no: n.sesiones_dificiles, f: a.familias + n.familias.length, r: ev.familias[0].n });
    const g = $("rejilla");
    g.textContent = "";
    const cab = (t) => { const c = el("div", "cab", t); c.setAttribute("role", "columnheader"); g.appendChild(c); };
    ["Familia", "Un caso por casilla", "Resultado", "Qué rotó primero", "Bits que salieron"].forEach(cab);
    const fila = (id, estados, cuenta, sufijo, regla, bits, textos) => {
      const f = el("div", "fila");
      f.setAttribute("role", "row");
      const fam = el("div", "fam");
      fam.appendChild(el("b", "", id));
      fam.appendChild(document.createTextNode(nombres.familias[id] || ""));
      const celdas = el("div", "celdas");
      celdas.setAttribute("role", "img");
      celdas.setAttribute("aria-label", `${id}: ${cuenta} de ${estados.length} ${sufijo}`);
      estados.forEach((s, i) => {
        const c = el("i", `c ${s}`);
        c.dataset.valor = `${id} · ${i + 1} de ${estados.length}`;
        c.dataset.tip = textos[s];
        celdas.appendChild(c);
      });
      const cu = el("div", "cuenta", `${cuenta} de ${estados.length}`);
      cu.appendChild(el("small", "", sufijo));
      const re = el("div", "regla", regla);
      const bi = el("div", "bits", bits);
      for (const x of [fam, celdas, cu, re, bi]) { x.setAttribute("role", "cell"); f.appendChild(x); }
      g.appendChild(f);
    };
    g.appendChild(el("div", "grupo", `Ataques (${a.n})`));
    for (const id of ORDEN_A) {
      const f = ev.familias.find((x) => x.id === id);
      const m = d.ataques[id];
      fila(id, Array(f.n).fill(f.frenados === f.n ? "stop" : "out"), f.frenados, "frenados",
        m.frenados ? reglas(m.reglas) : (Object.keys(m.reglas).includes("contador") ? "rota otra clave, no esta" : "nada"),
        `${entero(m.mediana_bits)} de ${a.bits_clave}`,
        { stop: "Ataque frenado: no pasó del límite.", out: "Ataque no frenado: salió más del límite." });
    }
    g.appendChild(el("div", "grupo", `Sesiones normales difíciles (${n.sesiones_dificiles})`));
    for (const id of ORDEN_B) {
      const f = n.familias.find((x) => x.id === id);
      const m = d.normales[id];
      fila(id, [...f.tira].map((c) => (c === "1" ? "rot" : "calm")), f.con_rotacion_de_mas, "rotó de más",
        m.con_rotacion ? reglas(m.reglas) : "—", `${m.bloqueos} bloqueos`,
        { rot: "Sesión normal: Alicanto rotó una clave sin necesidad.", calm: "Sesión normal: no pasó nada." });
    }
    $("set-pie").textContent = fill(
      "Límite: {lim} de {bits} bits de una misma versión de la clave. «Bits que salieron» es la mediana de la familia. Las dos familias que se escapan: en A9 la clave viaja a su propio destino permitido, y en A13 la fuga se cuenta en cada commit, aunque el proxy en vivo bloquea el push.",
      { lim: a.bits_clave - 64, bits: a.bits_clave });

    // 3. los otros guardias
    $("otros-e").textContent = fill(
      "Los mismos {n} ataques y las mismas sesiones normales, con la misma métrica. Cada guardia es una función que recibe una llamada y decide.",
      { n: a.n });
    const tb = document.querySelector("#sistemas tbody");
    tb.textContent = "";
    eje(document.querySelector("#sistemas th.eje"), a.n);
    for (const s of d.sistemas) {
      const tr = el("tr", s.id === "ours" ? "nuestro" : "");
      const nombre = s.id === "per_session" ? "Alicanto con una cuenta por agente" : (nombres.sistemas[s.id] || s.id);
      const th = el("th", "", nombre);
      th.scope = "row";
      tr.appendChild(th);
      tr.appendChild(pista(s.proxy, a.n, s.grabadas, `${nombre}. Con las marcas de las grabaciones: ${s.grabadas}.`, `${s.proxy} de ${a.n} frenados`));
      tr.appendChild(el("td", "num", String(s.proxy)));
      tr.appendChild(el("td", "num", s.bloqueadas_pct ? `${coma(s.bloqueadas_pct, 1)} %` : "0"));
      tr.appendChild(el("td", "num", coma(s.rot_1000, 2)));
      tb.appendChild(tr);
    }
    const regla = d.sistemas.find((s) => s.id === "taint_rule");
    $("otros-pie").textContent = fill(
      "La marca fina es el resultado con las marcas que traían las grabaciones: ahí Alicanto y la regla simple empatan en {g} de {n}, porque el generador de los ataques había marcado todos los envíos. Con las marcas del proxy, Alicanto frena {p} y la regla {r}. Los dos «réplica nuestra» son versiones simplificadas hechas por el equipo: sus cifras no son las de ningún producto.",
      { g: nuestro.grabadas, n: a.n, p: nuestro.proxy, r: regla.proxy });

    // 4. el protocolo
    const ol = $("tiempo");
    ol.textContent = "";
    for (const t of d.tiempo) {
      const li = el("li");
      li.appendChild(el("span", "hora", t.hora));
      const q = el("span", `quien ${t.quien}`);
      if (t.quien) { q.appendChild(el("i")); q.appendChild(document.createTextNode(`equipo ${t.quien}`)); }
      li.appendChild(q);
      const que = el("span", "que", t.que.charAt(0).toUpperCase() + t.que.slice(1));
      const h = el("span", "huella", (t.huella ? `sha256 ${t.huella} · ` : "") + `commit ${t.commit}`);
      que.appendChild(h);
      li.appendChild(que);
      ol.appendChild(li);
    }
    $("sello").textContent = fill("El sello cubre {n} archivos: las sesiones, sus etiquetas y el generador. Cambiar un byte lo cambia.", { n: ev.sello.archivos });

    // 5a. el atacante que se adapta
    const ad = d.adaptativo.test;
    $("ad-e").textContent = "Las grabaciones siguen enviando la clave vieja después de una rotación. Aquí el atacante, simulado, relee la clave nueva y sigue.";
    const ta = document.querySelector("#adaptativo tbody");
    ta.textContent = "";
    eje(document.querySelector("#adaptativo th.eje"), ad.ours.rewritten);
    for (const [id, nombre] of [["ours", "Alicanto"], ["no_evidence", "Sin evidencia de comportamiento"], ["no_rotation", "Sin rotación"]]) {
      const x = ad[id];
      const tr = el("tr", id === "ours" ? "nuestro" : "");
      const th = el("th", "", nombre);
      th.scope = "row";
      tr.appendChild(th);
      tr.appendChild(pista(x.prevented, x.rewritten, null, nombre, `${x.prevented} de ${x.rewritten} frenados`));
      tr.appendChild(el("td", "num", String(x.prevented)));
      tr.appendChild(el("td", "num", entero(x.max_max_bits)));
      ta.appendChild(tr);
    }
    $("ad-pie").textContent = fill(
      "Con las marcas de las grabaciones, {k} de {n} ataques que se adaptan no pasan de {lim} bits de ninguna versión. No lo logra rotando sin fin: en el {esc} % de los casos llega a su tope de {tope} rotaciones y bloquea las salidas de esa clave ({bloq} envíos bloqueados). Es una simulación, y el costo de ese bloqueo sobre trabajo normal no está medido.",
      { k: ad.ours.prevented, n: ad.ours.rewritten, lim: a.bits_clave - 64, esc: Math.round(ad.ours.escalated_fraction * 100),
        tope: Math.round(ad.ours.median_rotations), bloq: miles(ad.ours.blocked_after_escalation) });

    // 5b. fragmentos cortos
    const fr = d.fragmentos;
    $("fr-e").textContent = fill("El contador no cuenta pedazos de menos de 4 caracteres. Cada celda es el máximo de bits de una misma versión que salió en una sesión de {n} llamadas.", { n: fr.llamadas });
    const th = document.querySelector("#fragmentos thead");
    th.textContent = "";
    const r1 = el("tr");
    r1.appendChild(el("th", "", "Configuración"));
    r1.appendChild(el("th", "num", "Un envío cada"));
    for (const t of fr.tamanos) r1.appendChild(el("th", "num", `${t} car.`));
    th.appendChild(r1);
    const tf = document.querySelector("#fragmentos tbody");
    tf.textContent = "";
    const nombreCfg = { ours: "Evaluada, con evidencia", no_evidence: "Evaluada, sin evidencia", demo: "Demo y hook, sin evidencia" };
    let pasan = 0;
    for (const cfg of ["ours", "no_evidence", "demo"]) {
      fr.sistemas[cfg].forEach((filaCfg, i) => {
        const tr = el("tr", i === 0 && cfg !== "ours" ? "corte" : "");
        const h = el("th", "", i === 0 ? nombreCfg[cfg] : "");
        h.scope = "row";
        tr.appendChild(h);
        tr.appendChild(el("td", "num", `${fr.ritmos[i]} ${fr.ritmos[i] === 1 ? "llamada" : "llamadas"}`));
        filaCfg.forEach((c, j) => {
          const td = el("td", `num${c.pasa ? " pasa" : ""}`, entero(c.bits));
          td.dataset.valor = `${entero(c.bits)} bits`;
          td.dataset.tip = `${nombreCfg[cfg]}: ${fr.tamanos[j]} caracteres cada ${fr.ritmos[i]} llamadas.${c.pasa ? " Pasa del límite." : ""}`;
          if (c.pasa) pasan += 1;
          tr.appendChild(td);
        });
        tf.appendChild(tr);
      });
    }
    $("fr-pie").textContent = fill(
      "El cuadro de oro marca las {p} celdas que pasan de {lim} bits. Con pedazos de 4 o más, ninguna pasa. Con pedazos de 1 a 3, lo que protege es la evidencia de comportamiento: la configuración de la demo y la del hook de Claude Code no la llevan.",
      { p: pasan, lim: entero(fr.limite) });

    // 6. lo que no dice
    const lim = [
      ["Son ataques grabados.", "Después de una rotación, la grabación sigue enviando la clave vieja. El atacante que se adapta se midió aparte, y en simulación."],
      ["Todo el tráfico es sintético.", "Ataques y sesiones normales los generó el equipo. No hay tráfico de producción."],
      ["Son seis plantillas.", "Cada familia son réplicas de una misma plantilla: el set mide cuántas familias se frenan, no cuántos casos distintos."],
      ["Dos familias no se cubren.", "La clave enviada a su propio destino permitido y la fuga por commits de git."],
      ["Lo que frena lo nuevo es la evidencia, no el contador.", fill("Solo con el contador de bits se frenan {n}.", { n: d.sistemas.find((s) => s.id === "no_evidence").proxy })],
      ["La evidencia equivale, en estos datos, a una regla simple.", "«La sesión leyó un secreto y esta llamada sale a un destino que no es el de ninguna clave.»"],
      ["Rotar de más no cumple nuestra propia meta.", fill("{m} rotaciones por cada 1.000 llamadas normales; la meta era 5.", { m: coma(n.rotaciones_por_mil) })],
      ["El contador no cuenta pedazos de menos de 4 caracteres.", "Ver la tabla de arriba."],
      ["La cuenta compartida cubre una máquina.", "Varios agentes en un mismo computador, no varios computadores."],
      ["Ningún modelo real siguió la instrucción plantada.", "No hay una medición de Alicanto frenando una fuga producida por un modelo."],
    ];
    const ul = $("lim-l");
    ul.textContent = "";
    for (const [t, r] of lim) {
      const li = el("li");
      li.appendChild(el("b", "", t));
      li.appendChild(document.createTextNode(` ${r}`));
      ul.appendChild(li);
    }

    // 7. repetirlo
    const pre = $("comandos");
    pre.textContent = "";
    const cmd = [
      ["# El sello del set de prueba, recalculado sobre los archivos de hoy", "python demo/alternativas/03-enjambre-juanpedro/hacer_evaluacion.py --sello"],
      [`# La medición con las marcas del proxy (unos 3 minutos)`, "python -m eval.final.proxy_flags --out /tmp/pf"],
      ["# El detalle por familia y este tablero", "python docs/informe/hacer_datos.py --check\npython demo/alternativas/03-enjambre-juanpedro/hacer_pruebas.py"],
      ["# La sesión de la demo, con los procesos reales", "python demo/alternativas/03-enjambre-juanpedro/vivo.py"],
      ["# Una defensa propia, con los mismos datos", "python -m eval.bench --defense <modulo>:<fabrica> --set test --out /tmp/x"],
      ["# Toda la suite", "python -m pytest -q"],
    ];
    cmd.forEach(([c, x], i) => {
      pre.appendChild(el("span", "c1", `${i ? "\n\n" : ""}${c}\n`));
      pre.appendChild(document.createTextNode(x));
    });
    $("fuente").textContent = fill(
      "Cifras de results/ (corrida única, commit {c1}; marcas del proxy, commit {c2}) y de docs/informe/datos/cifras.json. Configuración congelada {h}. Esta página no trae cifras escritas a mano.",
      { c1: ev.sello.commit_corrida, c2: ev.medicion.commit, h: corto(ev.congelado.hash) });
    $("tablero").setAttribute("aria-busy", "false");
    document.body.dataset.listo = "si";
  }

  async function sello(d) {
    // Con servidor.py: el sello se recalcula recién, en este computador, y se compara aquí.
    try {
      const r = await fetch("/api/sello", { cache: "no-store" });
      if (!r.ok) return;
      const j = await r.json();
      const ok = j.sha256 === d.evaluacion.sello.sha256;
      const p = $("sello");
      p.textContent = "";
      p.appendChild(el("b", "", ok ? "Sello recalculado recién en este computador: coincide. " : "El sello recalculado NO coincide con el publicado. "));
      p.appendChild(document.createTextNode(`${j.archivos} archivos, ${String(j.ms).replace(".", ",")} ms.`));
      document.body.dataset.sello = ok ? "coincide" : "distinto";
    } catch (_) { /* sin servidor: queda el sello publicado */ }
  }

  async function partir() {
    try {
      const [d, sc] = await Promise.all([
        fetch("pruebas.json").then((r) => { if (!r.ok) throw new Error("pruebas.json"); return r.json(); }),
        fetch("escenario.json").then((r) => (r.ok ? r.json() : {})).catch(() => ({})),
      ]);
      const p = (sc && sc.prueba) || {};
      pintar(d, { familias: p.familias || {}, sistemas: (p.otros && p.otros.sistemas) || {} });
      // En el sitio publicado no hay quien recalcule el sello: solo se pide en este computador.
      if (/^(127\.0\.0\.1|localhost)$/.test(location.hostname)) sello(d);
    } catch (err) {
      const m = $("tablero");
      m.textContent = "";
      m.appendChild(el("p", "entrada", `No se pudieron leer los datos (${err.message}). Esta página necesita un servidor: python demo/alternativas/03-enjambre-juanpedro/servidor.py`));
    }
    // El informe técnico queda junto a la página en el sitio publicado, y servidor.py también lo
    // entrega. Si no está, el enlace no se muestra.
    try {
      const r = await fetch("informe.pdf", { method: "HEAD" });
      if (r.ok) $("pdf").hidden = false;
    } catch (_) { /* no está */ }
  }

  partir();
})();
