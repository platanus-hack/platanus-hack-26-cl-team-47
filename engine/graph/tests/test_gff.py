import json
import time
from pathlib import Path

import networkx as nx
import numpy as np
import pytest

from engine.graph.gff import FileGraph, build_graph, posterior, precision

ROOT = Path(__file__).resolve().parents[3]
DEMO = ROOT / "demo" / "repo"
MANIFEST = ROOT / "demo" / "secrets_manifest.json"


@pytest.fixture(scope="module")
def demo():
    return FileGraph.from_workspace(str(DEMO), str(MANIFEST))


def _random_graph(n, seed):
    rng = np.random.default_rng(seed)
    G = nx.connected_watts_strogatz_graph(n, 4, 0.3, seed=seed)
    G = nx.relabel_nodes(G, {i: f"n{i}" for i in G.nodes})
    for u, v in G.edges:
        G[u][v]["weight"] = float(rng.choice([1.0, 2.0, 4.0]))
    return G


def test_conditioning_matches_dense():
    G = _random_graph(50, 7)
    labels = {"n0": 1.0, "n10": 0.0, "n20": 1.0, "n30": 0.0, "n40": 0.5}
    kappa, tau = 0.05, 0.2
    fg = FileGraph(G, labels, kappa, tau)

    Q = precision(G, fg.nodes, kappa).toarray()
    w = tau ** -2
    P = np.zeros(50)
    y = np.zeros(50)
    for n, v in labels.items():
        P[fg.idx[n]] = 1.0
        y[fg.idx[n]] = v
    inv = np.linalg.inv(Q + np.diag(w * P))
    mu_dense = inv @ (w * P * y)
    assert np.max(np.abs(fg.mu - mu_dense)) < 1e-8
    assert np.max(np.abs(fg.var - np.diag(inv))) < 1e-8


def test_precision_is_laplacian_plus_kappa():
    G = _random_graph(20, 1)
    Q = precision(G, list(G.nodes), 0.05).toarray()
    assert np.allclose(Q, Q.T)
    assert np.allclose(Q.sum(axis=1), 0.05)


def test_hot_and_cold(demo):
    s = demo.sensitivity()
    assert s[".env"][0] > 0.8
    assert s["config/secrets.yaml"][0] > 0.8
    assert s["docs/"][0] < 0.2
    assert s["SECRET_1"][0] > 0.5  # el secreto hereda calor de su archivo
    assert demo.heat()[".env"] == s[".env"][0]


def test_graph_structure():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    G = build_graph(str(DEMO), manifest)
    assert G.has_edge("./", ".env") and G.has_edge("config/", "config/secrets.yaml")
    assert G.has_edge(".env", "SECRET_1") and G.has_edge("SECRET_1", "api.empresa.test")
    assert G[".env"]["SECRET_1"]["weight"] == 4.0
    # tests/test_franjas.py importa app.franjas (layout src/)
    assert G["tests/test_franjas.py"]["src/app/franjas.py"]["weight"] == 2.0
    assert all(not n.startswith(".git/") for n in G.nodes)


def test_imports_tmp(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "a.py").write_text("from . import b\nimport os\n")
    (tmp_path / "pkg" / "b.py").write_text("x = 1\n")
    (tmp_path / "main.py").write_text("from pkg.a import thing\n")
    G = build_graph(str(tmp_path), {"secrets": []})
    assert G.has_edge("pkg/a.py", "pkg/b.py")
    assert G.has_edge("main.py", "pkg/a.py")


def test_uncertainty(demo):
    s = demo.sensitivity()
    far = "src/app/api_client.py"
    assert far not in demo.labels
    assert s[far][1] > s[".env"][1]


def test_jump_far_vs_near(demo):
    near = FileGraph.from_workspace(str(DEMO), str(MANIFEST))
    assert near.touch(["src/app/franjas.py"])["jump"] == 0.0
    j_near = near.touch(["src/app/api_client.py"])["jump"]

    far = FileGraph.from_workspace(str(DEMO), str(MANIFEST))
    far.touch(["docs/onboarding.md"])
    r = far.touch([".env"])
    assert r["jump"] > j_near
    assert r["m"] > 0.8 and r["m_sd"] > 0


def test_touch_ignores_unknown_and_normalizes():
    fg = FileGraph.from_workspace(str(DEMO), str(MANIFEST))
    assert fg.touch(["git", "attacker.test"]) == {"m": 0.0, "m_sd": 0.0, "jump": 0.0}
    r = fg.touch(["docs", "."])
    assert r["m"] < 0.5
    assert fg.touch(["api.empresa.test"])["m"] > 0.5  # host permitido es nodo


def test_window_is_five_calls():
    fg = FileGraph.from_workspace(str(DEMO), str(MANIFEST))
    fg.touch([".env"])
    for _ in range(5):
        fg.touch(["docs/onboarding.md"])
    # .env salió de la ventana: volver a él ya no es salto 0
    assert fg.touch([".env"])["jump"] > 0


def test_touch_latency_200_nodes():
    G = _random_graph(200, 3)
    fg = FileGraph(G, {"n0": 1.0, "n100": 0.0}, 0.05, 0.2)
    rng = np.random.default_rng(0)
    nodes = fg.nodes
    times = []
    for _ in range(100):
        res = [nodes[i] for i in rng.integers(0, 200, size=3)]
        t0 = time.perf_counter()
        fg.touch(res)
        times.append(time.perf_counter() - t0)
    assert max(times) < 0.015


def test_correlation_matches_dense():
    G = _random_graph(50, 11)
    labels = {"n0": 1.0, "n12": 0.0, "n25": 1.0, "n37": 0.0, "n49": 1.0}
    fg = FileGraph(G, labels, 0.05, 0.2)
    Q = precision(G, fg.nodes, 0.05).toarray()
    P = np.zeros(50)
    for n in labels:
        P[fg.idx[n]] = 1.0
    Sigma = np.linalg.inv(Q + np.diag(0.2 ** -2 * P))
    rng = np.random.default_rng(0)
    for _ in range(30):
        u, v = (fg.nodes[i] for i in rng.integers(0, 50, size=2))
        i, j = fg.idx[u], fg.idx[v]
        dense = Sigma[i, j] / np.sqrt(Sigma[i, i] * Sigma[j, j])
        assert abs(fg.correlation(u, v) - dense) < 1e-8
    assert fg.correlation("n3", "n3") == 1.0
    assert -1.0 <= fg.correlation("n0", "n25") <= 1.0


def test_correlation_demo(demo):
    assert demo.correlation(".env", "SECRET_1") > demo.correlation(".env", "docs/onboarding.md")
