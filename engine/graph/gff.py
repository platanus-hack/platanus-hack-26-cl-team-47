"""Grafo de archivos con campo libre gaussiano (GFF). Tarea 7a.

G_R no dirigido: archivos, directorios (terminan en "/", la raíz es "./"),
secretos del manifiesto y hosts permitidos. Q = D − A + κI.
Posterior con etiquetas (hot = 1, cold = 0) y ruido τ:
    Q_post = Q + τ⁻² P_B,   Q_post μ = τ⁻² P_B y_B,   var = diag(Q_post⁻¹).
"""

from __future__ import annotations

import ast
import json
import os
from collections import deque
from pathlib import Path
from typing import Iterable

import networkx as nx
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import splu

ROOT_NODE = "./"
WINDOW = 5
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".pytest_cache"}


# --- Construcción del grafo ------------------------------------------------

def _walk(root: Path) -> tuple[list[str], list[str]]:
    """Devuelve (directorios, archivos) relativos a root en formato posix."""
    dirs, files = [], []
    for cur, dnames, fnames in os.walk(root):
        dnames[:] = sorted(d for d in dnames if d not in SKIP_DIRS)
        rel = Path(cur).relative_to(root).as_posix()
        if rel != ".":
            dirs.append(rel + "/")
        for f in sorted(fnames):
            files.append((Path(rel) / f).as_posix() if rel != "." else f)
    return dirs, files


def _parent(node: str) -> str:
    p = Path(node.rstrip("/")).parent.as_posix()
    return ROOT_NODE if p == "." else p + "/"


def _module_index(py_files: list[str]) -> dict[str, str]:
    """Nombre de módulo -> archivo. Indexa todos los sufijos del camino punteado
    (src.app.x, app.x, x) para soportar el layout src/; un paquete es su __init__.py."""
    index: dict[str, str] = {}
    for f in py_files:
        parts = f[:-3].split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        for i in range(len(parts)):
            index.setdefault(".".join(parts[i:]), f)
    return index


def _imports(root: Path, f: str, index: dict[str, str]) -> set[str]:
    try:
        tree = ast.parse((root / f).read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    pkg = f.split("/")[:-1]
    found: set[str] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                up = pkg[: len(pkg) - (node.level - 1)] if node.level > 1 else pkg
                base = ".".join([*up, base] if base else up)
            names = [base] + [f"{base}.{a.name}" if base else a.name for a in node.names]
        for n in names:
            # El módulo importado o su paquete más cercano dentro del repo.
            parts = n.split(".")
            for i in range(len(parts), 0, -1):
                target = index.get(".".join(parts[:i]))
                if target:
                    if target != f:
                        found.add(target)
                    break
    return found


def build_graph(root: str, manifest: dict, C_tree=1.0, C_import=2.0, C_ref=4.0) -> nx.Graph:
    rootp = Path(root)
    G = nx.Graph()
    G.add_node(ROOT_NODE, kind="dir")
    dirs, files = _walk(rootp)
    for d in dirs:
        G.add_node(d, kind="dir")
    for f in files:
        G.add_node(f, kind="file")
    for n in dirs + files:
        G.add_edge(_parent(n), n, weight=C_tree)

    py = [f for f in files if f.endswith(".py")]
    index = _module_index(py)
    for f in py:
        for g in _imports(rootp, f, index):
            w = G[f][g]["weight"] if G.has_edge(f, g) else 0.0
            G.add_edge(f, g, weight=w + C_import)

    for s in manifest.get("secrets", []):
        sid = s["secret_id"]  # el campo `value` nunca se lee
        G.add_node(sid, kind="secret")
        for path in s.get("files", []):
            if path in G:
                G.add_edge(path, sid, weight=C_ref)
        for host in s.get("allowed_hosts", []):
            G.add_node(host, kind="host")
            G.add_edge(sid, host, weight=C_ref)
    return G


def _label_node(G: nx.Graph, path: str) -> str | None:
    p = path.rstrip("/")
    if p in ("", "."):
        return ROOT_NODE
    if p + "/" in G:
        return p + "/"
    return p if p in G else None


# --- Posterior --------------------------------------------------------------

def posterior(Q: sp.spmatrix, labels: dict[int, float], tau: float) -> tuple[np.ndarray, np.ndarray]:
    """μ y varianza marginal con factorización dispersa LU."""
    n = Q.shape[0]
    w = tau ** -2
    pb = np.zeros(n)
    yb = np.zeros(n)
    for i, y in labels.items():
        pb[i] = 1.0
        yb[i] = y
    Qp = (Q + sp.diags(w * pb)).tocsc()
    lu = splu(Qp)
    mu = lu.solve(w * pb * yb)
    var = np.empty(n)
    block = 256
    for start in range(0, n, block):
        stop = min(n, start + block)
        E = np.zeros((n, stop - start))
        E[np.arange(start, stop), np.arange(stop - start)] = 1.0
        var[start:stop] = lu.solve(E)[np.arange(start, stop), np.arange(stop - start)]
    return mu, var


def precision(G: nx.Graph, nodes: list[str], kappa: float) -> sp.csr_matrix:
    A = nx.to_scipy_sparse_array(G, nodelist=nodes, weight="weight", format="csr")
    A = sp.csr_matrix(A)
    D = sp.diags(np.asarray(A.sum(axis=1)).ravel())
    return (D - A + kappa * sp.identity(len(nodes))).tocsr()


class FileGraph:
    def __init__(self, G: nx.Graph, labels: dict[str, float], kappa=0.05, tau=0.2):
        self.G = G
        self.nodes: list[str] = list(G.nodes)
        self.idx = {n: i for i, n in enumerate(self.nodes)}
        self.kappa, self.tau = kappa, tau
        self.labels = {n: y for n, y in labels.items() if n in self.idx}
        self.Q = precision(G, self.nodes, kappa)
        self.mu, self.var = posterior(self.Q, {self.idx[n]: y for n, y in self.labels.items()}, tau)
        self.sd = np.sqrt(np.maximum(self.var, 0.0))
        self._recent: deque[list[str]] = deque(maxlen=WINDOW)

    @classmethod
    def from_workspace(cls, root: str, manifest_path: str, C_tree=1.0, C_import=2.0,
                       C_ref=4.0, kappa=0.05, tau=0.2) -> "FileGraph":
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        G = build_graph(root, manifest, C_tree, C_import, C_ref)
        labels: dict[str, float] = {}
        for p in manifest.get("cold_paths", []):
            n = _label_node(G, p)
            if n:
                labels[n] = 0.0
        for p in manifest.get("hot_paths", []):
            n = _label_node(G, p)
            if n:
                labels[n] = 1.0
        return cls(G, labels, kappa, tau)

    # --- Lecturas -------------------------------------------------------

    def sensitivity(self) -> dict[str, tuple[float, float]]:
        return {n: (float(self.mu[i]), float(self.sd[i])) for n, i in self.idx.items()}

    def heat(self) -> dict[str, float]:
        return {n: float(self.mu[i]) for n, i in self.idx.items()}

    def node_of(self, resource: str) -> str | None:
        """Traduce un recurso del ToolCall a un nodo (acepta 'docs' por 'docs/' y '.' por la raíz)."""
        if resource in self.idx:
            return resource
        return _label_node(self.G, resource)

    def _hops(self, sources: Iterable[str], targets: set[str]) -> float:
        """Camino más corto sin pesos entre cualquier par (BFS multi-origen)."""
        frontier = deque((s, 0) for s in sources)
        seen = {s for s, _ in frontier}
        while frontier:
            n, d = frontier.popleft()
            if n in targets:
                return float(d)
            for nb in self.G.adj[n]:
                if nb not in seen:
                    seen.add(nb)
                    frontier.append((nb, d + 1))
        return float(len(self.nodes))  # componentes distintas: cota superior finita

    def touch(self, resources: list[str]) -> dict:
        touched = [n for n in (self.node_of(r) for r in resources) if n is not None]
        touched = list(dict.fromkeys(touched))
        region = {n for call in self._recent for n in call}
        self._recent.append(touched)
        if not touched:
            return {"m": 0.0, "m_sd": 0.0, "jump": 0.0}
        best = max(touched, key=lambda n: self.mu[self.idx[n]])
        i = self.idx[best]
        jump = self._hops(touched, region) if region else 0.0
        return {"m": float(self.mu[i]), "m_sd": float(self.sd[i]), "jump": jump}
