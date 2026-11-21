"""Aristas de sospecha y R⁺. Tarea 12.

Arista candidata i -> j: i es fuente (no confiable o lee un secreto) y t_j > t_i.
Se abre con probabilidad p_ij = g · exp(−(t_j − t_i) / τ_s), con g de la tarea
12b (ver suspicion_g): solo el lado que tiene nodos del grafo cuando i es no
confiable o j es un sumidero externo; correlación posterior si ambos tienen nodos.

R⁺(c) = P(existe camino no confiable -> lectura de secreto -> c) con las aristas
de contenido siempre abiertas y las de sospecha independientes. Como en el
nivel 0, «camino» significa que c desciende de una llamada no confiable y de
una lectura de secreto.

Monte Carlo: cada arista de sospecha alimenta un solo nodo (su cabeza), así que
por nodo y muestra basta sortear si se abre alguna arista de las fuentes con
(U y S), solo U o solo S en esa muestra: P(ninguna abierta) = Π(1 − p). Es la
misma distribución que sortear arista por arista, vectorizada sobre las M muestras.
"""

from __future__ import annotations

import itertools

import numpy as np

from .dag import CallDAG
from .gff import FileGraph

MAX_EXACT = 16
_P_MAX = 1.0 - 1e-12


def _nodes(graph: FileGraph, resources: list[str]) -> list[str]:
    out = []
    for r in resources:
        n = graph.node_of(r)
        if n is not None and n not in out:
            out.append(n)
    return out


def _mu01(graph: FileGraph, node: str) -> float:
    return float(np.clip(graph.mu[graph.idx[node]], 0.0, 1.0))


def _side(graph: FileGraph, nodes: list[str]) -> float:
    """max sobre los nodos de sqrt(max(0, μ)); 0 si no hay nodos."""
    return max((float(np.sqrt(max(0.0, graph.mu[graph.idx[n]]))) for n in nodes), default=0.0)


def suspicion_g(graph: FileGraph, res_i: list[str], res_j: list[str],
                i_untrusted: bool = False, j_sink: bool = False) -> float:
    """g de la arista i -> j (tarea 12b), recortado a [0, 1]:
    - i no confiable y N_j no vacío: max_v sqrt(μ_v) sobre N_j;
    - i no confiable y j sumidero sin nodos: 0;
    - j sumidero sin nodos y N_i no vacío: max_u sqrt(μ_u) sobre N_i;
    - ambos con nodos: max sqrt(μ_u μ_v) · max(0, ρ_uv);
    - si no, 0.
    """
    a, b = _nodes(graph, res_i), _nodes(graph, res_j)
    if i_untrusted:
        g = _side(graph, b) if b else 0.0
    elif not b:
        g = _side(graph, a) if (j_sink and a) else 0.0
    elif a:
        g = 0.0
        for u in a:
            for v in b:
                rho = graph.correlation(u, v)
                if rho > 0:
                    g = max(g, float(np.sqrt(_mu01(graph, u) * _mu01(graph, v))) * rho)
    else:
        g = 0.0
    return float(np.clip(g, 0.0, 1.0))


def suspicion_probability(graph: FileGraph, res_i: list[str], res_j: list[str],
                          t_i: int, t_j: int, tau_s: float = 50.0, *,
                          i_untrusted: bool = False, j_sink: bool = False) -> float:
    if t_j <= t_i:
        return 0.0
    g = suspicion_g(graph, res_i, res_j, i_untrusted=i_untrusted, j_sink=j_sink)
    return float(np.clip(g * np.exp(-(t_j - t_i) / tau_s), 0.0, 1.0))


class RPlus:
    def __init__(self, dag: CallDAG, graph: FileGraph, tau_s: float = 50.0, M: int = 200, seed: int = 0):
        self.dag, self.graph = dag, graph
        self.tau_s, self.M, self.seed = tau_s, M, seed

    # --- Estructura común ---------------------------------------------------

    def _setup(self, call_id: str):
        """Llamadas hasta c (orden temporal), etiquetas propias, padres de contenido y P."""
        tc = self.dag.nodes[call_id].call.t
        ids = [i for i in self.dag.order if self.dag.nodes[i].call.t <= tc]
        ids.sort(key=lambda i: self.dag.nodes[i].call.t)
        pos = {cid: k for k, cid in enumerate(ids)}
        n = len(ids)
        own_U = np.array([self.dag.nodes[i].call.untrusted for i in ids], dtype=bool)
        own_S = np.array([bool(self.dag.nodes[i].secrets_read) for i in ids], dtype=bool)
        parents = [[pos[p] for p in self.dag.nodes[i].parents if p in pos] for i in ids]
        t = np.array([self.dag.nodes[i].call.t for i in ids], dtype=float)

        # Probabilidades de sospecha, vectorizadas por nodo del grafo.
        g = self.graph
        touched = [[g.idx[x] for x in _nodes(g, self.dag.nodes[i].call.resources)] for i in ids]
        T = sorted({x for tt in touched for x in tt})
        src = own_U | own_S
        sink = np.array([self.dag.nodes[i].call.is_sink for i in ids], dtype=bool)
        has = np.array([bool(tt) for tt in touched], dtype=bool)
        side = np.array([max((np.sqrt(max(0.0, g.mu[x])) for x in tt), default=0.0) for tt in touched])

        G = np.zeros((n, n))
        # Ambos con nodos e i confiable: correlación posterior.
        if T:
            loc = {x: k for k, x in enumerate(T)}
            mu = np.clip(g.mu[T], 0.0, 1.0)
            Gm = np.sqrt(np.outer(mu, mu)) * np.maximum(0.0, g.corr_block(T))
            R = np.zeros((n, len(T)))
            for i in np.nonzero(src & ~own_U & has)[0]:
                R[i] = Gm[[loc[x] for x in touched[i]]].max(axis=0)
            for j in np.nonzero(has)[0]:
                G[:, j] = R[:, [loc[x] for x in touched[j]]].max(axis=1)
        # i no confiable y N_j no vacío: sensibilidad de lo que toca j.
        G[own_U] = 0.0
        G[np.ix_(own_U, has)] = side[has][None, :]
        # j sumidero sin nodos, i confiable con nodos: sensibilidad de lo que leyó i.
        ext = sink & ~has
        rows = ~own_U & has
        G[np.ix_(rows, ext)] = side[rows][:, None]

        later = t[None, :] > t[:, None]
        decay = np.exp(-np.maximum(t[None, :] - t[:, None], 0.0) / self.tau_s)
        P = np.clip(np.clip(G, 0.0, 1.0) * decay * later * src[:, None], 0.0, 1.0)
        return ids, pos[call_id], own_U, own_S, parents, P

    def _trivial(self, call_id: str):
        node = self.dag.nodes[call_id]
        if not node.call.is_sink:
            return 0.0
        if node.U and node.S:  # camino solo con aristas de contenido
            return 1.0
        return None

    # --- Exacto -------------------------------------------------------------

    def exact(self, call_id: str) -> float:
        triv = self._trivial(call_id)
        if triv is not None:
            return triv
        ids, c, own_U, own_S, parents, P = self._setup(call_id)
        n = len(ids)
        edges = [(i, j, P[i, j]) for i, j in zip(*np.nonzero(P))]
        certain = [(i, j) for i, j, p in edges if p >= 1.0]
        uncertain = [(i, j, p) for i, j, p in edges if p < 1.0]
        if len(uncertain) > MAX_EXACT:
            raise ValueError(f"{len(uncertain)} aristas inciertas: más de {MAX_EXACT}")
        total = 0.0
        for mask in itertools.product((False, True), repeat=len(uncertain)):
            prob = 1.0
            inc: list[list[int]] = [list(parents[j]) for j in range(n)]
            for i, j in certain:
                inc[j].append(i)
            for (i, j, p), on in zip(uncertain, mask):
                prob *= p if on else (1.0 - p)
                if on:
                    inc[j].append(i)
            if prob == 0.0:
                continue
            U = own_U.copy()
            S = own_S.copy()
            for j in range(n):
                for i in inc[j]:
                    U[j] |= U[i]
                    S[j] |= S[i]
            if U[c] and S[c]:
                total += prob
        return total

    # --- Monte Carlo --------------------------------------------------------

    def estimate(self, call_id: str) -> dict:
        triv = self._trivial(call_id)
        if triv is not None:
            return {"R_plus": triv, "se": 0.0, "n_uncertain": 0}
        ids, c, own_U, own_S, parents, P = self._setup(call_id)
        n, M = len(ids), self.M
        n_unc = int(np.count_nonzero((P > 0) & (P < 1)))
        rng = np.random.default_rng(self.seed)
        logq = np.log1p(-np.minimum(P, _P_MAX))  # log(1 − p); p = 1 queda en 1 − 1e-12

        U = np.zeros((n, M), dtype=bool)
        S = np.zeros((n, M), dtype=bool)
        for j in range(n):
            u = np.full(M, own_U[j])
            s = np.full(M, own_S[j])
            if parents[j]:
                u |= U[parents[j]].any(axis=0)
                s |= S[parents[j]].any(axis=0)
            srcs = np.nonzero(P[:, j] > 0)[0]
            if len(srcs):
                L = logq[srcs, j]
                Ui, Si = U[srcs], S[srcs]
                both = (Ui & Si).astype(float)
                uo = (Ui & ~Si).astype(float)
                so = (Si & ~Ui).astype(float)
                lb, lu, ls = L @ both, L @ uo, L @ so
                r = rng.random((3, M))
                open_b = r[0] < -np.expm1(lb)
                u |= open_b | (r[1] < -np.expm1(lu))
                s |= open_b | (r[2] < -np.expm1(ls))
            U[j], S[j] = u, s
        hit = U[c] & S[c]
        R = float(hit.mean())
        return {"R_plus": R, "se": float(np.sqrt(R * (1.0 - R) / M)), "n_uncertain": n_unc}
