"""Demo legible a 1024×768 y en teléfono, y aviso de reproducción (tarea 15n).

Con navegador (Playwright, se salta si no está instalado):
    pip install playwright && playwright install chromium
"""

import functools
import http.server
import json
import re
import threading
from pathlib import Path

import pytest

VIZ = Path(__file__).resolve().parents[1]

SIZES = [(1024, 768), (1280, 720), (1440, 900), (390, 844)]
DEMOS = ["split.html?t=end", "split.html?demo=enjambre&t=end"]

# Mide, dentro de la página, todo lo que pide el contrato de A.
MEASURE = """() => {
  const box = (el) => el.getBoundingClientRect();
  const sides = [...document.querySelectorAll('.split-page .side')];
  const per = sides.map((s) => {
    const head = s.querySelector('.side-head'), meter = s.querySelector('.meter'), result = s.querySelector('.result');
    const hb = box(head);
    const hidden = [...result.querySelectorAll('*')].concat([result]).filter((el) => {
      const b = box(el);
      return b.top < hb.top - 1 || b.bottom > hb.bottom + 1 || b.left < hb.left - 1 || b.right > hb.right + 1;
    }).map((el) => el.className);
    return {
      head: { sh: head.scrollHeight, ch: head.clientHeight, h: hb.height },
      meter: { sh: meter.scrollHeight, ch: meter.clientHeight, h: box(meter).height },
      resultText: result.innerText.trim(),
      resultClipped: result.scrollHeight > result.clientHeight + 1 || result.scrollWidth > result.clientWidth + 1,
      hidden,
      top: box(s).top + window.scrollY, bottom: box(s).bottom + window.scrollY,
    };
  });
  const controls = box(document.querySelector('.controls'));
  // html tiene overflow-x: hidden, así que scrollWidth no basta: se mira cada elemento.
  const outside = [...document.querySelectorAll('.bar *, .split *')]
    .filter((el) => el.getClientRects().length && !el.closest('svg, .call-list'))
    .filter((el) => box(el).right > window.innerWidth + 1 || box(el).left < -1)
    .slice(0, 5).map((el) => `${el.tagName}.${el.className}`);
  return {
    outside,
    sides: per,
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    controlsRight: controls.right,
    controlsLeft: controls.left,
  };
}"""


@pytest.fixture(scope="module")
def server():
    handler = functools.partial(_QuietHandler, directory=str(VIZ))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _settle(page):
    """Espera a que termine el sello (se vuelve a animar al cargar el escenario) y las transiciones."""
    page.wait_for_timeout(300)
    page.wait_for_function("document.getAnimations().every((a) => a.playState !== 'running')")


def _open(browser, url, size):
    page = browser.new_page(viewport={"width": size[0], "height": size[1]})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    return page, errors


@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
@pytest.mark.parametrize("demo", DEMOS)
def test_nada_cortado_y_lados_alineados(server, browser, demo, size):
    page, errors = _open(browser, f"{server}/{demo}", size)
    try:
        page.wait_for_function("document.querySelectorAll('.side .result .result-code').length === 2")
        page.wait_for_load_state("networkidle")
        _settle(page)
        m = page.evaluate(MEASURE)
    finally:
        page.close()
    assert not errors, errors
    assert not m["outside"], f"elementos fuera de la pantalla: {m['outside']}"
    left, right = m["sides"]
    for name, s in (("izquierda", left), ("derecha", right)):
        assert s["head"]["sh"] <= s["head"]["ch"] + 1, f"{name}: cabecera cortada {s['head']}"
        assert s["meter"]["sh"] <= s["meter"]["ch"] + 1, f"{name}: medidor cortado {s['meter']}"
        assert s["resultText"], f"{name}: sin resultado"
        assert not s["resultClipped"], f"{name}: texto del resultado cortado"
        assert not s["hidden"], f"{name}: partes del resultado fuera de la cabecera: {s['hidden']}"
    if size[0] >= 900:
        assert abs(left["head"]["h"] - right["head"]["h"]) <= 1, (left["head"], right["head"])
        assert abs(left["meter"]["h"] - right["meter"]["h"]) <= 1, (left["meter"], right["meter"])
    else:
        assert right["top"] >= left["bottom"], "en teléfono, «con Alicanto» va debajo de «sin protección»"
        assert m["scrollWidth"] <= m["innerWidth"], f"desplazamiento horizontal: {m['scrollWidth']} > {m['innerWidth']}"
        assert m["controlsLeft"] >= 0 and m["controlsRight"] <= m["innerWidth"], "los controles no caben"


@pytest.mark.parametrize("demo", ["split.html", "split.html?demo=enjambre"])
def test_aviso_de_reproduccion(server, browser, demo):
    page, errors = _open(browser, f"{server}/{demo}", (1024, 768))
    try:
        page.wait_for_function("document.getElementById('position').textContent.startsWith('t = ')")
        hint = page.locator("#play-hint")
        assert hint.is_visible()
        assert hint.inner_text() == "Pulsa espacio o ▶ para reproducir"
        page.keyboard.press(" ")
        assert hint.is_hidden()
        page.wait_for_timeout(700)
        page.keyboard.press(" ")              # pausa: el aviso no vuelve
        page.click("#btn-start")              # ni al volver al inicio
        assert hint.is_hidden()
    finally:
        page.close()
    assert not errors, errors


def test_sin_aviso_con_t(server, browser):
    page, _ = _open(browser, f"{server}/split.html?t=end", (1280, 720))
    try:
        page.wait_for_function("document.getElementById('position').textContent.startsWith('t = ')")
        assert page.locator("#play-hint").is_hidden()
    finally:
        page.close()


def test_doble_clic_explica_como_abrirla(browser):
    page, _ = _open(browser, (VIZ / "split.html").as_uri() + "?demo=enjambre", (1024, 768))
    try:
        box = page.locator(".needs-server")
        box.wait_for()
        assert "Esta página necesita un servidor." in box.inner_text()
        assert "Failed to fetch" not in page.content()
        assert box.locator("a").get_attribute("href") == "https://alicanto.vercel.app/split.html?demo=enjambre"
        assert "python -m http.server 8200 --directory demo/viz" in box.inner_text()
    finally:
        page.close()


# ------------------------------------------------ sin navegador

ROOT = VIZ.parents[1]


def test_css_ya_no_fija_alto_con_overflow_hidden():
    css = (VIZ / "style.css").read_text(encoding="utf-8")
    for sel in (".split-page .side-head", ".split-page .meter"):
        for m in re.finditer(re.escape(sel) + r"\s*\{([^}]*)\}", css):
            body = m.group(1)
            fixed = re.search(r"(?<![-\w])height:\s*\d", body)
            assert not (fixed and re.search(r"overflow:\s*hidden", body)), f"{sel} {{{body}}}"


def test_split_js_explica_file():
    js = (VIZ / "split.js").read_text(encoding="utf-8")
    assert 'location.protocol === "file:"' in js
    assert "Esta página necesita un servidor. Ábrela en " in js
    assert '"https://alicanto.vercel.app/split.html"' in js
    assert "python -m http.server 8200 --directory demo/viz" in js


def test_split_html_tiene_el_aviso_de_reproduccion():
    html = (VIZ / "split.html").read_text(encoding="utf-8")
    assert re.search(r'id="play-hint"[^>]*hidden[^>]*>Pulsa espacio o ▶ para reproducir<', html)


def test_vercel_json_publica_las_laminas():
    cfg = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    build = cfg["buildCommand"]
    assert "mkdir -p demo/viz/pitch" in build
    for f in ("index.html", "slides.js", "style.css"):
        assert f"pitch/{f}" in build
        assert (ROOT / "pitch" / f).is_file()
    assert build.rstrip().endswith("demo/viz/pitch/")
    for r in ({"source": "/", "destination": "/home.html", "permanent": False},
              {"source": "/pitch", "destination": "/pitch/index.html", "permanent": False},
              {"source": "/demo/viz/:path*", "destination": "/:path*", "permanent": False}):
        assert r in cfg["redirects"], r
    # Las láminas no cargan nada fuera de esos tres archivos (si no, hay que agregarlo a la copia).
    html = (ROOT / "pitch" / "index.html").read_text(encoding="utf-8")
    local = [h for h in re.findall(r'(?:src|href)="([^"]+)"', html) if not h.startswith(("http", "../demo/viz/", "#"))]
    assert set(local) <= {"style.css", "slides.js"}, local
    assert "demo/viz/pitch/" in (ROOT / ".gitignore").read_text(encoding="utf-8")
