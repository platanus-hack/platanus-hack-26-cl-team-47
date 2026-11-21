/* Navegación de las láminas: flechas, espacio, clic, inicio/fin. ?s=N abre la lámina N. */
"use strict";

(function () {
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
