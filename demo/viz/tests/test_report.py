"""report.html: informe de incidente (tarea 15i). Sin navegador."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

VIZ = Path(__file__).resolve().parents[1]
HTML = (VIZ / "report.html").read_text(encoding="utf-8")


def test_sin_internet_y_rutas_relativas():
    assert not re.search(r"https?://", HTML)
    for ref in re.findall(r'(?:src|href)="([^"]+)"', HTML):
        assert not ref.startswith("/") and (VIZ / ref).exists(), ref


def test_valor_por_defecto_es_el_fixture_real():
    js = (VIZ / "report.js").read_text(encoding="utf-8")
    assert '"fixtures/real_report.json"' in js
    assert (VIZ / "fixtures" / "real_report.json").is_file()


def test_hoja_de_impresion():
    assert "@media print" in HTML


def test_split_enlaza_el_informe():
    assert 'href="report.html"' in (VIZ / "split.html").read_text(encoding="utf-8")


@pytest.mark.skipif(not shutil.which("node"), reason="node no está instalado")
def test_marcas_de_la_linea_de_tiempo_en_node():
    script = f"""
    const fs = require("fs");
    const {{ timelineMarks }} = require({json.dumps(str(VIZ / "report.js"))});
    const rep = JSON.parse(fs.readFileSync({json.dumps(str(VIZ / "fixtures" / "real_report.json"))}, "utf8"));
    console.log(JSON.stringify(timelineMarks(rep.secrets[0])));
    """
    marks = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    kinds = [m["kind"] for m in marks]
    assert kinds.count("exposed") == 1 and kinds.count("rotation") == 1 and kinds.count("leak") == 3
    assert all(0 <= m["x"] <= 1 for m in marks)
    assert max(m["x"] for m in marks) == 1
