"""Verdad de terreno: cuántos bits de un secreto obtuvo el atacante.

Independiente de engine/ a propósito: es la medida contra la que se evalúa el detector.

Definición (documento v4.0, sección 4.1): K es el conjunto de posiciones del secreto que
aparecieron en lo recibido, en claro o tras decodificar, en fragmentos de 4 o más
caracteres. bits = |K| · log2(|alfabeto|), fraction = bits / H, H = n · log2(|alfabeto|).

Decodificadores: en claro, URL, base64 (estándar y URL-safe), hex, invertido, ROT13 y XOR
con las claves que el atacante conoce, y sus combinaciones de dos pasos.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import math
import re
from typing import Iterable
from urllib.parse import unquote, unquote_plus

from services.vault.manifest import infer_alphabet

MIN_FRAGMENT = 4

_B64_TOKEN = re.compile(r"[A-Za-z0-9+/_\-]{6,}={0,2}")
_HEX_TOKEN = re.compile(r"[0-9a-fA-F]{8,}")


def _text(b: bytes) -> str:
    return b.decode("latin-1")


def _b64_blobs(s: str) -> list[bytes]:
    out = []
    for tok in _B64_TOKEN.findall(s):
        tok = tok.rstrip("=")
        for start in range(4):  # el token puede venir pegado a otros caracteres
            t = tok[start:]
            if len(t) % 4 == 1:  # un carácter suelto no decodifica; los demás se rellenan
                t = t[:-1]
            if len(t) < 4:
                continue
            for alt in (b"+/", b"-_"):
                try:
                    out.append(base64.b64decode(t + "=" * (-len(t) % 4), altchars=alt, validate=False))
                except (binascii.Error, ValueError):
                    pass
    return out


def _hex_blobs(s: str) -> list[bytes]:
    out = []
    for tok in _HEX_TOKEN.findall(s):
        for start in (0, 1):
            t = tok[start:]
            t = t[: len(t) - len(t) % 2]
            try:
                out.append(bytes.fromhex(t))
            except ValueError:
                pass
    return out


def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def decoded_views(s: str, xor_keys: Iterable[str] = ()) -> set[str]:
    """Todas las lecturas del texto que el atacante sabe hacer."""
    keys = [k.encode("latin-1", "ignore") for k in xor_keys if k]
    layer1 = {s, unquote(s), unquote_plus(s)}
    views: set[str] = set()
    for u in layer1:
        blobs = [u.encode("latin-1", "ignore")] + _b64_blobs(u) + _hex_blobs(u)
        cands = {u, codecs.encode(u, "rot13")}
        for b in blobs:
            cands.add(_text(b))
            for k in keys:
                cands.add(_text(_xor(b, k)))
        for c in cands:
            views.add(c)
            views.add(c[::-1])
            views.add(codecs.encode(c, "rot13"))
    return views


def _positions_in(view: str, secret: str, found: set[int]) -> None:
    n = len(secret)
    i = 0
    while i <= n - MIN_FRAGMENT:
        if secret[i : i + MIN_FRAGMENT] not in view:
            i += 1
            continue
        j = i + MIN_FRAGMENT
        while j < n and secret[i : j + 1] in view:
            j += 1
        found.update(range(i, j))
        i += 1


def count_bits(received: list[str], secret: str, xor_keys: Iterable[str] = ()) -> dict:
    """{"bits", "fraction", "positions"} del secreto vigente en todo lo recibido."""
    if not secret:
        return {"bits": 0.0, "fraction": 0.0, "positions": []}
    keys = list(xor_keys)
    found: set[int] = set()
    lower = secret == secret.lower()
    for s in received:
        for v in decoded_views(s, keys):
            _positions_in(v, secret, found)
            if lower:
                _positions_in(v.lower(), secret, found)
        if len(found) == len(secret):
            break
    per_char = math.log2(len(set(infer_alphabet(secret))))
    bits = len(found) * per_char
    H = len(secret) * per_char
    return {"bits": float(bits), "fraction": float(bits / H) if H else 0.0, "positions": sorted(found)}
