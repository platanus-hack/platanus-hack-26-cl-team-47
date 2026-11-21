"""Tests del visor (tarea 15a). Sin navegador."""

import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from contracts import Decision, Event, ToolCall

VIZ = Path(__file__).resolve().parents[1]
FIXTURE = VIZ / "fixtures" / "sample.jsonl"


def events():
    return [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_cada_linea_es_un_event_valido():
    for raw in events():
        ev = Event.model_validate(raw)
        if ev.kind == "tool_call":
            ToolCall.model_validate(ev.data)
        elif ev.kind == "decision":
            Decision.model_validate(ev.data)


def test_fixture_cumple_las_condiciones():
    evs = events()
    calls = [e["data"] for e in evs if e["kind"] == "tool_call"]
    decisions = {e["call_id"]: e["data"] for e in evs if e["kind"] == "decision"}
    rotations = [e for e in evs if e["kind"] == "rotation"]
    t_of = {c["id"]: c["t"] for c in calls}

    assert len(calls) == 40
    assert sum(c["is_sink"] for c in calls) >= 3
    assert sum(c["untrusted"] for c in calls) >= 1
    actions = Counter(d["action"] for d in decisions.values())
    assert set(actions) == {"allow", "block", "rotate+allow", "rotate+block"}

    # Bits por secreto en orden de t.
    ordered = sorted(calls, key=lambda c: c["t"])
    bits = {sid: [decisions[c["id"]]["leak"].get(sid, {}).get("bits", 0.0) for c in ordered]
            for sid in ("SECRET_1", "SECRET_2")}
    for sid, series in bits.items():
        assert max(series) > 0, f"{sid} nunca sube"
        assert any(b > a for a, b in zip(series, series[1:])), f"{sid} no sube"

    # Al menos una rotación tras la cual los bits de ese secreto vuelven a 0.
    assert rotations
    reset = False
    for r in rotations:
        sid, t_rot = r["data"]["secret_id"], t_of[r["call_id"]]
        after = [decisions[c["id"]]["leak"].get(sid, {}).get("bits", 0.0) for c in ordered if c["t"] == t_rot + 1]
        before = bits[sid][t_rot - 1]
        if before > 0 and after and after[0] == 0:
            reset = True
    assert reset, "ninguna rotación devuelve los bits a 0"


def test_make_fixture_es_determinista(tmp_path):
    before = FIXTURE.read_bytes()
    for _ in range(2):
        subprocess.run([sys.executable, str(VIZ / "make_fixture.py")], check=True, capture_output=True)
        assert FIXTURE.read_bytes() == before


def test_index_no_carga_nada_de_internet():
    html = (VIZ / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"https?://", html)
    assert (VIZ / "vendor" / "d3.min.js").stat().st_size > 100_000
    for ref in re.findall(r'(?:src|href)="([^"]+)"', html):
        assert (VIZ / ref).exists(), f"falta {ref}"


@pytest.mark.skipif(not shutil.which("node"), reason="node no está instalado")
def test_build_frames_en_node():
    """buildFrames es pura: se prueba con node sobre el fixture."""
    script = f"""
    const fs = require("fs");
    const {{ parseJsonl, buildFrames, secretIds, summarizeArgs }} = require({json.dumps(str(VIZ / "app.js"))});
    const evs = parseJsonl(fs.readFileSync({json.dumps(str(FIXTURE))}, "utf8"));
    evs.push({{ kind: "otro", source: "agent", data: {{}} }});  // kinds desconocidos se ignoran
    const frames = buildFrames(evs.slice().reverse());          // orden por t aunque el archivo venga desordenado
    console.log(JSON.stringify({{
      n: frames.length,
      ts: frames.map(f => f.t),
      decided: frames.every(f => f.decision && f.decision.action),
      rotations: frames.filter(f => f.rotations.length).map(f => [f.t, f.rotations[0].secret_id]),
      secrets: secretIds(frames),
      maxArgs: Math.max(...frames.map(f => summarizeArgs(f.call.args).length)),
    }}));
    """
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout
    r = json.loads(out)
    assert r["n"] == 40 and r["ts"] == list(range(1, 41))
    assert r["decided"]
    assert r["rotations"] == [[18, "SECRET_1"], [32, "SECRET_2"]]
    assert r["secrets"] == ["SECRET_1", "SECRET_2"]
    assert r["maxArgs"] <= 80
