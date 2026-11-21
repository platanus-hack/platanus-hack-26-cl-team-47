"""Motor de bits (tarea #5, paso 4): I_t y λ_t por secreto.

Reglas (documento v4.0, secciones 4.1 y 6.2):
- Solo cuentan los argumentos de llamadas con is_sink = true.
- H(s) = n·log2|A_s|;  I_t(s) = |K_t(s)|·log2|A_s|;  λ_t = I_t / H.
- Confirmada: coincidencia de k o más caracteres tras normalizar y decodificar. No caduca.
- Candidata: coincidencia de 4 a k-1 caracteres. Cuenta para rotar, nunca para bloquear.
  Caduca tras W llamadas si no aparece otra candidata en una posición distinta del mismo secreto.
- No son candidatas las cadenas con formato de hash (SHA de 40/64 hex, UUID) que van a un destino
  permitido del secreto.

Salida de observe() por secreto:
  bits, fraction                     -> confirmadas (lo que va en Decision.leak)
  candidate_bits, candidate_fraction -> solo candidatas vigentes, disjuntas de las confirmadas
                                        (total para rotar = bits + candidate_bits)
  positions                          -> posiciones confirmadas K_t, ordenadas
  candidate_positions                -> posiciones candidatas vigentes, ordenadas
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from .decoders import alphabet_of, expand_oriented, iter_strings, normalize

MIN_CANDIDATE = 4

_HASH_TOKEN = re.compile(
    r"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{64}|[0-9A-Fa-f]{40})(?![0-9A-Fa-f])"
    r"|[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}"
)
_HOST = re.compile(r"\b((?:[a-z0-9-]+\.)+test)\b", re.IGNORECASE)


def _get(call: Any, key: str, default: Any = None) -> Any:
    if isinstance(call, Mapping):
        return call.get(key, default)
    return getattr(call, key, default)


def maximal_matches(secret: str, text: str, min_len: int = MIN_CANDIDATE) -> list[tuple[int, int]]:
    """Coincidencias maximales (inicio en el secreto, largo) de al menos min_len caracteres."""
    n = len(secret)
    if n < min_len or len(text) < min_len:
        return []
    index: dict[str, list[int]] = defaultdict(list)
    for i in range(n - min_len + 1):
        index[secret[i : i + min_len]].append(i)
    out: list[tuple[int, int]] = []
    for j in range(len(text) - min_len + 1):
        starts = index.get(text[j : j + min_len])
        if not starts:
            continue
        for i in starts:
            if i > 0 and j > 0 and secret[i - 1] == text[j - 1]:
                continue  # no es maximal: se extiende a la izquierda
            L = min_len
            while i + L < n and j + L < len(text) and secret[i + L] == text[j + L]:
                L += 1
            out.append((i, L))
    return out


class _SecretState:
    __slots__ = ("value", "norm", "ci", "alphabet", "bits_per_char", "K", "cand", "last_new", "allowed")

    def __init__(self, value: str, allowed: Iterable[str]):
        self.allowed = frozenset(h.lower() for h in allowed)
        self.reset(value)

    def reset(self, value: str) -> None:
        self.value = value
        self.alphabet, size, self.ci = alphabet_of(value)
        self.norm = normalize(value, self.ci)
        self.bits_per_char = math.log2(size)
        self.K: set[int] = set()
        self.cand: set[int] = set()
        self.last_new = 0

    @property
    def H(self) -> float:
        return len(self.value) * self.bits_per_char

    def report(self) -> dict:
        n = len(self.value) or 1
        cand = self.cand - self.K
        return {
            "bits": len(self.K) * self.bits_per_char,
            "fraction": len(self.K) / n,
            "candidate_bits": len(cand) * self.bits_per_char,
            "candidate_fraction": len(cand) / n,
            "positions": sorted(self.K),
            "candidate_positions": sorted(cand),
        }


class BitsEngine:
    """Lleva, por secreto, lo filtrado hacia sumideros a lo largo de una sesión."""

    def __init__(
        self,
        secrets: dict[str, str],
        k: int = 8,
        W: int = 50,
        allowed_hosts: Mapping[str, Iterable[str]] | None = None,
        depth: int = 2,
    ):
        if k < MIN_CANDIDATE + 1:
            raise ValueError(f"k debe ser mayor que {MIN_CANDIDATE}")
        self.k = k
        self.W = W
        self.depth = depth
        allowed_hosts = allowed_hosts or {}
        self._s = {sid: _SecretState(v, allowed_hosts.get(sid, ())) for sid, v in secrets.items()}
        self._step = 0

    @classmethod
    def from_manifest(cls, path: str | Path = "demo/secrets_manifest.json", **kw: Any) -> "BitsEngine":
        """Construye el motor desde el manifiesto de 1b (secret_id, value, allowed_hosts)."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        secrets = {s["secret_id"]: s["value"] for s in data["secrets"]}
        allowed = {s["secret_id"]: s.get("allowed_hosts", []) for s in data["secrets"]}
        return cls(secrets, allowed_hosts=allowed, **kw)

    def H(self, secret_id: str) -> float:
        return self._s[secret_id].H

    def state(self) -> dict[str, dict]:
        return {sid: st.report() for sid, st in self._s.items()}

    def rotate(self, secret_id: str, new_value: str) -> None:
        """Reinicia lo filtrado de ese secreto: el valor nuevo no ha salido."""
        self._s[secret_id].reset(new_value)

    def observe(self, call: Any) -> dict[str, dict]:
        self._step += 1
        found_conf: dict[str, set[int]] = {sid: set() for sid in self._s}
        found_cand: dict[str, set[int]] = {sid: set() for sid in self._s}

        if _get(call, "is_sink", False):
            strings = list(iter_strings(_get(call, "args", {}) or {}))
            if strings:
                text = "\n".join(strings)
                hosts = {h.lower() for h in _HOST.findall(text)}
                variants = expand_oriented(text, self.depth)
                blanked = _HASH_TOKEN.sub(" ", text)
                blanked_variants = expand_oriented(blanked, self.depth) if blanked != text else None
                for sid, st in self._s.items():
                    to_allowed = bool(hosts) and hosts <= st.allowed
                    full = self._matches(st, variants)
                    for i, L in full:
                        if L >= self.k:
                            found_conf[sid].update(range(i, i + L))
                    cand_src = self._matches(st, blanked_variants) if (to_allowed and blanked_variants) else full
                    for i, L in cand_src:
                        if L < self.k:
                            found_cand[sid].update(range(i, i + L))

        for sid, st in self._s.items():
            st.K |= found_conf[sid]
            new = found_cand[sid] - st.K - st.cand
            if new:
                st.cand |= new
                st.last_new = self._step
            elif st.cand and self._step - st.last_new >= self.W:
                st.cand.clear()
            st.cand -= st.K
        return self.state()

    @staticmethod
    def _matches(st: _SecretState, variants: list[tuple[str, bool]]) -> set[tuple[int, int]]:
        """Coincidencias maximales (inicio, largo) en todas las variantes, sin las espejadas (#76).

        Si el secreto tiene un palíndromo junto al borde de lo enviado, la variante invertida de lo
        enviado contiene caracteres del secreto desplazados, fuera de lo enviado. Una coincidencia de
        una orientación se descarta si su inversa aparece en el secreto en otra posición y esas
        posiciones ya las explica la orientación contraria: es la misma información leída al revés.

        Dos pasos para no descartar ambas cuando se espejan entre sí (frecuente con 4-gramas): primero
        se filtran las invertidas contra las directas; después las directas solo contra las invertidas
        que quedaron. Si la ambigüedad es real, gana la lectura directa (mismo número de bits).
        """
        groups: dict[bool, set[tuple[int, int]]] = {False: set(), True: set()}
        for v, flipped in variants:
            groups[flipped].update(maximal_matches(st.norm, normalize(v, st.ci)))
        s = st.norm

        def cover(ms: set[tuple[int, int]]) -> set[int]:
            return {p for i, L in ms for p in range(i, i + L)}

        def unmirrored(ms: set[tuple[int, int]], other: set[int]) -> set[tuple[int, int]]:
            out = set()
            for i, L in ms:
                rev = s[i:i + L][::-1]
                j = s.find(rev)
                while j != -1 and not (j != i and all(p in other for p in range(j, j + L))):
                    j = s.find(rev, j + 1)
                if j == -1:
                    out.add((i, L))
            return out

        kept_rev = unmirrored(groups[True], cover(groups[False]))
        kept_fwd = unmirrored(groups[False], cover(kept_rev))
        return kept_fwd | kept_rev
