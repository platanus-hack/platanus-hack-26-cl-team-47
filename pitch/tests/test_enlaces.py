"""Láminas abiertas con doble clic (file://): los enlaces a la demo van al sitio público (tarea 15n)."""

import re
from pathlib import Path

import pytest

PITCH = Path(__file__).resolve().parents[1]
SLIDES_JS = (PITCH / "slides.js").read_text(encoding="utf-8")
HTML = (PITCH / "index.html").read_text(encoding="utf-8")


def test_slides_js_reescribe_los_enlaces_con_file():
    assert 'protocol !== "file:"' in SLIDES_JS
    assert '"https://alicanto.vercel.app/"' in SLIDES_JS
    assert "demo\\/viz\\/" in SLIDES_JS  # la expresión que reconoce ../demo/viz/<archivo>
    assert "enlacesDemo(document, location.protocol)" in SLIDES_JS


def test_las_laminas_enlazan_la_demo_con_rutas_relativas():
    # En el sitio, /pitch/index.html -> ../demo/viz/split.html -> /demo/viz/split.html -> /split.html (vercel.json).
    hrefs = re.findall(r'href="([^"]*demo/viz/[^"]*)"', HTML)
    assert hrefs and all(h.startswith("../demo/viz/") for h in hrefs), hrefs


def test_en_el_navegador_con_file_los_enlaces_van_al_sitio():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto((PITCH / "index.html").as_uri())
        demo = page.get_attribute("a.demo-link", "href")
        swarm = page.get_attribute("a.swarm-link", "href")
        others = page.eval_on_selector_all("a[href]", "els => els.map((a) => a.getAttribute('href'))")
        browser.close()
    assert not errors, errors
    assert demo == "https://alicanto.vercel.app/split.html"
    assert swarm == "https://alicanto.vercel.app/split.html?demo=enjambre"
    assert not [h for h in others if "demo/viz/" in h and not h.startswith("https://")], others
