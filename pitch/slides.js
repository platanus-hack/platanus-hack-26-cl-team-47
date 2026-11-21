/* Navegación de las láminas: flechas, espacio, clic, inicio/fin. ?s=N abre la lámina N. */
"use strict";

/* Escenario de la demo (tarea 15j, docs/ESCENARIO.md). Ficticio: no es un hospital real. */
const ESCENARIO = {
  organization: "Hospital Regional Tres Cóndores",
  fictional_note: "Hospital, pacientes y claves ficticios.",
  frase: "Un hospital tiene 3 horas para avisar a la ANCI de un incidente. Su equipo de TI ya programa " +
         "con agentes de IA, y las claves de la ficha clínica están en el mismo repositorio que el agente lee.",
};

/** Lámina «El ejemplo» (respaldo): agrega la frase y el nombre del escenario (con nota de ficticio). */
function aplicarEscenario(doc) {
  const s3 = doc.querySelector(".slide.slide-ejemplo");
  if (!s3) return;
  const marker = s3.querySelector(".pendiente");
  const frase = doc.createElement("p");
  frase.textContent = ESCENARIO.frase;
  const nombre = doc.createElement("p");
  nombre.className = "escenario-nombre";
  nombre.style.fontSize = "26px";
  nombre.style.color = "var(--muted)";
  nombre.textContent = `${ESCENARIO.organization} · ${ESCENARIO.fictional_note}`;
  if (marker) marker.replaceWith(frase, nombre); else s3.append(frase, nombre);
}

(function () {
  aplicarEscenario(document);
  const slides = Array.from(document.querySelectorAll(".slide"));
  const deck = document.getElementById("deck");
  const counter = document.getElementById("counter");
  let i = 0;

  function fit() {
    const s = Math.min(window.innerWidth / 1600, window.innerHeight / 900) * 0.96;
    deck.style.transform = `translate(-50%, -50%) scale(${s})`;
  }

  function show(n) {
    i = Math.max(0, Math.min(slides.length - 1, n));
    slides.forEach((el, k) => el.classList.toggle("active", k === i));
    counter.textContent = `${i + 1} / ${slides.length}`;
    try { history.replaceState(null, "", `?s=${i + 1}`); } catch (e) { /* file:// */ }
  }

  document.addEventListener("keydown", (e) => {
    if (["ArrowRight", "PageDown", " ", "Enter"].includes(e.key)) { e.preventDefault(); show(i + 1); }
    if (["ArrowLeft", "PageUp", "Backspace"].includes(e.key)) { e.preventDefault(); show(i - 1); }
    if (e.key === "Home") show(0);
    if (e.key === "End") show(slides.length - 1);
  });
  deck.addEventListener("click", (e) => {
    if (e.target.closest("a")) return; // el enlace de la demo no avanza
    show(e.clientX < window.innerWidth / 3 ? i - 1 : i + 1);
  });
  document.getElementById("prev").addEventListener("click", () => show(i - 1));
  document.getElementById("next").addEventListener("click", () => show(i + 1));
  window.addEventListener("resize", fit);

  const start = Number(new URLSearchParams(location.search).get("s")) || 1;
  fit();
  show(start - 1);
})();
