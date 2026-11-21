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
    assert fx["proxy_flags"] == load(ROOT / "results" / "proxy_flags" / "systems.json")
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
    pf = {v: {r["system"]: r for r in fx["proxy_flags"][v]} for v in ("grabadas", "proxy")}
    assert pf["proxy"]["ours"]["prevented_rate"] == pytest.approx(120 / 180)
    assert pf["proxy"]["taint_rule"]["prevented_rate"] == pytest.approx(90 / 180)
    assert pf["grabadas"]["taint_rule"]["prevented_rate"] == 1.0
    assert pf["proxy"]["ours"]["false_alarm_rate"] == 0.0
    # La variante «grabadas» reproduce results/test (los extremos de algunos intervalos difieren en el
    # último dígito del flotante, por eso no se compara byte a byte).
    keys = ("prevented_rate", "false_alarm_rate", "benign_rotations_per_1000", "median_max_bits_true", "by_family")
    assert {r["system"]: [r[k] for k in keys] for r in fx["systems"]} == \
        {s: [r[k] for k in keys] for s, r in pf["grabadas"].items() if s != "taint_rule"}


def test_pagina_de_resultados():
    html = (VIZ / "results.html").read_text(encoding="utf-8")
    assert "fixtures/results.json" in html and 'src="results.js"' in html
    assert "fixtures/results.json" in (VIZ / "results.js").read_text(encoding="utf-8")
    assert "no dice" in html
    limits = html.split("no dice", 1)[1].split("</ol>", 1)[0]
    assert len(re.findall(r"<li>", limits)) == 10
    assert "A9" in limits and "A13" in limits and "4 de 6 familias" in limits and "regla simple empata" in limits
    assert "180 ataques grabados de seis familias nuevas: Alicanto frenó 120, cuatro de las seis" in html
    assert "como lo calcula el proxy en vivo" in html and "con las marcas de las grabaciones" in html
    assert "32 de 160" not in html
    assert 'name="viewport"' in html and 'href="style.css"' in html
    assert not re.search(r"https?://", html)
    for ref in re.findall(r'(?:src|href)\s*=\s*"([^"]*)"', html):
        assert not ref.startswith("/") and (VIZ / ref.split("?", 1)[0]).is_file(), ref


def test_cada_sistema_explicado_y_las_replicas_marcadas():
    js = (VIZ / "results.js").read_text(encoding="utf-8")
    for s in ("ours", "no_rotation", "per_session", "no_evidence", "allowlist", "detect_secrets", "combined",
              "budget", "reassembly", "taint_rule"):
        assert re.search(rf"\b{s}: \[", js), s
    assert js.count("(réplica)") == 2 and js.count("Réplica simplificada") == 2


def test_portada_enlaza_los_resultados():
    html = (VIZ / "home.html").read_text(encoding="utf-8")
    assert 'href="results.html"' in html and "Ver los resultados y sus límites" in html
    assert ("120 de 180 ataques nuevos frenados, medido como los ve el proxy en vivo · 0 llamadas normales bloqueadas"
            in html)


def _paragraphs(path):
    text = Path(path).read_text(encoding="utf-8")
    if path.suffix == ".html":
        return re.split(r"</(?:p|li|div|h[1-6]|td|th|dd|section)>", text)
    return re.split(r"\n\s*\n|\n(?=\s*[-*|] )", text.replace("\r\n", "\n"))   # párrafos, viñetas y filas


# En HTML un párrafo puede ocupar varias líneas: se busca en todo el bloque.
QUALIFIED = re.compile(r"(marcas|banderas).*?(grabaciones|generador)|(grabaciones|generador).*?(marcas|banderas)",
                       re.IGNORECASE | re.DOTALL)


@pytest.mark.parametrize("path", [ROOT / "README.md", ROOT / "docs" / "RESUMEN.md", *sorted(VIZ.glob("*.html"))],
                         ids=lambda p: p.name)
def test_180_de_180_siempre_con_las_marcas_de_las_grabaciones(path):
    """#180: «180 de 180» solo junto a que se midió con las marcas (banderas) de las grabaciones."""
    for par in _paragraphs(path):
        if "180 de 180" in par:
            assert QUALIFIED.search(par), f"{path.name}: «180 de 180» sin decir que es con las marcas de las grabaciones: {par.strip()[:200]!r}"


def test_el_detector_de_frases_sueltas_funciona(tmp_path):
    bad = tmp_path / "x.md"
    bad.write_text("Intro.\n\nAlicanto frenó 180 de 180 ataques.\n\nCon las banderas del generador.\n", encoding="utf-8")
    assert any("180 de 180" in p and not QUALIFIED.search(p) for p in _paragraphs(bad))


@pytest.mark.skipif(not shutil.which("node"), reason="node no está instalado")
def test_filas_en_node():
    script = """
const r = require(%s);
const fx = require(%s);
const rows = r.systemRows(fx.systems);
const ad = r.adaptiveRows(fx.adaptive);
const rows2 = r.systemRows(fx.systems, fx.proxy_flags);
console.log(JSON.stringify({n: rows.length, n2: rows2.length, first: rows[0].name, ours: ad.find(x => x.system === "ours").prevented,
  live: rows2[0].proxy.split(" [")[0], rec: rows2[0].prevented.split(" [")[0]}));
""" % (json.dumps(str(VIZ / "results.js")), json.dumps(str(FIXTURE)))
    out = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8",
                                    check=True).stdout)
    assert out == {"n": 9, "n2": 10, "first": "Alicanto", "ours": "180 de 180", "live": "120 de 180", "rec": "180 de 180"}
