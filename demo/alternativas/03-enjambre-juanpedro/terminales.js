/* La escena con terminales debajo.
 *
 * Arriba va enjambre.html tal cual, en un marco. Esta página no dibuja la escena ni decide nada:
 * mira en qué llamada va (data-world y data-t del <body> de la escena) y pide que esa llamada se
 * ejecute de verdad.
 *
 *   En vivo      con servidor.py. /api/vivo/abrir levanta como procesos el gestor de secretos, la
 *                API, el servidor del atacante y el GitHub simulado, y arma un proxy real por
 *                asistente. Cada vez que la escena avanza, /api/vivo/paso ejecuta las llamadas
 *                que faltan hasta esa y devuelve las líneas de cada terminal. Lo de abajo ocurre
 *                en ese momento. El servidor compara cada decisión con la de la escena.
 *   Grabación    sin servidor (por ejemplo, en la web). Las terminales muestran la grabación de
 *                una corrida real (grabaciones/terminales.json, hecha con vivo.py --grabar),
 *                al paso de la escena. La barra lo dice.
 *
 * Si el público elige otro reparto en el pitch, la escena deja sus valores en data-params y las
 * terminales corren ese mismo reparto.
 */
"use strict";

(function () {
  const $ = (id) => document.getElementById(id);
  const marco = $("escena");
  const PANES = ["proxy", "gestor", "atacante"];
  const TITULO_PROXY = { a: "Proxy · un monitor por asistente", b: "Proxy · Alicanto, una cuenta por clave" };
  const MAX_LINEAS = 240;
  const NIVELES = 3; // hasta dónde se abrevia una terminal angosta (ver terminales.css)
  // La escena está hecha para un proyector. Con la franja debajo le queda una ventana más baja:
  // se dibuja a ese ancho y se achica entera, en vez de dejar que se corte.
  const ANCHO_BAJA = 1920; // en una ventana baja (la que deja la franja) la escena cabe desde este ancho
  const ANCHO_16_9 = 1280; // en una ventana de 16:9 o más alta, desde este
  const FORMATO_MAX = 2.58; // lo más apaisada que la escena cabe entera (1920 × 745)
  const TELEFONO = "(max-width: 899px) and (orientation: portrait)"; // el mismo corte que terminales.css
  const GRABACION = "grabaciones/terminales.json";

  let modo = ""; // "vivo" o "grabacion"
  let motivo = ""; // por qué no hay vivo, si el servidor lo dijo
  let grab = null; // la grabación, cuando hace falta
  let corrida = null; // { clave, mundo, params, id, hecho, lista, resumen }
  let turno = 0; // para descartar respuestas de una apertura que ya se reemplazó
  let pidiendo = false;
  let quiere = 0; // hasta qué llamada va la escena
  let quitadas = []; // cuándo otra ventana le quitó la corrida a esta

  // ---------- la escena ----------

  function escena() {
    const doc = marco.contentDocument;
    const b = doc && doc.body;
    if (!b || !b.dataset.world) return null;
    let params = null;
    try { params = b.dataset.params ? JSON.parse(b.dataset.params) : null; } catch (_) { params = null; }
    if (params) params = { semilla: params.semilla, reparten: params.reparten, disfraz: params.disfraz };
    return { mundo: b.dataset.world === "b" ? "b" : "a", T: Number(b.dataset.t) || 0, params };
  }

  function alCambiar() {
    const e = escena();
    if (!e) return;
    // Con alguien explicando (el pitch) la escena va con poco texto, y la barra tampoco lleva su frase.
    document.body.dataset.texto = marco.contentDocument.body.dataset.texto || "todo";
    const clave = e.mundo + "|" + JSON.stringify(e.params);
    // Otra corrida si cambió el mundo, si el público eligió otro reparto o si la escena volvió atrás.
    if (!corrida || corrida.clave !== clave || e.T < corrida.hecho) abrir(e.mundo, e.params, clave);
    quiere = e.T;
    avanzar();
  }

  function enganchar() {
    const doc = marco.contentDocument;
    if (!doc || !doc.body) return;
    new MutationObserver(alCambiar).observe(doc.body, {
      attributes: true,
      attributeFilter: ["data-world", "data-t", "data-params", "data-texto"],
    });
    try { marco.contentWindow.focus(); } catch (_) { /* sin foco no pasa nada */ }
    alCambiar();
  }

  function encajar() {
    const caja = $("lienzo");
    const A = caja.clientWidth;
    const B = caja.clientHeight;
    if (!A || !B) return;
    const ancho = Math.min(A, Math.round(B * FORMATO_MAX)); // si la ventana es muy apaisada, la escena va al centro
    const s = Math.min(1, ancho / (ancho / B <= 1.8 ? ANCHO_16_9 : ANCHO_BAJA));
    const x = Math.round((A - ancho) / 2);
    marco.style.width = `${Math.round(ancho / s)}px`;
    marco.style.height = `${Math.round(B / s)}px`;
    marco.style.transform = s === 1 && !x ? "none" : `translate(${x}px, 0) scale(${s})`;
    document.body.dataset.escala = s.toFixed(3);
  }

  // ---------- las terminales ----------

  function salida(pane) { return document.querySelector(`#t-${pane} .salida`); }

  function medidor(pane) { return document.querySelector(`#t-${pane} .medir`); }

  function limpiar() {
    for (const p of PANES) {
      salida(p).textContent = "";
      medidor(p).textContent = "";
      $("t-" + p).dataset.nivel = "0";
    }
  }

  function hacerLinea(l) {
    const li = document.createElement("li");
    li.className = l.clase || "normal";
    li.dataset.t = String(l.t);
    for (const [texto, clase] of l.partes) {
      if (!texto) continue;
      const s = document.createElement("span");
      if (clase) s.className = clase;
      s.textContent = texto;
      li.appendChild(s);
    }
    return li;
  }

  const seCorta = (li) => li.scrollWidth > li.clientWidth + 1;

  /** Elige en cada terminal el primer nivel de abreviación en que ninguna línea esperada se corta. */
  function nivelar() {
    const telefono = matchMedia(TELEFONO).matches; // ahí las líneas se doblan: se abrevia todo lo que se puede
    for (const p of PANES) {
      const term = $("t-" + p);
      const filas = [...medidor(p).children];
      let n = telefono ? NIVELES : 0;
      term.dataset.nivel = String(n);
      while (n < NIVELES && filas.some(seCorta)) term.dataset.nivel = String(++n);
    }
  }

  /** Las líneas que se esperan de la corrida. No se ven: sirven para elegir el nivel antes de partir. */
  function medir(lineas) {
    for (const p of PANES) medidor(p).textContent = "";
    for (const l of lineas || []) {
      const ol = medidor(l.pane);
      if (ol) ol.appendChild(hacerLinea(l));
    }
    nivelar();
  }

  function pintar(lineas) {
    let sube = false;
    for (const l of lineas || []) {
      const ol = salida(l.pane);
      if (!ol) continue;
      ol.appendChild(hacerLinea(l));
      while (ol.childElementCount > MAX_LINEAS) ol.removeChild(ol.firstElementChild);
      // Si la realidad salió más ancha que lo esperado, esa línea también cuenta para el nivel.
      const copia = medidor(l.pane).appendChild(hacerLinea(l));
      if (seCorta(copia)) sube = true;
      else copia.remove();
    }
    if (sube) nivelar();
    enteras();
  }

  /** Solo líneas enteras: las que no caben arriba se esconden, en vez de quedar cortadas por la mitad. */
  function enteras() {
    for (const p of PANES) {
      const ol = salida(p);
      const filas = [...ol.children];
      if (!filas.length) continue;
      for (const li of filas) li.hidden = false;
      const estilo = getComputedStyle(ol);
      let libre = ol.clientHeight - parseFloat(estilo.paddingTop) - parseFloat(estilo.paddingBottom);
      const altos = filas.map((li) => li.getBoundingClientRect().height); // en un teléfono hay líneas dobladas
      let desde = filas.length - 1; // la última se muestra siempre
      libre -= altos[desde];
      while (desde > 0 && libre - altos[desde - 1] >= -0.5) libre -= altos[--desde];
      for (let i = 0; i < desde; i++) filas[i].hidden = true;
    }
  }

  function fecha(iso) {
    // Tal como la anotó quien grabó (hora de Santiago), no en la zona horaria de quien mira.
    const m = /^\d{4}-(\d\d)-(\d\d)T(\d\d):(\d\d)/.exec(iso || "");
    if (!m) return "";
    const mes = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"][Number(m[1]) - 1];
    return `${Number(m[2])} ${mes}, ${m[3]}:${m[4]}`;
  }

  function pintarBarra() {
    document.body.dataset.modo = modo;
    const m = $("modo");
    const i = $("igual");
    const r = corrida && corrida.resumen;
    $("que").textContent = modo === "grabacion"
      ? "Abajo no hay dibujo: es lo que escribieron los procesos en una corrida real, al paso de la escena."
      : "Abajo no hay dibujo: cada línea es una llamada que el proxy acaba de decidir.";
    if (modo === "vivo") {
      m.textContent = "En vivo · procesos de este computador";
      if (r && r.hecho > 0) {
        const mal = r.difieren && r.difieren.length;
        i.textContent = mal
          ? `difiere de la escena en la llamada ${r.difieren[0]}`
          : `${r.coinciden} de ${r.hecho} decisiones iguales a las de la escena`;
        i.classList.toggle("difiere", !!mal);
      } else {
        i.textContent = "";
      }
    } else if (modo === "grabacion") {
      const cuando = grab ? fecha(grab.fecha) : "";
      m.textContent = "Grabación de una corrida real" + (cuando ? ` · ${cuando}` : "") + (motivo ? ` · ${motivo}` : "");
      const g = grab && corrida && grab.mundos[corrida.mundo];
      i.textContent = g ? `grabada con ${g.resumen.coinciden} de ${g.resumen.n} decisiones iguales a las de la escena` : "";
      i.classList.remove("difiere");
    } else {
      m.textContent = "";
      i.textContent = "";
    }
    document.body.dataset.mundo = corrida ? corrida.mundo : "";
    document.body.dataset.hecho = corrida ? String(corrida.hecho) : "0";
    document.body.dataset.cobro = r && r.cobro != null ? String(r.cobro) : "";
  }

  function procesos(p) {
    // En vivo, el puerto y el pid de cada proceso. En la grabación, solo el nombre del servidor.
    const texto = (nombre, host) => {
      const x = p && p[nombre];
      return x ? `:${x.puerto} · pid ${x.pid}` : host;
    };
    document.querySelector("#t-proxy .proc").textContent = p && p.proxy ? `pid ${p.proxy.pid}` : "";
    document.querySelector("#t-gestor .proc").textContent = texto("vault", "vault.test");
    document.querySelector("#t-atacante .proc").textContent = texto("attacker", "attacker.test");
  }

  // ---------- pedir ----------

  async function json(url, ms) {
    const ctl = new AbortController();
    const corte = setTimeout(() => ctl.abort(), ms);
    try {
      const r = await fetch(url, { signal: ctl.signal, cache: "no-store" });
      let cuerpo = null;
      try { cuerpo = await r.json(); } catch (_) { cuerpo = null; }
      return { ok: r.ok, estado: r.status, cuerpo };
    } catch (_) {
      return { ok: false, estado: 0, cuerpo: null };
    } finally {
      clearTimeout(corte);
    }
  }

  async function cargarGrabacion() {
    if (grab) return grab;
    const r = await json(GRABACION, 8000);
    grab = r.ok && r.cuerpo && r.cuerpo.mundos ? r.cuerpo : { mundos: {}, fecha: "" };
    return grab;
  }

  async function abrir(mundo, params, clave) {
    const yo = ++turno;
    corrida = { clave, mundo, params, id: null, hecho: 0, lista: false, resumen: null };
    limpiar();
    document.querySelector("#t-proxy .nombre").textContent = TITULO_PROXY[mundo];
    pintarBarra();

    if (modo !== "grabacion") {
      const q = new URLSearchParams({ mundo });
      if (params) for (const k of ["semilla", "reparten", "disfraz"]) q.set(k, String(params[k]));
      const r = await json(`/api/vivo/abrir?${q}`, 15000);
      if (yo !== turno) return;
      if (r.ok && r.cuerpo && r.cuerpo.corrida) {
        modo = "vivo";
        motivo = "";
        corrida.id = r.cuerpo.corrida;
        corrida.resumen = r.cuerpo;
        corrida.lista = true;
        procesos(r.cuerpo.procesos);
        medir(r.cuerpo.moldes);
        pintar(r.cuerpo.lineas);
        pintarBarra();
        avanzar();
        return;
      }
      // 503: hay servidor, pero no pudo levantar los procesos (casi siempre un puerto ocupado).
      modo = "grabacion";
      motivo = r.estado === 503 ? "no se pudieron levantar los procesos" : "";
    }
    await cargarGrabacion();
    if (yo !== turno) return;
    procesos(null);
    corrida.lista = true;
    const g = grab.mundos[mundo];
    medir(g ? g.lineas : []);
    pintar(g ? g.lineas.filter((l) => l.t === 0) : []);
    pintarBarra();
    avanzar();
  }

  async function avanzar() {
    const c = corrida;
    if (!c || !c.lista || quiere <= c.hecho) return;
    if (modo === "grabacion") {
      const g = grab && grab.mundos[c.mundo];
      const hasta = quiere;
      if (g) {
        pintar(g.lineas.filter((l) => l.t > c.hecho && l.t <= hasta));
        if (hasta >= g.resumen.n + 2) c.resumen = g.resumen;
      }
      c.hecho = hasta;
      pintarBarra();
      return;
    }
    if (pidiendo) return;
    pidiendo = true;
    const hasta = quiere;
    const r = await json(`/api/vivo/paso?corrida=${encodeURIComponent(c.id)}&t=${hasta}`, 10000);
    pidiendo = false;
    if (c !== corrida) { avanzar(); return; } // mientras tanto se abrió otra corrida
    if (r.ok && r.cuerpo) {
      pintar(r.cuerpo.lineas);
      c.hecho = Math.max(c.hecho, hasta);
      c.resumen = r.cuerpo;
      pintarBarra();
      if (quiere > c.hecho) avanzar();
      return;
    }
    if (r.estado === 410) {
      // El servidor ya tiene otra corrida: la abrió otra ventana. Esta recupera la suya, pero si se la
      // quitan varias veces seguidas deja de insistir (dos ventanas se pelearían sin fin) y sigue con la grabación.
      const ahora = Date.now();
      quitadas = quitadas.filter((x) => ahora - x < 20000).concat(ahora);
      if (quitadas.length <= 2) { abrir(c.mundo, c.params, c.clave); return; }
      modo = "grabacion";
      motivo = "otra ventana está usando los procesos";
      await cargarGrabacion();
      pintarBarra();
      avanzar();
      return;
    }
    // Se perdió el servidor a mitad de camino: sigue la grabación desde donde iba.
    modo = "grabacion";
    motivo = "se perdió el servidor";
    await cargarGrabacion();
    pintarBarra();
    avanzar();
  }

  // ---------- teclas y foco: las teclas son de la escena ----------

  document.addEventListener("keydown", (ev) => {
    const doc = marco.contentDocument;
    if (!doc || ev.metaKey || ev.ctrlKey || ev.altKey) return;
    doc.dispatchEvent(new KeyboardEvent("keydown", { key: ev.key, code: ev.code, bubbles: true, cancelable: true }));
    if (ev.key === " " || ev.key.startsWith("Arrow")) ev.preventDefault();
  });
  $("franja").addEventListener("click", () => { try { marco.contentWindow.focus(); } catch (_) { /* nada */ } });
  window.addEventListener("resize", () => { encajar(); nivelar(); enteras(); });

  // ---------- partir ----------

  window.__terminales = {
    estado: () => ({ modo, motivo, corrida, quiere, niveles: PANES.map((p) => Number($("t-" + p).dataset.nivel)) }),
  };
  encajar();
  marco.addEventListener("load", enganchar);
  // En el sitio publicado la escena parte sola, salvo que la dirección pida algo que la escena
  // entiende: quien llega no tiene por qué saber qué tecla pulsar. Los parámetros que no son suyos
  // (los de un enlace viejo, como ?demo=enjambre) no cuentan. En este computador (el del pitch)
  // espera a quien presenta.
  const local = /^(127\.0\.0\.1|localhost)$/.test(location.hostname) || location.protocol === "file:";
  const SUYOS = ["w", "t", "speed", "autoplay", "a", "b", "pitch", "escena", "paso", "texto", "enc"];
  const consulta = new URLSearchParams(location.search);
  const pide = SUYOS.some((k) => consulta.has(k));
  marco.src = "enjambre.html" + (pide ? location.search : local ? "" : "?autoplay=1") + location.hash;
})();
