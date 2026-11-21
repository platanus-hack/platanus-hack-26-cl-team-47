"""Exporta el grafo de archivos (GFF) para la pantalla dividida (tarea 15e).

    python demo/export_graph.py --out demo/out/graph.json

{"nodes": [{"id", "kind": file|dir|secret|host, "mu", "sd"}], "edges": [{"source", "target"}]}

Usa engine.graph.gff tal cual. Nunca exporta el campo `value` de los secretos.
Orden estable: nodos por id, aristas por (source, target).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.graph.gff import FileGraph, build_graph  # noqa: E402

DEFAULT_WORKSPACE = "demo/repo"
DEFAULT_MANIFEST = "demo/secrets_manifest.json"


def _abs(p: str | Path) -> Path:
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def export_graph(workspace: str = DEFAULT_WORKSPACE, manifest_path: str = DEFAULT_MANIFEST) -> dict:
    ws, mf = _abs(workspace), _abs(manifest_path)
    manifest = json.loads(mf.read_text(encoding="utf-8"))
    secret_ids = {s["secret_id"] for s in manifest.get("secrets", [])}
    hosts = {h for s in manifest.get("secrets", []) for h in s.get("allowed_hosts", [])}

    sens = FileGraph.from_workspace(str(ws), str(mf)).sensitivity()
    G = build_graph(str(ws), manifest)

    def kind(n: str) -> str:
        if n in secret_ids:
            return "secret"
        if n in hosts:
            return "host"
        return "dir" if n.endswith("/") else "file"

    nodes = []
    for n in sorted(G.nodes()):
        mu, sd = sens.get(n, (0.0, 0.0))
        nodes.append({"id": n, "kind": kind(n), "mu": round(float(mu), 4), "sd": round(float(sd), 4)})
    edges = sorted({tuple(sorted((u, v))) for u, v in G.edges() if u != v})
    return {"nodes": nodes, "edges": [{"source": u, "target": v} for u, v in edges]}


def write_graph(out: str | Path, workspace: str = DEFAULT_WORKSPACE, manifest_path: str = DEFAULT_MANIFEST) -> Path:
    out = _abs(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = export_graph(workspace, manifest_path)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(prog="python demo/export_graph.py")
    ap.add_argument("--out", default="demo/out/graph.json")
    ap.add_argument("--workspace", default=DEFAULT_WORKSPACE)
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    args = ap.parse_args()
    p = write_graph(args.out, args.workspace, args.manifest)
    d = json.loads(p.read_text(encoding="utf-8"))
    print(f"{p}: {len(d['nodes'])} nodos, {len(d['edges'])} aristas")


if __name__ == "__main__":
    main()
