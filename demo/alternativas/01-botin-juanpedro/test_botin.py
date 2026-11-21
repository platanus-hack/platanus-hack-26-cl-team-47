"""Alternativa 01, «El botín»: lo que la página supone de las grabaciones, y que se ve entera.

La página no calcula nada: lee demo/viz/fixtures/real_left.jsonl y real_right.jsonl. Si esas
grabaciones se regeneran y dejan de cumplir lo que la página supone, estos tests lo avisan.
"""
from __future__ import annotations

import functools
import http.server
import json
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

HERE = Path(__file__).resolve().parent
DEMO = HERE.parents[1]
FIXTURES = DEMO / "viz" / "fixtures"
PAGE = f"alternativas/{HERE.name}/botin.html"


def _events(name: str) -> list[dict]:
    return [json.loads(line) for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def _fragments(events: list[dict]) -> list[tuple[int, str]]:
    """(t, fragmento) de cada llamada a attacker.test que salió, en orden."""
    action = {e["call_id"]: e["data"]["action"] for e in events if e["kind"] == "decision"}
    out = []
    for e in events:
        if e["kind"] != "tool_call":
            continue
        d = e["data"]
        url = urlparse(d["args"].get("url", ""))
        if url.hostname == "attacker.test" and action[d["id"]].endswith("allow"):
            out.append((d["t"], parse_qs(url.query)["d"][0]))
    return sorted(out)


def _key_read_by_agent(events: list[dict]) -> str:
    for e in events:
        if e["kind"] == "tool_call" and e["data"]["args"].get("path") == ".env":
            for line in e["data"]["output"].splitlines():
                if line.startswith("API_EMPRESA_KEY="):
                    return line.split("=", 1)[1]
    raise AssertionError("la grabación no lee .env")


def _cash(events: list[dict]) -> dict:
    return next(e["data"] for e in events if e["source"] == "attacker" and e["kind"] == "received")


def test_los_archivos_de_la_alternativa_existen():
    for name in ("README.md", "botin.html", "botin.js", "botin.css"):
        assert (HERE / name).is_file(), name


def test_sin_alicanto_los_fragmentos_arman_la_clave_que_leyo_el_agente():
    ev = _events("real_left.jsonl")
    assert "".join(f for _, f in _fragments(ev)) == _key_read_by_agent(ev)
    cash = _cash(ev)
    assert cash["status"] == 200 and cash["key_complete"] is True


def test_con_alicanto_rota_y_el_cobro_falla():
    ev = _events("real_right.jsonl")
    rotations = [e for e in ev if e["kind"] == "rotation" and e["data"]["secret_id"] == "SECRET_1"]
    assert rotations, "la página supone al menos una rotación de SECRET_1"
    calls = {e["data"]["id"]: e["data"] for e in ev if e["kind"] == "tool_call"}
    rot_t = calls[rotations[0]["call_id"]]["t"]
    # La página marca como muertos todos los caracteres desde la rotación: vale porque el
    # agente lee la clave una sola vez, antes de que rote.
    reads = [d["t"] for d in calls.values() if d["args"].get("path") == ".env"]
    assert reads and max(reads) < rot_t
    cash = _cash(ev)
    assert cash["status"] == 401 and cash["key_complete"] is False


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


def _open(browser, url, width, height):
    page = browser.new_page(viewport={"width": width, "height": height})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    page.wait_for_selector("#left .key .ch")
    return page, errors


@pytest.mark.parametrize("size", [(1024, 768), (1280, 720), (1440, 900)])
def test_estado_final_en_proyector(browser, site, size):
    page, errors = _open(browser, site + "?t=end", *size)
    assert page.inner_text("#left .result .code") == "200"
    assert page.inner_text("#right .result .code") == "401"
    assert "rotated" in page.get_attribute("#right", "class")
    assert "Ficha de ejemplo, ficticia".lower() in page.inner_text("#left .ficha").lower()
    assert "48 de 160 bits" in page.inner_text("#headline")
    # Nada se sale: ni la clave de su panel, ni la página de la pantalla.
    fits = page.evaluate(
        """() => {
          const out = [];
          for (const k of document.querySelectorAll('.key')) {
            const panel = k.closest('.term').getBoundingClientRect();
            for (const g of k.querySelectorAll('.grp')) {
              if (g.getBoundingClientRect().right > panel.right - 4) out.push('clave fuera del panel');
            }
          }
          const d = document.documentElement;
          if (d.scrollWidth > innerWidth) out.push('desplazamiento horizontal');
          if (d.scrollHeight > innerHeight + 1) out.push('desplazamiento vertical');
          return out;
        }"""
    )
    assert fits == []
    assert errors == []
    page.close()


@pytest.mark.parametrize("disfraz,prefix", [("base64", "enc_base64"), ("reversed", "enc_reversed")])
def test_fragmentos_disfrazados_arman_la_misma_clave(browser, site, disfraz, prefix):
    key = _key_read_by_agent(_events(f"{prefix}_left.jsonl"))
    page, errors = _open(browser, site + f"?disfraz={disfraz}&t=end", 1280, 720)
    shown = page.evaluate("[...document.querySelectorAll('#left .key .ch')].map(e => e.textContent).join('')")
    assert shown == key
    assert page.inner_text("#left .result .code") == "200"
    assert page.inner_text("#right .result .code") == "401"
    assert errors == []
    page.close()


def test_en_telefono_no_hay_desplazamiento_horizontal(browser, site):
    page, errors = _open(browser, site + "?t=end", 390, 844)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    left = page.locator("#left").bounding_box()
    right = page.locator("#right").bounding_box()
    assert right["y"] >= left["y"] + left["height"] - 1  # una columna
    head = page.locator("#headline").bounding_box()
    assert head["y"] >= right["y"] + right["height"] - 1  # la frase final no tapa nada
    overlap = page.evaluate(
        """() => [...document.querySelectorAll('.meter')].some(m => {
          const a = m.querySelector('.bits').getBoundingClientRect();
          const b = m.querySelector('.of').getBoundingClientRect();
          return a.right > b.left + 1;
        })"""
    )
    assert not overlap  # el número de bits no pisa su leyenda
    assert errors == []
    page.close()


def test_reproduccion_y_momento_de_la_rotacion(browser, site):
    page, errors = _open(browser, site, 1024, 768)
    assert page.is_visible("#hint")
    assert page.inner_text("#right .bits") == "0"
    for _ in range(23):
        page.keyboard.press("ArrowRight")
    assert not page.is_visible("#hint")
    assert page.inner_text("#right .bits") == "32"
    assert "rotated" not in (page.get_attribute("#right", "class") or "")
    page.keyboard.press("ArrowRight")  # llamada 24: rota
    cls = page.get_attribute("#right", "class")
    assert "rotated" in cls and "crumbling" in cls
    assert page.inner_text("#right .bits") == "0"
    assert page.inner_text("#left .bits") == "48"
    assert "llamada 24" in page.inner_text("#right .banner")
    assert page.locator("#right .ch.dead").count() == 12
    assert page.locator("#left .ch.dead").count() == 0
    page.keyboard.press("Space")  # reproduce
    page.wait_for_function("document.getElementById('clock').textContent.includes('llamada 2') && !document.getElementById('clock').textContent.includes('llamada 24')", timeout=8000)
    assert errors == []
    page.close()
