"""Detector del nivel 0 (tarea #29, paso 9a): decide(ToolCall) -> Decision.

Orden en cada llamada (documento v4.0, sección 7.1):
  1. touch = graph.touch(resources)      2. dag_info = dag.add(call)
  3. bits = bits_engine.observe(call)    4. f = extract(...); l = model.llr(f); S = cusum.update(l)
  5. regla de decisión (sección 4.4)      6. dag.set_output si la llamada trae output grabado

Regla, en orden:
  1. Bloqueo determinista: sumidero, subieron los bits confirmados de s y el destino no está
     en allowed_hosts de s -> rotate+block (se rota s).
  2. Rotar: (bits + candidate_bits)/H >= lambda_rot, o s expuesto y S >= b_rot, o s expuesto
     y e(s) >= T -> rotate+allow.
  3. Bloqueo por evidencia: dag.exposed() no vacío, S > b y path no vacío -> block
     (nivel 0: R_plus = 1 si hay path).
  4. allow.
Si 2 y 3 se cumplen a la vez, la acción es rotate+block.

Enviar un secreto a un host de sus allowed_hosts no es fuga: lo que el motor de bits contó
para ese secreto en esa llamada se descarta.

Decision.leak[s] = {bits: confirmadas + candidatas, fraction: bits / H(s)}, con los valores de
antes de rotar. El bloqueo determinista (regla 1) mira solo las confirmadas.
Con enforce=False (make_measure_only) se mide todo igual pero la acción es siempre allow y no se rota.
"""

from __future__ import annotations

import json
import random
import string
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from contracts import Decision, Leak, ToolCall
from engine.bits import BitsEngine, alphabet_of
from engine.evidence import Cusum, FeatureModel
from engine.graph.dag import CallDAG
from engine.graph.gff import FileGraph

from .features import extract
from .params import Params

_ALPHABET_CHARS = {
    "hex": "0123456789abcdef",
    "alnum": string.digits + string.ascii_letters,
    "base64": string.digits + string.ascii_letters + "+/",
    "printable": string.digits + string.ascii_letters + string.punctuation,
}


def _dest_host(call: ToolCall, files: set[str]) -> str | None:
    url = call.args.get("url") if isinstance(call.args, dict) else None
    if isinstance(url, str) and url:
        host = urlparse(url if "//" in url else "//" + url).hostname
        if host:
            return host.lower()
    for r in call.resources:
        if r and r not in files and "/" not in r and "." in r:
            return r.lower()
    return None


class Detector:
    def __init__(self, workspace: str = "demo/repo", manifest_path: str = "demo/secrets_manifest.json",
                 model: FeatureModel | None = None, params: Params = Params(),
                 rotate: Callable[[str], str] | None = None, seed: int = 0, enforce: bool = True):
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        self.enforce = enforce
        self.params = params
        self.model = model
        self._rotate_fn = rotate
        self._rng = random.Random(seed)
        self.secret_files = {s["secret_id"]: list(s.get("files", [])) for s in manifest["secrets"]}
        self.allowed = {s["secret_id"]: {h.lower() for h in s.get("allowed_hosts", [])} for s in manifest["secrets"]}
        self._file_to_secrets: dict[str, set[str]] = {}
        for sid, fs in self.secret_files.items():
            for f in fs:
                self._file_to_secrets.setdefault(f, set()).add(sid)
        self.graph = FileGraph.from_workspace(workspace, manifest_path)
        self.dag = CallDAG(self.secret_files)
        self.bits = BitsEngine.from_manifest(manifest_path)
        self.cusum = Cusum()
        self.exposed: dict[str, bool] = {sid: False for sid in self.secret_files}
        self.e: dict[str, int] = {sid: 0 for sid in self.secret_files}
        self._prev_kind: str | None = None
        # Para el camino explicativo (#51): primera lectura y sumideros que aportaron, desde la última rotación.
        self.first_read: dict[str, str | None] = {sid: None for sid in self.secret_files}
        self.contrib: dict[str, list[str]] = {sid: [] for sid in self.secret_files}
        self._t_of: dict[str, int] = {}

    # --- API ---------------------------------------------------------------

    def set_output(self, call_id: str, output: str) -> None:
        self.dag.set_output(call_id, output)

    def decide(self, call: ToolCall) -> Decision:
        t0 = time.perf_counter()
        p = self.params

        touch = self.graph.touch(call.resources)
        dag_info = self.dag.add(call)

        before = {sid: self._snapshot(sid) for sid in self.secret_files}
        bits = self.bits.observe(call)
        dest = _dest_host(call, set(self._file_to_secrets)) if call.is_sink else None
        if dest is not None:
            for sid in self.secret_files:
                if dest in self.allowed[sid]:   # uso legítimo: no es fuga
                    self._restore(sid, before[sid])
            bits = self.bits.state()

        f = extract(call, touch, dag_info, bits, self._prev_kind)
        l = self.model.llr(f) if self.model is not None else 0.0
        S = self.cusum.update(l)

        for sid in self.secret_files:
            self.e[sid] += 1
        for r in call.resources:
            for sid in self._file_to_secrets.get(r, ()):
                self.exposed[sid] = True
                if self.first_read[sid] is None:
                    self.first_read[sid] = call.id
        self._t_of[call.id] = call.t
        if call.is_sink:
            for sid, v in bits.items():
                st = self.bits._s[sid]
                prev_total = (len(before[sid][0]) + len(before[sid][1] - before[sid][0])) * st.bits_per_char
                if v["bits"] + v["candidate_bits"] > prev_total:
                    self.contrib[sid].append(call.id)

        # leak = confirmadas + candidatas (lo mismo que compara la regla de rotación), antes de rotar.
        leak = {}
        for sid, v in bits.items():
            total = v["bits"] + v["candidate_bits"]
            H = self.bits.H(sid)
            leak[sid] = Leak(bits=total, fraction=min(1.0, total / H) if H else 0.0)
        dag_path = list(dag_info.get("path") or [])
        R_plus = 1.0 if dag_path else 0.0
        path_ids: set[str] = set()   # camino explicativo (#51), se ordena por t al final
        read_and_now = lambda sid: [i for i in (self.first_read[sid], call.id) if i]  # noqa: E731

        to_rotate: list[str] = []
        reasons: list[str] = []
        blocked = False

        # 1. Bloqueo determinista
        if call.is_sink:
            for sid, v in bits.items():
                if v["bits"] > before[sid][3] and (dest is None or dest not in self.allowed[sid]):
                    blocked = True
                    to_rotate.append(sid)
                    reasons.append(f"Sumidero con material de {sid} hacia {dest or 'destino desconocido'}")
                    path_ids.update(dag_path or read_and_now(sid))
        if blocked:
            action = "rotate+block"
        else:
            # 2. Rotar
            for sid, v in bits.items():
                H = self.bits.H(sid)
                frac = (v["bits"] + v["candidate_bits"]) / H if H else 0.0
                if frac >= p.lambda_rot:
                    reasons.append(f"Rotación de {sid}: fracción filtrada {frac:.2f} ≥ {p.lambda_rot}")
                    path_ids.update([i for i in [self.first_read[sid], *self.contrib[sid]] if i])
                elif self.exposed[sid] and S >= p.b_rot:
                    reasons.append(f"Rotación de {sid}: expuesto y evidencia S={S:.2f} ≥ {p.b_rot}")
                    path_ids.update(read_and_now(sid))
                elif self.exposed[sid] and self.e[sid] >= p.T:
                    reasons.append(f"Rotación periódica de {sid}: {self.e[sid]} llamadas desde la última")
                    path_ids.update(read_and_now(sid))
                else:
                    continue
                to_rotate.append(sid)
            # 3. Bloqueo por evidencia
            evidence_block = bool(self.dag.exposed()) and S > p.b and bool(dag_path)
            if evidence_block:
                reasons.append(f"Bloqueo por evidencia: S={S:.2f} > {p.b} con camino no confiable → secreto → sumidero")
                path_ids.update(dag_path)
            if to_rotate and evidence_block:
                action = "rotate+block"
            elif to_rotate:
                action = "rotate+allow"
            elif evidence_block:
                action = "block"
            else:
                action = "allow"

        path = sorted(path_ids, key=lambda i: (self._t_of.get(i, call.t), i))
        reason = "; ".join(reasons) if reasons else "Sin evidencia ni fuga"
        if self.enforce:
            for sid in to_rotate:
                self._do_rotate(sid)
        else:
            reason = f"Solo medición: {action} — {reason}"
            action = "allow"

        if call.output is not None:
            self.dag.set_output(call.id, call.output)
        self._prev_kind = dag_info.get("kind")

        return Decision(
            action=action, S=S, R_plus=R_plus, leak=leak, path=path,
            reason=reason,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    # --- interno -----------------------------------------------------------

    def _snapshot(self, sid: str) -> tuple[set[int], set[int], int, float]:
        st = self.bits._s[sid]
        return set(st.K), set(st.cand), st.last_new, len(st.K) * st.bits_per_char

    def _restore(self, sid: str, snap: tuple[set[int], set[int], int, float]) -> None:
        st = self.bits._s[sid]
        st.K, st.cand, st.last_new = set(snap[0]), set(snap[1]), snap[2]

    def _do_rotate(self, sid: str) -> None:
        if self._rotate_fn is not None:
            new = self._rotate_fn(sid)
        else:
            old = self.bits._s[sid].value
            chars = _ALPHABET_CHARS[alphabet_of(old)[0]]
            new = "".join(self._rng.choice(chars) for _ in range(len(old)))
        self.bits.rotate(sid, new)
        self.first_read[sid] = None
        self.contrib[sid] = []
        self.e[sid] = 0
        self.exposed[sid] = False


def make_decide() -> Callable[[ToolCall], Decision]:
    """Fábrica para el arnés: python -m eval.replay --decide engine.detector:make_decide"""
    return Detector().decide


def make_measure_only() -> Callable[[ToolCall], Decision]:
    """Mide igual que el detector pero nunca bloquea ni rota (panel «sin protección»)."""
    return Detector(enforce=False).decide
