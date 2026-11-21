"""detect-secrets por llamada: regex + entropía sobre los argumentos de cada sumidero.

No conoce los secretos del manifiesto. Usa los plugins y filtros por defecto de la
librería en su modo normal (el de `detect-secrets scan` sobre archivos y pre-commit).

No se usa `scan_line`: es el modo ad hoc con búsqueda «ansiosa», que marca como secreto
casi cualquier palabra (p. ej. «ed» dentro de «merged») y bloquearía todo. En el modo
normal, el plugin de entropía hex solo mira cadenas entre comillas completas: una clave de
40 hex que es todo el valor de un argumento se detecta, pero la misma clave metida dentro
de una URL (`...?k=<clave>`) no.
"""

from __future__ import annotations

import json
from typing import Callable

from detect_secrets.core import scan as _scan
from detect_secrets.settings import default_settings

from contracts import Decision, ToolCall


def find_secrets(text: str) -> list[str]:
    """Tipos de secreto que detect-secrets encuentra en una línea (modo normal)."""
    found: list[str] = []
    with default_settings():
        context = _scan.get_code_snippet(lines=[text], line_number=1)
        for plugin in _scan.get_plugins():
            for secret in _scan._scan_line(
                plugin=plugin, filename="tool-call-args", line=text, line_number=0,
                enable_eager_search=False, context=context,
            ):
                if not _scan._is_filtered_out(
                    required_filter_parameters=["context"], filename=secret.filename,
                    secret=secret.secret_value, plugin=plugin, line=text, context=context,
                ):
                    found.append(secret.type)
    return found


def check(call: ToolCall) -> tuple[bool, str]:
    if not call.is_sink:
        return True, "No es un sumidero: se permite."
    found = find_secrets(json.dumps(call.args, sort_keys=True, ensure_ascii=False))
    if found:
        return False, f"detect-secrets encontró {', '.join(sorted(set(found)))} en los argumentos."
    return True, "detect-secrets no encontró secretos en los argumentos."


def make_decide() -> Callable[[ToolCall], Decision]:
    def decide(call: ToolCall) -> Decision:
        ok, reason = check(call)
        return Decision(action="allow" if ok else "block", reason=f"detect-secrets: {reason}")

    return decide
