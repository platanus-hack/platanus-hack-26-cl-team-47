"""Allowlist de egress: el agente solo puede salir a dominios aprobados."""

from __future__ import annotations

from typing import Callable
from urllib.parse import urlsplit

from contracts import Decision, ToolCall

ALLOWED_HOSTS = frozenset(
    {"github.test", "api.empresa.test", "web.test", "vault.test", "deploy.empresa.test"}
)
_GITHUB_TOOLS = ("github_issue", "github_comment")


def _host(value: str) -> str:
    value = (value or "").strip()
    if "://" in value:
        value = urlsplit(value).hostname or ""
    return value.split("/", 1)[0].split(":", 1)[0].lower()


def destination(call: ToolCall) -> str | None:
    """Host de destino del sumidero, o None si es un git push (se considera permitido)."""
    if call.tool in _GITHUB_TOOLS:
        return "github.test"
    if call.tool == "git":
        return None
    url = call.args.get("url") if isinstance(call.args, dict) else None
    if url:
        return _host(str(url))
    return _host(call.resources[0]) if call.resources else ""


def check(call: ToolCall) -> tuple[bool, str]:
    """(permitido, motivo)."""
    if not call.is_sink:
        return True, "No es un sumidero: se permite."
    host = destination(call)
    if host is None:
        return True, "git push: se considera permitido por la allowlist."
    if host in ALLOWED_HOSTS:
        return True, f"Destino {host} está en la allowlist."
    return False, f"Destino {host or '(desconocido)'} fuera de la allowlist."


def make_decide() -> Callable[[ToolCall], Decision]:
    def decide(call: ToolCall) -> Decision:
        ok, reason = check(call)
        return Decision(action="allow" if ok else "block", reason=f"Allowlist: {reason}")

    return decide
