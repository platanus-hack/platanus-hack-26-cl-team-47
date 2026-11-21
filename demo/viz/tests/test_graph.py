"""Tests de la franja del grafo en la pantalla dividida (tarea 15e). Sin navegador."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

VIZ = Path(__file__).resolve().parents[1]


def test_split_html_sigue_local_y_carga_graph_js():
    html = (VIZ / "split.html").read_text(encoding="utf-8")
    assert not re.search(r"https?://", html)
    scripts = re.findall(r'<script src="([^"]+)"', html)
    assert scripts.index("app.js") < scripts.index("graph.js") < scripts.index("split.js")
    assert re.search(r'id="graph-strip"[^>]*hidden', html), "sin ?graph= la franja queda oculta"


def test_real_graph_es_json_valido():
    g = json.loads((VIZ / "fixtures" / "real_graph.json").read_text(encoding="utf-8"))
    assert g["nodes"] and g["edges"]


@pytest.mark.skipif(not shutil.which("node"), reason="node no está instalado")
def test_funciones_puras_en_node():
    script = f"""
    const fs = require("fs");
    const {{ parseJsonl, buildFrames }} = require({json.dumps(str(VIZ / "app.js"))});
    const {{ touchedUpTo, pathBoxes, resolveNode }} = require({json.dumps(str(VIZ / "graph.js"))});
    const frames = buildFrames(parseJsonl(fs.readFileSync({json.dumps(str(VIZ / "fixtures" / "real_right.jsonl"))}, "utf8")));
    const ids = new Set(["./", "docs/", ".env", "src/app/franjas.py"]);
    console.log(JSON.stringify({{
      t2: [...touchedUpTo(frames, 2)].sort(),
      t3: [...touchedUpTo(frames, 3)].sort(),
      boxes: pathBoxes(frames, {{ path: ["c3", "c24", "nope"] }}),
      empty: pathBoxes(frames, {{ path: [] }}),
      none: pathBoxes(frames, null),
      res: [resolveNode(ids, "docs"), resolveNode(ids, "."), resolveNode(ids, ".env"),
            resolveNode(ids, "attacker.test"), resolveNode(ids, "docs/")],
    }}));
    """
    r = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert ".env" not in r["t2"] and ".env" in r["t3"]
    assert set(r["t2"]) <= set(r["t3"])
    assert r["boxes"][0] == {"id": "c3", "tool": "read_file", "resource": ".env"}
    assert r["boxes"][1] == {"id": "c24", "tool": "http_request", "resource": "attacker.test"}
    assert r["boxes"][2] == {"id": "nope", "tool": "?", "resource": ""}
    assert r["empty"] == [] and r["none"] == []
    assert r["res"] == ["docs/", "./", ".env", None, "docs/"]
