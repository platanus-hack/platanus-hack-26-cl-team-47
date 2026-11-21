"""Explicación de un bloqueo por dominadores (tarea 12c, documento v4.0 sección 7.1).

Para un sumidero, los dominadores son las llamadas por las que pasa todo camino desde
una fuente no confiable hasta él: la explicación mínima del bloqueo y el mejor punto de
corte. Se agrega una raíz virtual conectada a las fuentes no confiables que alcanzan el
sumidero y se sube por la cadena de dominadores inmediatos.

Aristas: las de contenido del DAG; con include_suspicion=True, también las de sospecha
con p >= min_p. El sumidero no cuenta como su propia fuente aunque sea no confiable.
"""

from __future__ import annotations

from urllib.parse import urlsplit

import networkx as nx
import numpy as np

from .dag import CallDAG
from .gff import FileGraph

_ROOT = ("__raiz__",)


def _label(call) -> str:
    args = call.args if isinstance(call.args, dict) else {}
    res = call.resources[0] if call.resources else ""
    if call.tool == "read_file":
        text = f"leer {args.get('path', res)}"
    elif call.tool == "list_dir":
        text = f"listar {args.get('path', res)}"
    elif call.tool == "http_request":
        host = urlsplit(str(args.get("url", ""))).hostname or res
        text = f"{str(args.get('method', 'GET')).upper()} {host}"
    elif call.tool == "git":
        sub = next((a for a in args.get("args") or [] if not str(a).startswith("-")), "")
        text = f"git {sub}".strip()
    elif call.tool == "github_issue":
        text = f"crear issue en {args.get('repo', 'github.test')}"
    elif call.tool == "github_comment":
        text = f"comentar #{args.get('number', '?')} en {args.get('repo', 'github.test')}"
    else:
        text = f"{call.tool} {res}".strip()
    return text + (" (no confiable)" if call.untrusted else "")


def _empty(sink_id: str) -> dict:
    return {"sink": sink_id, "sources": [], "dominators": [], "explanation": ""}


def dominators(dag: CallDAG, sink_id: str, include_suspicion: bool = False,
               graph: FileGraph | None = None, min_p: float = 0.5) -> dict:
    if include_suspicion and graph is None:
        raise ValueError("include_suspicion=True requiere graph")
    nodes = dag.nodes
    t_sink = nodes[sink_id].call.t
    ids = [i for i in dag.order if nodes[i].call.t <= t_sink]

    G = nx.DiGraph()
    G.add_nodes_from(ids)
    for j in ids:
        for i in nodes[j].parents:
            if i in G:
                G.add_edge(i, j)
    if include_suspicion:
        from .suspicion import RPlus

        sids, _, _, _, _, P = RPlus(dag, graph)._setup(sink_id)
        for a, b in zip(*np.nonzero(P >= min_p)):
            G.add_edge(sids[a], sids[b])

    reach = nx.ancestors(G, sink_id)
    sources = sorted((i for i in reach if nodes[i].call.untrusted), key=lambda i: nodes[i].call.t)
    if not sources:
        return _empty(sink_id)

    sub = G.subgraph(reach | {sink_id}).copy()
    sub.add_node(_ROOT)
    sub.add_edges_from((_ROOT, s) for s in sources)
    idom = nx.immediate_dominators(sub, _ROOT)
    chain = []
    n = sink_id
    while n != _ROOT:
        chain.append(n)
        n = idom[n]
    chain.sort(key=lambda i: nodes[i].call.t)
    return {
        "sink": sink_id,
        "sources": sources,
        "dominators": chain,
        "explanation": " → ".join(_label(nodes[i].call) for i in chain),
    }
