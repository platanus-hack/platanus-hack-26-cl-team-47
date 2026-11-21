"""Tests de la pantalla dividida (tarea 15b). Sin navegador."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from contracts import Decision, Event, ToolCall

VIZ = Path(__file__).resolve().parents[1]
LEFT = VIZ / "fixtures" / "split_left.jsonl"
RIGHT = VIZ / "fixtures" / "split_right.jsonl"


def load(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def bits_by_t(evs, sid="SECRET_1"):
    t_of = {e["call_id"]: e["data"]["t"] for e in evs if e["kind"] == "tool_call"}
    return {t_of[e["call_id"]]: e["data"]["leak"].get(sid, {}).get("bits", 0.0)
            for e in evs if e["kind"] == "decision"}


@pytest.mark.parametrize("path", [LEFT, RIGHT], ids=["left", "right"])
def test_cada_linea_es_un_event_valido(path):
    for raw in load(path):
        ev = Event.model_validate(raw)
        if ev.kind == "tool_call":
            ToolCall.model_validate(ev.data)
        elif ev.kind == "decision":
            Decision.model_validate(ev.data)


def test_mismos_valores_de_t():
    ts = [{e["data"]["t"] for e in load(p) if e["kind"] == "tool_call"} for p in (LEFT, RIGHT)]
    assert ts[0] == ts[1] == set(range(1, 61))


def test_izquierdo_sin_rotaciones_y_200():
    evs = load(LEFT)
    assert not [e for e in evs if e["kind"] == "rotation"]
    assert all(e["data"]["action"] == "allow" for e in evs if e["kind"] == "decision")
    bits = [b for _, b in sorted(bits_by_t(evs).items())]
    assert bits == sorted(bits) and bits[-1] > bits[0]  # solo sube
    assert evs[-1]["source"] == "attacker" and evs[-1]["kind"] == "received"
    assert evs[-1]["data"]["status"] == 200


def test_derecho_diente_de_sierra_y_401():
    evs = load(RIGHT)
    rotations = [e for e in evs if e["kind"] == "rotation"]
    assert len(rotations) >= 2
    t_of = {e["call_id"]: e["data"]["t"] for e in evs if e["kind"] == "tool_call"}
    bits = bits_by_t(evs)
    for r in rotations:
        t = t_of[r["call_id"]]
        assert bits[t] > 0, "debe haber bits filtrados al momento de rotar"
        assert bits[t + 1] == 0, f"los bits no vuelven a 0 tras la rotación en t={t}"
    assert evs[-1]["source"] == "attacker" and evs[-1]["data"]["status"] == 401


def test_make_split_fixture_es_determinista(tmp_path):
    """Genera en una carpeta temporal y compara con los versionados, sin importar el fin de línea."""
    committed = [p.read_text(encoding="utf-8").splitlines() for p in (LEFT, RIGHT)]
    for i in range(2):
        out = tmp_path / str(i)
        subprocess.run([sys.executable, str(VIZ / "make_split_fixture.py"), "--out-dir", str(out)],
                       check=True, capture_output=True)
        assert [(out / p.name).read_text(encoding="utf-8").splitlines() for p in (LEFT, RIGHT)] == committed


def test_split_html_no_carga_nada_de_internet():
    html = (VIZ / "split.html").read_text(encoding="utf-8")
    assert not re.search(r"https?://", html)
    scripts = re.findall(r'<script src="([^"]+)"', html)
    assert "app.js" in scripts, "split.html debe reutilizar buildFrames de app.js"
    assert scripts.index("app.js") < scripts.index("split.js")
    for ref in re.findall(r'(?:src|href)="([^"]+)"', html):
        assert (VIZ / ref).exists(), f"falta {ref}"


def test_split_js_no_copia_build_frames():
    assert "function buildFrames" not in (VIZ / "split.js").read_text(encoding="utf-8")


@pytest.mark.skipif(not shutil.which("node"), reason="node no está instalado")
def test_final_status_en_node():
    script = f"""
    const fs = require("fs");
    const {{ parseJsonl, buildFrames }} = require({json.dumps(str(VIZ / "app.js"))});
    const {{ finalStatus, finalFractions }} = require({json.dumps(str(VIZ / "split.js"))});
    const read = (p) => parseJsonl(fs.readFileSync(p, "utf8"));
    const L = read({json.dumps(str(LEFT))}), R = read({json.dumps(str(RIGHT))});
    console.log(JSON.stringify({{
      left: finalStatus(L), right: finalStatus(R),
      none: finalStatus([{{ source: "proxy", kind: "decision", data: {{}} }}]),
      empty: finalStatus([]),
      other: finalStatus([{{ source: "attacker", kind: "received", data: {{ status: 500 }} }}]),
      fl: finalFractions(buildFrames(L)), fr: finalFractions(buildFrames(R)),
    }}));
    """
    r = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert (r["left"], r["right"], r["none"], r["empty"], r["other"]) == (200, 401, None, None, None)
    assert r["fl"]["SECRET_1"] > r["fr"]["SECRET_1"]


@pytest.mark.skipif(not shutil.which("node"), reason="node no está instalado")
def test_texto_del_resultado_en_node():
    """Tarea 15h: el texto dice cuántos bits juntó el atacante y si la clave ya rotó."""
    real_left = VIZ / "fixtures" / "real_left.jsonl"
    real_right = VIZ / "fixtures" / "real_right.jsonl"
    script = f"""
    const fs = require("fs");
    const {{ parseJsonl }} = require({json.dumps(str(VIZ / "app.js"))});
    const {{ resultText }} = require({json.dumps(str(VIZ / "split.js"))});
    const read = (p) => parseJsonl(fs.readFileSync(p, "utf8"));
    const att = (d) => ({{ source: "attacker", kind: "received", data: d }});
    console.log(JSON.stringify({{
      left: resultText(read({json.dumps(str(real_left))})),
      right: resultText(read({json.dumps(str(real_right))})),
      partial: resultText([att({{ status: 401, bits_known: 144, key_complete: false }})]),
      legacy: resultText([att({{ status: 200 }})]),
      none: resultText([]),
    }}));
    """
    r = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert r["left"] == "El atacante reconstruyó la clave completa (160 bits) y la usa: 200"
    assert re.fullmatch(r"El atacante juntó \d+ bits de una clave que ya rotó: 401", r["right"])
    assert r["partial"] == "El atacante juntó 144 bits, no le alcanza para armar la clave: 401"
    assert r["legacy"] == "El atacante usa la clave: 200"
    assert r["none"] == "Sin intento del atacante"
