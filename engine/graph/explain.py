"""Explicación de un bloqueo por dominadores (tarea 12c, documento v4.0 sección 7.1).

Para un sumidero, los dominadores son las llamadas por las que pasa todo camino desde
una fuente no confiable hasta él: la explicación mínima del bloqueo y el mejor punto de
corte. Se agrega una raíz virtual conectada a las fuentes no confiables que alcanzan el
sumidero y se sube por la cadena de dominadores inmediatos. Como las aristas van hacia
adelante en t, el orden por t es topológico y los dominadores salen en una pasada
(intersección de Cooper, Harvey y Kennedy), sin networkx.

Aristas: las de contenido del DAG; con include_suspicion=True, también las de sospecha
con p >= min_p. El sumidero no cuenta como su propia fuente aunque sea no confiable.
"""

from __future__ import annotations

from urllib.parse import urlsplit

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
    ids = sorted((i for i in dag.order if nodes[i].call.t <= t_sink), key=lambda i: nodes[i].call.t)
    alive = set(ids)
    preds: dict[str, set[str]] = {i: {p for p in nodes[i].parents if p in alive} for i in ids}
    if include_suspicion:
        from .suspicion import RPlus

        sids, _, _, _, _, P = RPlus(dag, graph)._setup(sink_id)
        for a, b in zip(*np.nonzero(P >= min_p)):
            preds[sids[b]].add(sids[a])

    # Llamadas que alcanzan el sumidero (BFS hacia atrás).
    reach = {sink_id}
    stack = [sink_id]
    while stack:
        for p in preds[stack.pop()]:
            if p not in reach:
                reach.add(p)
                stack.append(p)
    reach.discard(sink_id)
    sources = [i for i in ids if i in reach and nodes[i].call.untrusted]
    if not sources:
        return _empty(sink_id)

    # Dominadores en un DAG: el orden por t es topológico, así que basta una pasada.
    # idom(v) = intersección (ancestro común en el árbol de dominadores) de sus predecesores.
    src = set(sources)
    idom: dict = {_ROOT: _ROOT}
    depth: dict = {_ROOT: 0}

    def meet(a, b):
        while a != b:
            while depth[a] > depth[b]:
                a = idom[a]
            while depth[b] > depth[a]:
                b = idom[b]
            if a != b:
                a, b = idom[a], idom[b]
        return a

    for v in ids:
        if v not in reach and v != sink_id:
            continue
        ps = [p for p in preds[v] if p in idom]
        if v in src:
            ps.append(_ROOT)
        if not ps:
            continue  # no lo alcanza ninguna fuente no confiable
        d = ps[0]
        for p in ps[1:]:
            d = meet(d, p)
        idom[v] = d
        depth[v] = depth[d] + 1

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
