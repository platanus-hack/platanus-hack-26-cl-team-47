"""Carga de los secretos sintéticos iniciales desde el manifiesto de Demo.

La ruta viene de la variable SECRETS_MANIFEST (por defecto demo/secrets_manifest.json).
Los valores nunca se copian al código: se leen del manifiesto o de los archivos a los
que apunta (.env, YAML plano). Si no hay manifiesto, se generan SECRET_1..SECRET_3 al azar.

Formatos aceptados mientras se fija el de demo/README.md:
  {"secrets": [{"id": "SECRET_1", "value": "..."}, ...]}
  {"secrets": [{"id": "SECRET_1", "file": "demo/repo/.env", "key": "API_EMPRESA_KEY"}]}
  [{"id": ..., ...}, ...]
  {"SECRET_1": "valor", ...}   o   {"SECRET_1": {"value": ...}, ...}
"""

from __future__ import annotations

import json
import os
import re
import secrets as _rand
import string
from pathlib import Path

DEFAULT_MANIFEST = "demo/secrets_manifest.json"
DEFAULT_LENGTH = 40

HEX_LOWER = "0123456789abcdef"
HEX_UPPER = "0123456789ABCDEF"
ALNUM = string.ascii_letters + string.digits
URLSAFE = ALNUM + "-_"

_ID_KEYS = ("id", "secret_id", "name")
_VALUE_KEYS = ("value", "secret", "initial_value")
_FILE_KEYS = ("file", "path", "location", "source")
_KEY_KEYS = ("key", "env", "env_var", "var", "field")


def infer_alphabet(value: str) -> str:
    """El alfabeto más chico de los conocidos que contiene todo el valor."""
    chars = set(value)
    for alphabet in (HEX_LOWER, HEX_UPPER, ALNUM, URLSAFE):
        if chars <= set(alphabet):
            return alphabet
    return "".join(sorted(chars | set(ALNUM)))


def random_value(length: int = DEFAULT_LENGTH, alphabet: str = HEX_LOWER) -> str:
    return "".join(_rand.choice(alphabet) for _ in range(length))


def _first(entry: dict, keys: tuple[str, ...]):
    for k in keys:
        if k in entry and entry[k] not in (None, ""):
            return entry[k]
    return None


def _read_key_from_file(path: Path, key: str) -> str | None:
    """Lee KEY=valor (.env) o key: valor (YAML plano, también anidado por indentación)."""
    if not path.exists():
        return None
    pattern = re.compile(
        r"^\s*(?:export\s+)?" + re.escape(key) + r"\s*[:=]\s*(?P<v>.+?)\s*$"
    )
    for line in path.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line)
        if m:
            v = m.group("v").split(" #", 1)[0].strip()
            return v.strip("'\"")
    return None


def _resolve_entry(entry: dict, base: Path) -> tuple[str, str] | None:
    sid = _first(entry, _ID_KEYS)
    if not sid:
        return None
    value = _first(entry, _VALUE_KEYS)
    if value is None:
        file_ = _first(entry, _FILE_KEYS)
        key = _first(entry, _KEY_KEYS) or sid
        if file_:
            for candidate in (Path(file_), base / file_, base / "repo" / file_):
                value = _read_key_from_file(candidate, key)
                if value is not None:
                    break
    if value is None:
        return None
    return str(sid), str(value)


def load_manifest(path: str | os.PathLike | None = None) -> dict[str, str]:
    """Devuelve {secret_id: valor}. Sin manifiesto, SECRET_1..3 al azar."""
    path = Path(path or os.environ.get("SECRETS_MANIFEST", DEFAULT_MANIFEST))
    if not path.exists():
        return {f"SECRET_{i}": random_value() for i in range(1, 4)}

    data = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    if isinstance(data, dict) and isinstance(data.get("secrets"), (list, dict)):
        data = data["secrets"]

    entries: list[dict] = []
    if isinstance(data, list):
        entries = [e for e in data if isinstance(e, dict)]
    elif isinstance(data, dict):
        for sid, v in data.items():
            if isinstance(v, dict):
                entries.append({"id": sid, **v})
            elif isinstance(v, str):
                entries.append({"id": sid, "value": v})

    out: dict[str, str] = {}
    for e in entries:
        resolved = _resolve_entry(e, base)
        if resolved:
            out[resolved[0]] = resolved[1]
    return out
