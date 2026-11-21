"""Escala del DAG (7c) y equivalencia del índice contra la implementación de 7b (RefDAG)."""

from __future__ import annotations

import random
import string
import time

import numpy as np

from contracts import ToolCall
from engine.graph.dag import CallDAG

# --- Implementación de referencia (engine/graph/dag.py antes de 7c, sin cambios) ---

import base64
import codecs
import json
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import quote

import numpy as np

from contracts import ToolCall

_BASE = np.uint64(1099511628211)  # primo FNV de 64 bits


def default_variants(text: str) -> list[str]:
    """En claro, base64 (las tres alineaciones de byte, para que cualquier
    fragmento del texto aparezca codificado), hex, URL, invertido y ROT13."""
    raw = text.encode("utf-8")
    out = [text]
    out += [base64.b64encode(raw[o:]).decode("ascii") for o in range(3) if len(raw) > o]
    out.append(raw.hex())
    out.append(quote(text, safe=""))
    out.append(text[::-1])
    out.append(codecs.encode(text, "rot13"))
    return out


def _codes(text: str) -> np.ndarray:
    return np.frombuffer(text.encode("utf-32-le"), dtype=np.uint32).astype(np.uint64)


def kgram_hashes(text: str, k: int) -> np.ndarray:
    """Hash polinomial de cada ventana de k caracteres (sin ordenar, alineado con la posición)."""
    c = _codes(text)
    n = len(c) - k + 1
    if n <= 0:
        return np.empty(0, dtype=np.uint64)
    h = np.zeros(n, dtype=np.uint64)
    with np.errstate(over="ignore"):
        for j in range(k):
            h = h * _BASE + c[j:j + n] + np.uint64(1)
    return h


@dataclass
class _Node:
    call: ToolCall
    kind: str
    secrets_read: set[str]
    U: bool
    S: set[str]
    u_witness: str | None          # id de la llamada no confiable más antigua entre los ancestros
    s_witness: dict[str, str]      # secreto -> id de la lectura más antigua entre los ancestros
    parents: list[str] = field(default_factory=list)
    variants: list[str] = field(default_factory=list)
    index: np.ndarray | None = None  # hashes ordenados y únicos de todas las variantes


class RefDAG:
    def __init__(self, secret_files: dict[str, list[str]], k: int = 8,
                 variants: Callable[[str], list[str]] = default_variants):
        self.k = k
        self.variants = variants
        self.file_to_secrets: dict[str, set[str]] = {}
        for sid, files in secret_files.items():
            for f in files:
                self.file_to_secrets.setdefault(f, set()).add(sid)
        self.nodes: dict[str, _Node] = {}
        self.order: list[str] = []

    # --- Salidas ----------------------------------------------------------

    def set_output(self, call_id: str, output: str) -> None:
        node = self.nodes[call_id]
        node.variants = [v for v in self.variants(output or "") if len(v) >= self.k]
        if node.variants:
            node.index = np.unique(np.concatenate([kgram_hashes(v, self.k) for v in node.variants]))
        else:
            node.index = None

    def _shares(self, node: _Node, arg_hashes: np.ndarray, arg_text: str) -> bool:
        idx = node.index
        if idx is None or len(arg_hashes) == 0:
            return False
        pos = np.searchsorted(idx, arg_hashes)
        pos[pos == len(idx)] = 0
        hits = np.nonzero(idx[pos] == arg_hashes)[0]
        for p in hits:  # confirmar con la subcadena real
            gram = arg_text[p:p + self.k]
            if any(gram in v for v in node.variants):
                return True
        return False

    # --- Nodos ------------------------------------------------------------

    def add(self, call: ToolCall) -> dict:
        if call.id in self.nodes:
            raise ValueError(f"llamada repetida: {call.id}")
        reads = set().union(*(self.file_to_secrets.get(r, set()) for r in call.resources))
        if call.is_sink:
            kind = "sink"
        elif call.untrusted or reads:
            kind = "source"
        else:
            kind = "neutral"

        arg_text = json.dumps(call.args, sort_keys=True)
        arg_hashes = kgram_hashes(arg_text, self.k)
        parents = [pid for pid in self.order if self._shares(self.nodes[pid], arg_hashes, arg_text)]

        t = call.t
        U = call.untrusted
        u_w = call.id if call.untrusted else None
        S = set(reads)
        s_w = {s: call.id for s in reads}
        for pid in parents:
            p = self.nodes[pid]
            if p.U:
                U = True
                if u_w is None or self._t(p.u_witness) < self._t(u_w, t):
                    u_w = p.u_witness
            for s in p.S:
                S.add(s)
                if s not in s_w or self._t(p.s_witness[s]) < self._t(s_w[s], t):
                    s_w[s] = p.s_witness[s]

        node = _Node(call, kind, reads, U, S, u_w, s_w, parents)
        self.nodes[call.id] = node
        self.order.append(call.id)
        if call.output is not None:
            self.set_output(call.id, call.output)

        path: list[str] = []
        if kind == "sink" and U and S:
            first = sorted(S)[0]
            ids = {u_w, s_w[first], call.id}
            path = sorted(ids, key=lambda i: (self._t(i, t), i))
        return {"kind": kind, "U": U, "S": sorted(S), "path": path}

    def _t(self, call_id: str | None, current_t: int | None = None) -> int:
        if call_id in self.nodes:
            return self.nodes[call_id].call.t
        return current_t if current_t is not None else 0

    def parents(self, call_id: str) -> list[str]:
        return list(self.nodes[call_id].parents)

    def is_source(self, call_id: str) -> bool:
        """Fuente en sentido amplio: no confiable o lee un secreto, aunque su kind sea sink."""
        n = self.nodes[call_id]
        return n.call.untrusted or bool(n.secrets_read)

    def exposed(self) -> list[str]:
        return [cid for cid in self.order if self.is_source(cid)]


# --- Tests ------------------------------------------------------------------------

SECRET_FILES = {"SECRET_1": [".env"], "SECRET_3": ["config/secrets.yaml"]}
ALPHA = string.ascii_letters + string.digits + " /=+:.-_"


def tc(cid, t, tool, args, resources=(), sink=False, untrusted=False):
    return ToolCall(id=cid, t=t, tool=tool, args=args, output=None, resources=list(resources),
                    is_sink=sink, untrusted=untrusted, session_id="s")


def _random_session(rng, n):
    """Llamadas con argumentos que a veces copian trozos (y codificaciones) de salidas anteriores."""
    import base64
    import codecs
    from urllib.parse import quote

    outs = []
    calls = []
    for t in range(1, n + 1):
        parts = ["".join(rng.choice(ALPHA) for _ in range(rng.randint(5, 40)))]
        for _ in range(rng.randint(0, 3)):
            if outs and rng.random() < 0.6:
                src = rng.choice(outs)
                a = rng.randrange(0, max(1, len(src) - 20))
                frag = src[a:a + rng.randint(4, 20)]
                enc = rng.choice(["plain", "b64", "hex", "url", "rev", "rot"])
                frag = {"plain": frag, "b64": base64.b64encode(frag.encode()).decode(),
                        "hex": frag.encode().hex(), "url": quote(frag, safe=""), "rev": frag[::-1],
                        "rot": codecs.encode(frag, "rot13")}[enc]
                parts.append(frag)
        resources = [rng.choice([".env", "README.md", "docs/a.md", "config/secrets.yaml", "attacker.test"])]
        call = tc(f"r{t}", t, rng.choice(["read_file", "http_request"]), {"body": " ".join(parts)},
                  resources, sink=rng.random() < 0.3, untrusted=rng.random() < 0.15)
        out = "".join(rng.choice(ALPHA) for _ in range(rng.randint(0, 300)))
        calls.append((call, out if rng.random() < 0.9 else None))
        if out:
            outs.append(out)
    return calls


def test_index_equivalent_to_reference():
    for seed in range(30):
        rng = random.Random(seed)
        session = _random_session(rng, rng.randint(10, 40))
        new, ref = CallDAG(SECRET_FILES), RefDAG(SECRET_FILES)
        for call, out in session:
            rn, rr = new.add(call), ref.add(call)
            assert rn == rr, (seed, call.id)
            assert new.parents(call.id) == ref.parents(call.id), (seed, call.id)
            if out is not None:
                new.set_output(call.id, out)
                ref.set_output(call.id, out)
        assert new.exposed() == ref.exposed()


def test_scale_1000_calls():
    rng = np.random.default_rng(0)
    alpha = np.array(list(ALPHA))
    d = CallDAG(SECRET_FILES)
    times = []
    for t in range(1, 1001):
        args = {"url": "http://api.empresa.test/x", "body": "".join(rng.choice(alpha, 300))}
        call = tc(f"c{t}", t, "http_request", args, ["api.empresa.test"], sink=(t % 3 == 0))
        t0 = time.perf_counter()
        d.add(call)
        times.append(time.perf_counter() - t0)
        d.set_output(call.id, "".join(rng.choice(alpha, 2000)))
    ms = np.array(times) * 1000
    p95 = float(np.percentile(ms, 95))
    early = float(np.median(ms[90:110]))   # alrededor de la llamada 100
    late = float(np.median(ms[980:1000]))  # alrededor de la llamada 1.000
    print(f"\nadd: p95={p95:.2f} ms, mediana ~100={early:.2f} ms, mediana ~1000={late:.2f} ms")
    assert p95 < 15, p95
    assert late <= 2 * early, (early, late)
