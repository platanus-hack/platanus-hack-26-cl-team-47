"""Página de resultados de la evaluación final (16f). Sin navegador."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

VIZ = Path(__file__).resolve().parents[1]
ROOT = VIZ.parents[1]
FIXTURE = VIZ / "fixtures" / "results.json"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_la_copia_coincide_con_los_originales():
    fx = load(FIXTURE)
    assert fx["systems"] == load(ROOT / "results" / "test" / "systems.json")
    assert fx["report"] == load(ROOT / "results" / "test" / "report.json")
    assert fx["run"] == load(ROOT / "results" / "test" / "RUN.json")
    assert fx["adaptive"] == load(ROOT / "results" / "adaptive" / "summary.json")
    seal = re.search(r"Sello \(sha256\):\*\*\s*`([0-9a-f]{64})`", (ROOT / "redteam" / "SELLO.md").read_text(encoding="utf-8"))
    assert seal and fx["seal"] == seal.group(1)


def test_la_copia_trae_los_nueve_sistemas_y_las_cifras_de_la_lamina():
    fx = load(FIXTURE)
    rows = {r["system"]: r for r in fx["systems"]}
    assert len(rows) == 9
    assert rows["ours"]["prevented_rate"] == 1.0 and rows["ours"]["false_alarm_rate"] == 0.0
    assert rows["no_rotation"]["prevented_rate"] == pytest.approx(30 / 180)
    assert fx["report"]["tests"]["T3"]["b"] == 150 and fx["report"]["tests"]["T3"]["c"] == 0
    ours = fx["adaptive"]["test"]["ours"]["overall"]
    assert ours["prevented"] == ours["rewritten"] == 180 and ours["max_max_bits"] <= 96


def test_pagina_de_resultados():
    html = (VIZ / "results.html").read_text(encoding="utf-8")
    assert "fixtures/results.json" in html and 'src="results.js"' in html
    assert "fixtures/results.json" in (VIZ / "results.js").read_text(encoding="utf-8")
    assert "no dice" in html
    assert len(re.findall(r"<li>", html.split("no dice", 1)[1].split("</ol>", 1)[0])) == 7
    assert "180 ataques de seis familias nuevas: ninguno sacó más de 32 de 160 bits" in html
    assert 'name="viewport"' in html and 'href="style.css"' in html
    assert not re.search(r"https?://", html)
    for ref in re.findall(r'(?:src|href)\s*=\s*"([^"]*)"', html):
        assert not ref.startswith("/") and (VIZ / ref.split("?", 1)[0]).is_file(), ref


def test_cada_sistema_explicado_y_las_replicas_marcadas():
    js = (VIZ / "results.js").read_text(encoding="utf-8")
    for s in ("ours", "no_rotation", "per_session", "no_evidence", "allowlist", "detect_secrets", "combined",
              "budget", "reassembly"):
        assert re.search(rf"\b{s}: \[", js), s
    assert js.count("(réplica)") == 2 and js.count("Réplica simplificada") == 2


def test_portada_enlaza_los_resultados():
    html = (VIZ / "home.html").read_text(encoding="utf-8")
    assert 'href="results.html"' in html and "Ver los resultados y sus límites" in html
    assert "180 de 180 ataques nuevos prevenidos · 0 llamadas benignas bloqueadas" in html


@pytest.mark.skipif(not shutil.which("node"), reason="node no está instalado")
def test_filas_en_node():
    script = """
const r = require(%s);
const fx = require(%s);
const rows = r.systemRows(fx.systems);
const ad = r.adaptiveRows(fx.adaptive);
console.log(JSON.stringify({n: rows.length, first: rows[0].name, ours: ad.find(x => x.system === "ours").prevented}));
""" % (json.dumps(str(VIZ / "results.js")), json.dumps(str(FIXTURE)))
    out = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8",
                                    check=True).stdout)
    assert out == {"n": 9, "first": "Alicanto", "ours": "180 de 180"}
