"""Escenario en la visualización (tarea 15j). Sin navegador."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

VIZ = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("page", ["split.html", "report.html", "home.html", "index.html"])
def test_paginas_cargan_el_escenario_y_muestran_la_nota(page):
    html = (VIZ / page).read_text(encoding="utf-8")
    assert '<script src="scenario.js"></script>' in html
    for el in ("scenario-org", "scenario-system", "scenario-note"):
        assert f'id="{el}"' in html, f"{page} no tiene #{el}"


def test_scenario_js_lee_scenario_json_y_llena_la_nota():
    js = (VIZ / "scenario.js").read_text(encoding="utf-8")
    assert '"scenario.json"' in js and "fictional_note" in js and "organization" in js
    assert (VIZ / "scenario.json").is_file()


def test_scenario_js_se_carga_antes_que_los_que_lo_usan():
    html = (VIZ / "split.html").read_text(encoding="utf-8")
    order = [s for s in ("scenario.js", "app.js", "graph.js", "split.js") if s in html]
    assert sorted(order, key=html.index) == ["scenario.js", "app.js", "graph.js", "split.js"]


@pytest.mark.skipif(not shutil.which("node"), reason="node no está instalado")
def test_label_en_node():
    script = f"""
    const {{ label, labelWithId, setScenario }} = require({json.dumps(str(VIZ / "scenario.js"))});
    const before = labelWithId("SECRET_1");
    setScenario(JSON.parse(require("fs").readFileSync({json.dumps(str(VIZ / "scenario.json"))}, "utf8")));
    console.log(JSON.stringify({{ before,
      s1: labelWithId("SECRET_1"), att: labelWithId("attacker.test"), other: labelWithId("otro.test"),
      raw: label("SECRET_1") }}));
    """
    r = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True,
                                  encoding="utf-8", check=True).stdout)
    assert r["before"] == "SECRET_1"  # sin escenario, el id
    assert r["s1"] == "Clave de la API de ficha clínica (SECRET_1)"
    assert r["att"] == "Servidor del atacante (attacker.test)"
    assert r["other"] == "otro.test"
    assert r["raw"] == "Clave de la API de ficha clínica"
