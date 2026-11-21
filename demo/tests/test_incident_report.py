"""demo/incident_report.py: informe de incidente por secreto desde el registro (tarea 15i)."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import read_events  # noqa: E402
from demo.incident_report import build_report  # noqa: E402

FIX = ROOT / "demo" / "viz" / "fixtures"
RIGHT, LEFT, REPORT = FIX / "real_right.jsonl", FIX / "real_left.jsonl", FIX / "real_report.json"
MANIFEST = ROOT / "demo" / "secrets_manifest.json"


def right():
    return build_report(read_events(RIGHT), generated_from=RIGHT.name)


def test_derecha_un_secreto_con_rotacion_y_al_menos():
    rep = right()
    assert rep["generated_from"] == "real_right.jsonl" and rep["session_id"]
    assert [s["secret_id"] for s in rep["secrets"]] == ["SECRET_1"]
    s = rep["secrets"][0]
    assert s["rotations"] and s["rotations"][0]["t"] == 24 and s["rotations"][0]["version"] == 2
    assert s["rotations"][0]["reason"]
    assert s["leak_calls"] and all(c["destination"] == "attacker.test" for c in s["leak_calls"])
    assert [c["bits_after"] for c in s["leak_calls"]] == [16.0, 32.0, 48.0]
    assert s["max_bits_before_rotation"] == 48.0 and s["max_fraction"] == 0.3
    assert s["exposed_at"] == {"call_id": "c3", "t": 3, "tool": "read_file", "resource": ".env"}
    assert s["path"][0] == "c3" and s["destinations"] == ["attacker.test"]
    assert s["final_status"] == 401
    assert "al menos" in s["statement"]
    assert s["statement"] == ("Salieron al menos 48 bits de 160 de SECRET_1 hacia attacker.test en 3 llamadas. "
                              "La clave se rotó en la llamada 24. La versión filtrada ya no es válida.")


def test_izquierda_sin_rotaciones_y_200():
    rep = build_report(read_events(LEFT))
    s = rep["secrets"][0]
    assert s["rotations"] == [] and s["exposed_at"] is None
    assert s["final_status"] == 200
    assert s["max_bits_before_rotation"] == 160.0 and len(s["leak_calls"]) == 10
    assert "al menos" in s["statement"] and "no se rotó" in s["statement"]


def test_sin_valores_ni_fragmentos_de_secretos():
    secrets = [s["value"] for s in json.loads(MANIFEST.read_text(encoding="utf-8"))["secrets"]]
    frags = set()
    for path in (RIGHT, LEFT):
        for e in read_events(path):
            if e.kind == "tool_call":
                for v in re.findall(r"[0-9a-fA-F]{4,}", json.dumps(e.data.get("args", {}))):
                    if any(v.lower() in s for s in secrets):
                        frags.add(v.lower())
    assert frags, "la sesión debe tener fragmentos en los argumentos para que el test sirva"
    for path in (RIGHT, LEFT):
        text = json.dumps(build_report(read_events(path)), ensure_ascii=False).lower()
        assert not any(s in text for s in secrets)
        assert not any(f in text for f in frags), "el informe contiene un fragmento del secreto"


def test_fixture_al_dia():
    """El fixture de la página se genera con el escenario (--scenario demo/scenario.json)."""
    from demo.incident_report import load_scenario
    fresh = build_report(read_events(RIGHT), generated_from=RIGHT.name, scenario=load_scenario())
    assert json.loads(REPORT.read_text(encoding="utf-8")) == fresh


def test_cli(tmp_path):
    out = tmp_path / "report.json"
    r = subprocess.run([sys.executable, str(ROOT / "demo" / "incident_report.py"), "--events", str(RIGHT),
                        "--out", str(out)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(out.read_text(encoding="utf-8")) == right()
    assert "al menos" in r.stdout


def test_sin_fuga_ni_rotacion_no_hay_secretos():
    from contracts import Event
    evs = [Event(ts=0, session_id="s", source="proxy", kind="tool_call", call_id="c1",
                 data={"id": "c1", "t": 1, "tool": "read_file", "args": {"path": "README.md"}, "resources": ["README.md"]}),
           Event(ts=0, session_id="s", source="proxy", kind="decision", call_id="c1",
                 data={"action": "allow", "leak": {"SECRET_1": {"bits": 0.0, "fraction": 0.0}}})]
    assert build_report(evs)["secrets"] == []


# ------------------------------------------------ escenario del hospital (15j)

SCENARIO = ROOT / "demo" / "scenario.json"


def test_scenario_json_es_el_bloque_de_escenario_md():
    doc = (ROOT / "docs" / "ESCENARIO.md").read_text(encoding="utf-8")
    block = re.search(r"`demo/scenario.json` \(contenido exacto\):\n\n```json\n(.*?)```", doc, re.S).group(1)
    assert json.loads(SCENARIO.read_text(encoding="utf-8")) == json.loads(block)
    assert SCENARIO.read_text(encoding="utf-8") == block


def test_copia_para_el_sitio_estatico_es_identica():
    assert (ROOT / "demo" / "viz" / "scenario.json").read_bytes() == SCENARIO.read_bytes()


def test_informe_con_escenario_usa_etiquetas():
    from demo.incident_report import load_scenario
    rep = build_report(read_events(RIGHT), generated_from=RIGHT.name, scenario=load_scenario())
    text = json.dumps(rep, ensure_ascii=False)
    assert "Clave de la API de ficha clínica (SECRET_1)" in text
    assert "Hospital Regional Tres Cóndores" in text
    assert rep["secrets"][0]["statement"].startswith(
        "Salieron al menos 48 bits de 160 de la Clave de la API de ficha clínica (SECRET_1) "
        "hacia el Servidor del atacante (attacker.test)")
    # los campos técnicos no cambian
    assert rep["secrets"][0]["secret_id"] == "SECRET_1" and rep["secrets"][0]["destinations"] == ["attacker.test"]


def test_informe_sin_escenario_igual_que_antes():
    rep = right()
    assert "organization" not in rep
    assert rep["secrets"][0]["statement"].startswith("Salieron al menos 48 bits de 160 de SECRET_1 hacia attacker.test")


def test_cli_con_escenario(tmp_path):
    out = tmp_path / "r.json"
    r = subprocess.run([sys.executable, str(ROOT / "demo" / "incident_report.py"), "--events", str(RIGHT),
                        "--out", str(out), "--scenario", str(SCENARIO)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(out.read_text(encoding="utf-8"))["organization"] == "Hospital Regional Tres Cóndores"
