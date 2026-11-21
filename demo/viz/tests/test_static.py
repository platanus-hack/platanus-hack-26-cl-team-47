"""El sitio estático de demo/viz (tarea 17a): todo local, relativo y con valores por defecto."""

import json
import re
from pathlib import Path

import pytest

VIZ = Path(__file__).resolve().parents[1]
ROOT = VIZ.parents[1]
PAGES = ["home.html", "split.html", "index.html"]
REFS = re.compile(r'(?:src|href)\s*=\s*"([^"]*)"')


@pytest.mark.parametrize("page", PAGES)
def test_pagina_local_y_relativa(page):
    html = (VIZ / page).read_text(encoding="utf-8")
    assert not re.search(r"https?://", html), f"{page} carga algo de internet"
    for ref in REFS.findall(html):
        assert not ref.startswith("/"), f"{page}: ruta absoluta {ref!r}"


@pytest.mark.parametrize("page", PAGES)
def test_referencias_existen(page):
    html = (VIZ / page).read_text(encoding="utf-8")
    for ref in REFS.findall(html):
        target = ref.split("?", 1)[0].split("#", 1)[0]
        if target:
            assert (VIZ / target).is_file(), f"{page}: falta {ref}"


def test_portada_enlaza_la_demo_y_un_registro():
    html = (VIZ / "home.html").read_text(encoding="utf-8")
    assert "Medidor de información filtrada para agentes de IA" in html
    assert re.search(r'href="split.html"[^>]*>\s*Ver la demo', html)
    assert re.search(r'href="index.html"[^>]*>\s*Ver un registro', html)
    assert 'href="style.css"' in html


def test_valores_por_defecto_son_los_fixtures_reales():
    split_js = (VIZ / "split.js").read_text(encoding="utf-8")
    app_js = (VIZ / "app.js").read_text(encoding="utf-8")
    for name in ("real_left.jsonl", "real_right.jsonl", "real_graph.json"):
        assert (VIZ / "fixtures" / name).is_file()
        assert f'"fixtures/{name}"' in split_js, f"split.js no usa fixtures/{name} por defecto"
    assert '"fixtures/real_right.jsonl"' in app_js


def test_vercel_json():
    cfg = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert cfg["outputDirectory"] == "demo/viz"
    assert {"source": "/", "destination": "/home.html", "permanent": False} in cfg["redirects"]
    # El único paso de build copia las láminas al sitio (tarea 15n; detalle en test_legible.py).
    assert cfg["buildCommand"].startswith("mkdir -p demo/viz/pitch && cp pitch/")
