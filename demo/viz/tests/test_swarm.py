"""Visualización de la demo del enjambre (tarea 15k). Sin navegador."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

VIZ = Path(__file__).resolve().parents[1]


def test_split_js_conoce_demo_enjambre():
    js = (VIZ / "split.js").read_text(encoding="utf-8")
    assert "enjambre" in js and "fixtures/swarm_left.jsonl" in js and "fixtures/swarm_right.jsonl" in js
    for text in ("Cuenta por agente", "Cuenta global", "agentes se reparten la fuga",
                 "Lo máximo que ve un monitor por agente"):
        assert text in js


def test_home_enlaza_demo_enjambre():
    html = (VIZ / "home.html").read_text(encoding="utf-8")
    assert 'href="split.html?demo=enjambre"' in html and "Ver la demo del enjambre" in html
    assert 'href="split.html"' in html


def test_fixtures_del_enjambre_existen():
    for name in ("swarm_left.jsonl", "swarm_right.jsonl"):
        assert (VIZ / "fixtures" / name).stat().st_size > 0


@pytest.mark.skipif(not shutil.which("node"), reason="node no está instalado")
def test_agente_y_maximo_por_agente_en_node():
    script = """
global.bitsAt = (f, sid) => (f.decision.leak[sid] || {}).bits || 0;
const s = require(%s);
const fr = (id, b) => ({ call: { id }, decision: { leak: { S: { bits: b } } } });
console.log(JSON.stringify({
  a: s.agentOf("a3-0032"), none: s.agentOf("c12"),
  max: s.maxAgentBits([fr("a1-0001", 8), fr("a2-0002", 16), fr("a1-0003", 4), fr("a2-0004", 0)], "S"),
  demo: s.DEMOS.enjambre.left,
}));
""" % json.dumps(str(VIZ / "split.js"))
    r = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True,
                                  encoding="utf-8", check=True).stdout)
    assert r == {"a": "a3", "none": None, "max": [8, 16, 16, 4], "demo": "fixtures/swarm_left.jsonl"}
