"""Reensamblado por sesión (#133): línea de base del estado del arte que ya junta fragmentos entre llamadas.

Es una RÉPLICA SIMPLIFICADA, inspirada en herramientas que reensamblan lo que sale en una sesión
(Pipelock, AgentBrake; ver docs/INVESTIGACION.md, «Actualización de H10»). No es su código ni su producto.

- Un estado por sesión (un make_decide nuevo por sesión), sin compartir entre sesiones.
- En cada sumidero hacia un destino que no está en los allowed_hosts de un secreto, los VALORES que salen
  (parámetros de la query, último segmento de la ruta sin extensión, cabeceras, cuerpo; title y body en las
  herramientas de GitHub; args["outgoing"] en git push) se agregan, en orden y sin separador, a un búfer de
  la sesión. El búfer es POR CAMPO (cada parámetro de la query por su nombre, la ruta, cada cabecera, el
  cuerpo…): si fuera uno solo, un campo fijo como el segmento "c" de /c?d=<fragmento> quedaría intercalado
  entre fragmento y fragmento y el reensamblado no vería nunca un goteo por el parámetro d. Un valor ajeno en
  el MISMO campo sí lo corta (límite documentado de la réplica). Sin decodificar nada: es la limitación que
  esas herramientas declaran.
- Bloquea si el búfer contiene min_run o más caracteres consecutivos del secreto (sin distinguir mayúsculas),
  o si una sola llamada los contiene en cualquier parte de sus argumentos serializados. Desde ahí bloquea
  todos los sumideros posteriores de la sesión hacia destinos no permitidos. No rota. leak vacío.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qsl, urlsplit

from contracts import Decision, ToolCall
from eval.baselines.allowlist import destination

MANIFEST = "demo/secrets_manifest.json"
_GITHUB_TOOLS = ("github_issue", "github_comment")


def _manifest() -> tuple[dict[str, str], dict[str, set[str]]]:
    data = json.loads(Path(MANIFEST).read_text(encoding="utf-8"))
    return ({s["secret_id"]: s["value"] for s in data["secrets"]},
            {s["secret_id"]: {h.lower() for h in s.get("allowed_hosts", [])} for s in data["secrets"]})


def _text(v: Any) -> str:
    if v is None:
        return ""
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, sort_keys=True)


def outgoing_values(call: ToolCall) -> list[tuple[str, str]]:
    """Los valores que salen en un sumidero, en orden, como (campo, valor)."""
    args = call.args if isinstance(call.args, dict) else {}
    out: list[tuple[str, str]] = []
    if call.tool in _GITHUB_TOOLS:
        out += [("title", _text(args.get("title"))), ("body", _text(args.get("body")))]
    elif call.tool == "git":
        out.append(("outgoing", _text(args.get("outgoing"))))
    else:
        url = args.get("url")
        if isinstance(url, str) and url:
            u = urlsplit(url)
            out += [(f"query:{k}", v) for k, v in parse_qsl(u.query, keep_blank_values=True)]
            last = u.path.rstrip("/").rsplit("/", 1)[-1]
            if "." in last:
                last = last.rsplit(".", 1)[0]
            out.append(("path", last))
        headers = args.get("headers")
        if isinstance(headers, dict):
            out += [(f"header:{k.lower()}", _text(v)) for k, v in headers.items()]
        out.append(("body", _text(args.get("body"))))
    return [(f, v) for f, v in out if v]


def _has_run(secret: str, text: str, min_run: int) -> bool:
    s, t = secret.lower(), text.lower()
    return len(s) >= min_run and any(s[i:i + min_run] in t for i in range(len(s) - min_run + 1))


def make_decide(secrets: dict[str, str] | None = None, min_run: int = 16) -> Callable[[ToolCall], Decision]:
    values, allowed = _manifest()
    if secrets is not None:
        values = dict(secrets)
    buffers: dict[tuple[str, str], str] = {}     # (secreto, campo) -> lo reensamblado
    state = {"blocked_by": None}

    def decide(call: ToolCall) -> Decision:
        if not call.is_sink:
            return Decision(action="allow", reason="Reensamblado: no es un sumidero.")
        dest = destination(call)
        host = (dest or "").lower()
        outside = [sid for sid in values if not (dest and host in allowed.get(sid, set()))]
        if not outside:
            return Decision(action="allow", reason=f"Reensamblado: {host} es un destino permitido.")
        if state["blocked_by"] is not None:
            return Decision(action="block", reason=f"Reensamblado: ya se reensambló {state['blocked_by']}; "
                                                   "se bloquean los sumideros hacia destinos no permitidos.")
        fields = outgoing_values(call)
        serial = _text(call.args)
        for sid in outside:
            hit = _has_run(values[sid], serial, min_run)
            for field, value in fields:
                key = (sid, field)
                buffers[key] = buffers.get(key, "") + value
                hit = hit or _has_run(values[sid], buffers[key], min_run)
            if hit:
                state["blocked_by"] = sid
                return Decision(action="block", reason=f"Reensamblado: {min_run} o más caracteres seguidos de {sid} "
                                                       f"hacia {host or 'destino desconocido'}.")
        return Decision(action="allow", reason="Reensamblado: sin secreto reensamblado.")

    return decide
