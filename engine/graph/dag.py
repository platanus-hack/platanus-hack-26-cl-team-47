"""DAG de llamadas con aristas de contenido. Tareas 7b y 7c.

Arista i -> j (i anterior a j) si json.dumps(args_j, sort_keys=True) comparte
una subcadena de k o más caracteres con alguna variante de la salida de i.
Etiquetas heredadas: U (desciende de algo no confiable) y S (secretos leídos).
Patrón peligroso del nivel 0: sumidero con U y S no vacío -> path.

U viaja por cualquier arista de contenido. Con `secret_values`, S de un secreto s
viaja por la arista i -> j solo si el material compartido incluye k o más
caracteres seguidos del valor vigente de s (en claro o en una de sus variantes);
sin `secret_values`, S viaja por cualquier arista (comportamiento de 7b). Una
llamada lee s si toca su archivo o si su salida contiene k caracteres seguidos
del valor de s.

Límite conocido: un envío en fragmentos menores que k no crea arista de
contenido. Esos casos los cubren el motor de bits y la rotación, no el DAG.

Índice: un índice global hash de k-grama -> llamadas, alimentado en set_output
con todas las variantes de la salida. Son bloques ordenados de numpy que se
fusionan por tamaño (como un árbol LSM): consultar cuesta O(m · log N) para
m k-gramas de argumentos, sin recorrer las llamadas anteriores. Toda coincidencia
de hash se confirma con la subcadena real antes de crear la arista.
"""

from __future__ import annotations

import base64
import codecs
import json
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import quote

import numpy as np

from contracts import ToolCall

_BASE = np.uint64(1099511628211)  # primo FNV de 64 bits
MAX_INDEXED_CHARS = 200_000


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


class _KGramIndex:
    """hash de k-grama -> índices de llamada, en bloques ordenados que se fusionan por tamaño."""

    def __init__(self):
        self.levels: list[tuple[np.ndarray, np.ndarray]] = []

    def add(self, owner: int, hashes: np.ndarray) -> None:
        if len(hashes) == 0:
            return
        h = np.unique(hashes)
        self.levels.append((h, np.full(len(h), owner, dtype=np.int32)))
        while len(self.levels) >= 2 and len(self.levels[-2][0]) <= len(self.levels[-1][0]):
            (h2, o2), (h1, o1) = self.levels.pop(), self.levels.pop()
            hh = np.concatenate([h1, h2])
            oo = np.concatenate([o1, o2])
            order = np.argsort(hh, kind="stable")
            self.levels.append((hh[order], oo[order]))

    def lookup(self, q: np.ndarray) -> dict[int, list[int]]:
        """dueño -> posiciones de q que coinciden por hash (sin confirmar)."""
        found: dict[int, list[int]] = {}
        if len(q) == 0:
            return found
        for h, o in self.levels:
            lo = np.searchsorted(h, q, "left")
            hi = np.searchsorted(h, q, "right")
            for p in np.nonzero(hi > lo)[0]:
                for owner in o[lo[p]:hi[p]]:
                    found.setdefault(int(owner), []).append(int(p))
        return found


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
    truncated: bool = False


class CallDAG:
    def __init__(self, secret_files: dict[str, list[str]], k: int = 8,
                 variants: Callable[[str], list[str]] = default_variants,
                 secret_values: dict[str, str] | None = None):
        self.k = k
        self.variants = variants
        self.file_to_secrets: dict[str, set[str]] = {}
        for sid, files in secret_files.items():
            for f in files:
                self.file_to_secrets.setdefault(f, set()).add(sid)
        self.nodes: dict[str, _Node] = {}
        self.order: list[str] = []
        self._pos: dict[str, int] = {}
        self._index = _KGramIndex()
        self.secret_values: dict[str, str] | None = None
        self._secret_grams: dict[str, set[str]] = {}
        if secret_values is not None:
            self.secret_values = {}
            for sid, value in secret_values.items():
                self.set_secret_value(sid, value)

    # --- Secretos -----------------------------------------------------------

    def set_secret_value(self, secret_id: str, value: str) -> None:
        """Valor vigente de un secreto (por ejemplo, tras una rotación). El anterior deja de propagar S."""
        if self.secret_values is None:
            self.secret_values = {}
        self.secret_values[secret_id] = value
        k = self.k
        self._secret_grams[secret_id] = {v[i:i + k] for v in self.variants(value)
                                         for i in range(len(v) - k + 1)}

    def _secrets_in_output(self, text: str) -> set[str]:
        if not self.secret_values:
            return set()
        k = self.k
        return {sid for sid, value in self.secret_values.items()
                if any(value[i:i + k] in text for i in range(len(value) - k + 1))}

    # --- Salidas ------------------------------------------------------------

    def set_output(self, call_id: str, output: str) -> None:
        node = self.nodes[call_id]
        text = output or ""
        node.truncated = len(text) > MAX_INDEXED_CHARS
        text = text[:MAX_INDEXED_CHARS]
        node.variants = [v for v in self.variants(text) if len(v) >= self.k]
        if node.variants:
            self._index.add(self._pos[call_id],
                            np.concatenate([kgram_hashes(v, self.k) for v in node.variants]))
        # Leer un secreto también es recibirlo en la salida, aunque no se toque su archivo.
        for sid in self._secrets_in_output(text) - node.secrets_read:
            node.secrets_read.add(sid)
            node.S.add(sid)
            node.s_witness.setdefault(sid, call_id)
            if node.kind == "neutral":
                node.kind = "source"

    # --- Nodos --------------------------------------------------------------

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
        k = self.k
        parents: list[str] = []
        for owner in sorted(self._index.lookup(arg_hashes).items()):
            pid = self.order[owner[0]]
            variants = self.nodes[pid].variants
            if any(arg_text[p:p + k] in v for p in owner[1] for v in variants):
                parents.append(pid)

        # k-gramas de los argumentos que son material de cada secreto (solo con secret_values)
        secret_material: dict[str, list[str]] = {}
        if self.secret_values is not None:
            grams = {arg_text[i:i + k] for i in range(len(arg_text) - k + 1)}
            for sid, sg in self._secret_grams.items():
                hit = [g for g in grams if g in sg]
                if hit:
                    secret_material[sid] = hit

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
                if self.secret_values is not None:
                    mat = secret_material.get(s)
                    if not mat or not any(g in v for g in mat for v in p.variants):
                        continue  # la arista no lleva material de s
                S.add(s)
                if s not in s_w or self._t(p.s_witness[s]) < self._t(s_w[s], t):
                    s_w[s] = p.s_witness[s]

        node = _Node(call, kind, reads, U, S, u_w, s_w, parents)
        self.nodes[call.id] = node
        self._pos[call.id] = len(self.order)
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
