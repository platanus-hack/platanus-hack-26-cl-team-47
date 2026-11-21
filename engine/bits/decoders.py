"""Decodificadores y normalización del motor de bits (tarea #5, paso 4).

Cada decodificador recibe un texto y devuelve una lista de textos derivados
(puede ser vacía). El motor busca coincidencias en el texto original y en
todos sus derivados, con profundidad acotada, para cubrir encadenamientos
como base64(invertido(s)).
"""

from __future__ import annotations

import base64
import binascii
import codecs
import re
from typing import Callable, Iterable
from urllib.parse import unquote_plus

Decoder = Callable[[str], list[str]]

# Tokens con pinta de base64 (estándar o url-safe). Con 8 o más caracteres de cuerpo se aceptan
# siempre; los cortos, de 6 o 7 (#126), solo con relleno: ver decode_base64.
_B64_TOKEN = re.compile(r"[A-Za-z0-9+/_\-]{6,}={0,2}")
# Cuerpo mínimo de un token corto: 6 caracteres decodifican 4 bytes, MIN_CANDIDATE del motor (engine.py).
# Así un fragmento de 4 caracteres cuenta igual en base64 que en claro (#126).
_B64_SHORT_BODY = 6
_B64_LONG_BODY = 8
# Tokens hexadecimales de longitud par (bytes codificados).
_HEX_TOKEN = re.compile(r"(?:[0-9A-Fa-f]{2}){4,}")
# Caracteres sueltos separados por 1 a 3 separadores no alfanuméricos: "a-b-c-d", "a b c d".
_SEPARATED = re.compile(r"(?<![0-9A-Za-z])(?:[0-9A-Za-z][^0-9A-Za-z]{1,3}){3,}[0-9A-Za-z](?![0-9A-Za-z])")
_NON_ALNUM = re.compile(r"[^0-9A-Za-z]")


def _printable(raw: bytes) -> str | None:
    """Bytes a texto si son mayormente imprimibles; si no, None (ruido de decodificar algo que no era)."""
    if not raw:
        return None
    text = raw.decode("latin-1")
    good = sum(1 for ch in text if ch.isprintable() or ch in "\n\t\r")
    return text if good / len(text) >= 0.9 else None


def _short_b64_ok(body: str, pad: int) -> bool:
    """Token corto (6 o 7 caracteres de cuerpo): solo con relleno explícito y largo total múltiplo de 4.

    Es la forma que tiene un fragmento de 4 o 5 caracteres en base64 estándar ("YjJkZQ==",
    "YjJkZTE="). Exigir el relleno deja fuera las palabras de 6 o 7 letras sueltas (sin "="), que son
    la fuente obvia de coincidencias al azar; además decode_base64 exige texto imprimible."""
    return _B64_SHORT_BODY <= len(body) < _B64_LONG_BODY and pad > 0 and (len(body) + pad) % 4 == 0


def decode_base64(text: str) -> list[str]:
    out: list[str] = []
    for m in _B64_TOKEN.finditer(text):
        tok = m.group(0)
        pad = len(tok) - len(tok.rstrip("="))
        # El token puede venir pegado a texto alfanumérico ("key=QUJD..."): probamos los 4 desfases.
        for start in range(4):
            body = tok[start:].rstrip("=")
            if len(body) < _B64_LONG_BODY:
                if _short_b64_ok(body, pad):
                    padded = body + "=" * pad
                    for alt in (False, True):
                        try:
                            raw = (base64.urlsafe_b64decode if alt else base64.b64decode)(padded)
                        except (binascii.Error, ValueError):
                            continue
                        dec = _printable(raw)
                        if dec:
                            out.append(dec)
                break
            body = body[: len(body) - len(body) % 4] if len(body) % 4 == 1 else body
            padded = body + "=" * (-len(body) % 4)
            for alt in (False, True):
                try:
                    raw = (base64.urlsafe_b64decode if alt else base64.b64decode)(padded)
                except (binascii.Error, ValueError):
                    continue
                dec = _printable(raw)
                if dec:
                    out.append(dec)
    return out


def decode_hex(text: str) -> list[str]:
    out: list[str] = []
    for m in _HEX_TOKEN.finditer(text):
        tok = m.group(0)
        for start in (0, 1):
            body = tok[start:]
            body = body[: len(body) - len(body) % 2]
            if len(body) < 8:
                continue
            dec = _printable(bytes.fromhex(body))
            if dec:
                out.append(dec)
    return out


def decode_url(text: str) -> list[str]:
    if "%" not in text and "+" not in text:
        return []
    dec = unquote_plus(text)
    return [dec] if dec != text else []


def decode_reversed(text: str) -> list[str]:
    return [text[::-1]]


def decode_rot13(text: str) -> list[str]:
    dec = codecs.encode(text, "rot13")
    return [dec] if dec != text else []


def decode_separated(text: str) -> list[str]:
    return [_NON_ALNUM.sub("", m.group(0)) for m in _SEPARATED.finditer(text)]


DECODERS: dict[str, Decoder] = {
    "base64": decode_base64,
    "hex": decode_hex,
    "url": decode_url,
    "reversed": decode_reversed,
    "rot13": decode_rot13,
    "separated": decode_separated,
}


def expand_oriented(text: str, depth: int = 2, max_variants: int = 256) -> list[tuple[str, bool]]:
    """Como expand, pero cada variante dice si quedó invertida respecto del texto original
    (número impar de decodificadores «reversed» en su cadena)."""
    seen: dict[str, bool] = {text: False}
    frontier = [(text, False)]
    for _ in range(depth):
        nxt: list[tuple[str, bool]] = []
        for t, flipped in frontier:
            for name, dec in DECODERS.items():
                f = flipped != (name == "reversed")
                for d in dec(t):
                    if d and d not in seen and len(seen) < max_variants:
                        seen[d] = f
                        nxt.append((d, f))
        frontier = nxt
        if not frontier:
            break
    return list(seen.items())


def expand(text: str, depth: int = 2, max_variants: int = 256) -> list[str]:
    """Texto original más todos sus derivados hasta `depth` decodificadores encadenados."""
    return [t for t, _ in expand_oriented(text, depth, max_variants)]


# --- Alfabeto y normalización ---------------------------------------------

_ALPHABETS: list[tuple[str, frozenset[str], bool]] = [
    # (nombre, conjunto, insensible a mayúsculas)
    ("hex", frozenset("0123456789abcdef"), True),
    ("alnum", frozenset("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"), False),
    ("base64", frozenset("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/=-_"), False),
]
_PRINTABLE_SIZE = 95


def alphabet_of(secret: str) -> tuple[str, int, bool]:
    """(nombre, |A_s|, insensible_a_mayúsculas) del alfabeto más chico que contiene al secreto."""
    low = secret.lower()
    for name, chars, ci in _ALPHABETS:
        probe = low if ci else secret
        if set(probe) <= chars:
            return name, len(chars), ci
    return "printable", _PRINTABLE_SIZE, False


def normalize(text: str, case_insensitive: bool) -> str:
    return text.lower() if case_insensitive else text


def iter_strings(obj: object) -> Iterable[str]:
    """Todas las cadenas (claves y valores) dentro de los args de una llamada."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from iter_strings(v)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            yield from iter_strings(v)
    elif obj is not None:
        yield str(obj)
