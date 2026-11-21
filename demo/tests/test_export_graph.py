"""Tests de demo/export_graph.py (tarea 15e)."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from demo.export_graph import export_graph  # noqa: E402

MANIFEST = ROOT / "demo" / "secrets_manifest.json"
REAL_GRAPH = ROOT / "demo" / "viz" / "fixtures" / "real_graph.json"


def nodes_by_id(g):
    return {n["id"]: n for n in g["nodes"]}


def test_nodos_y_kinds():
    n = nodes_by_id(export_graph())
    expected = {".env": "file", "config/secrets.yaml": "file", "docs/": "dir",
                "SECRET_1": "secret", "api.empresa.test": "host"}
    for node_id, kind in expected.items():
        assert node_id in n, f"falta {node_id}"
        assert n[node_id]["kind"] == kind
    assert n[".env"]["mu"] > 0.8
    assert n["docs/"]["mu"] < 0.2
    assert set(n[".env"]) == {"id", "kind", "mu", "sd"}


def test_aristas_validas_y_orden_estable():
    g = export_graph()
    ids = [x["id"] for x in g["nodes"]]
    assert ids == sorted(ids)
    pairs = [(e["source"], e["target"]) for e in g["edges"]]
    assert pairs == sorted(pairs)
    assert all(s in ids and t in ids for s, t in pairs)
    assert ("config/", "config/secrets.yaml") in pairs


def test_sin_valores_de_secretos():
    text = json.dumps(export_graph())
    for s in json.loads(MANIFEST.read_text(encoding="utf-8"))["secrets"]:
        assert s["value"] not in text
    assert '"value"' not in text


def test_dos_exportaciones_identicas():
    assert json.dumps(export_graph()) == json.dumps(export_graph())


def test_fixture_real_graph_al_dia():
    assert json.loads(REAL_GRAPH.read_text(encoding="utf-8")) == export_graph()


def test_cli_y_run_split_escriben_graph(tmp_path):
    out = tmp_path / "g.json"
    r = subprocess.run([sys.executable, str(ROOT / "demo" / "export_graph.py"), "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(out.read_text(encoding="utf-8")) == export_graph()

    r = subprocess.run([sys.executable, str(ROOT / "demo" / "run_split.py"), "--out-dir", str(tmp_path / "o")],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads((tmp_path / "o" / "graph.json").read_text(encoding="utf-8")) == export_graph()
