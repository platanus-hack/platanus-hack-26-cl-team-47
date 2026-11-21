"""Alternativa 02, «El juez es el atacante»: la página del teléfono, con las grabaciones reales."""
from __future__ import annotations

import functools
import http.server
import json
import threading
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
DEMO = HERE.parents[1]
FIXTURES = DEMO / "viz" / "fixtures"
PAGE = f"alternativas/{HERE.name}/atacante.html"


def _events(name: str) -> list[dict]:
    return [json.loads(line) for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def _key_read_by_agent(events: list[dict]) -> str:
    for e in events:
        if e["kind"] == "tool_call" and e["data"]["args"].get("path") == ".env":
            for line in e["data"]["output"].splitlines():
                if line.startswith("API_EMPRESA_KEY="):
                    return line.split("=", 1)[1]
    raise AssertionError("la grabación no lee .env")


def test_los_archivos_de_la_alternativa_existen():
    for name in ("README.md", "atacante.html", "atacante.js", "atacante.css"):
        assert (HERE / name).is_file(), name


def test_la_pagina_no_delata_cual_hospital_tiene_alicanto_antes_del_cobro():
    """El atacante no sabe en qué hospital está: ni la página ni el parámetro lo dicen."""
    html = (HERE / "atacante.html").read_text(encoding="utf-8").lower()
    assert "alicanto" not in html
    assert "sin protec" not in html


@pytest.fixture(scope="module")
def site():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):  # sin registro de peticiones en la salida de los tests
            pass

    handler = functools.partial(Quiet, directory=str(DEMO))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/{PAGE}"
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:  # navegador de Playwright sin instalar
            pytest.skip(f"sin navegador de Playwright: {exc}")
        yield b
        b.close()


def _open(browser, url):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    page.wait_for_selector("#key .ch", state="attached")
    return page, errors


@pytest.mark.parametrize("h,fixture,status", [("1", "real_left.jsonl", "200"), ("2", "real_right.jsonl", "401")])
def test_recorrido_completo_en_telefono(browser, site, h, fixture, status):
    key = _key_read_by_agent(_events(fixture))
    page, errors = _open(browser, f"{site}?h={h}&ritmo=150")
    assert page.is_visible("#start")
    assert "attacker.test" in page.inner_text("#issue")
    page.click("#start")
    assert page.is_disabled("#use")  # no se puede cobrar sin la clave completa
    page.wait_for_selector("#use:not([disabled])", timeout=8000)
    shown = page.evaluate("[...document.querySelectorAll('#key .ch')].map(e => e.textContent).join('')")
    assert shown == key  # en los dos hospitales el atacante junta la misma clave
    assert "40 de 40" in page.inner_text("#count")
    assert "alicanto" not in page.inner_text("#app").lower()  # todavía no sabe en cuál está
    page.click("#use")
    assert page.inner_text("#result .code") == status
    text = page.inner_text("#result")
    if status == "200":
        assert "Ficha de ejemplo, ficticia".lower() in text.lower()
    else:
        assert "llamada 24" in text and "12 de 40" in text
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert errors == []
    page.close()


def test_se_puede_volver_a_intentar(browser, site):
    page, errors = _open(browser, site + "?h=2&t=cobro")
    assert page.inner_text("#result .code") == "401"
    page.click("#result .again")
    assert page.is_visible("#start")
    assert errors == []
    page.close()
