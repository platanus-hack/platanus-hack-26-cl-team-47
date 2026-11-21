"""Las seis herramientas del agente como funciones puras.

Cada función recibe el workspace o el mapa de hosts explícitamente y no
toca nada fuera de ellos. Los errores de política se levantan como
ToolError, que el proxy convierte en texto para el agente.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

HTTP_TIMEOUT_S = 10.0
GITHUB_HOST = "github.test"
UNTRUSTED_HOSTS = frozenset({"github.test", "web.test"})


class ToolError(Exception):
    pass


# --- Sistema de archivos -------------------------------------------------

def resolve_in_workspace(workspace: str | os.PathLike, path: str) -> Path:
    """Resuelve `path` relativo al workspace y falla si se sale de él."""
    root = Path(workspace).resolve()
    target = (root / path).resolve()
    if target != root and root not in target.parents:
        raise ToolError(f"ruta fuera del workspace: {path}")
    return target


def workspace_relative(workspace: str | os.PathLike, path: str) -> str:
    root = Path(workspace).resolve()
    rel = resolve_in_workspace(workspace, path).relative_to(root).as_posix()
    return rel or "."


def read_file(workspace: str | os.PathLike, path: str) -> str:
    target = resolve_in_workspace(workspace, path)
    if not target.is_file():
        raise ToolError(f"no existe el archivo: {path}")
    return target.read_text(encoding="utf-8", errors="replace")


def list_dir(workspace: str | os.PathLike, path: str = ".") -> str:
    target = resolve_in_workspace(workspace, path)
    if not target.is_dir():
        raise ToolError(f"no existe el directorio: {path}")
    entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name))
    return "\n".join(p.name + ("/" if p.is_dir() else "") for p in entries)


# --- Red -----------------------------------------------------------------

def url_host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def resolve_url(url: str, hosts: dict[str, str]) -> str:
    """Traduce http://<host>.test/ruta a la URL local del servicio simulado.

    Cualquier host fuera de `hosts` levanta ToolError y no se hace la petición.
    """
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("http", "https") or host not in hosts:
        raise ToolError(f"host no permitido: {host or url}")
    base = hosts[host].rstrip("/")
    rest = parts.path or "/"
    if parts.query:
        rest += "?" + parts.query
    return base + rest


def http_request(
    hosts: dict[str, str],
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: str = "",
) -> str:
    target = resolve_url(url, hosts)
    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(target, data=data, method=method.upper(), headers=dict(headers or {}))
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            status, text = resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        raise ToolError(f"no se pudo conectar con {url_host(url)}: {e.reason}") from e
    return f"{status}\n{text}"


def github_issue(hosts: dict[str, str], repo: str, title: str, body: str) -> str:
    payload = json.dumps({"title": title, "body": body})
    return http_request(
        hosts, "POST", f"http://{GITHUB_HOST}/repos/{repo}/issues",
        {"Content-Type": "application/json"}, payload,
    )


def github_comment(hosts: dict[str, str], repo: str, number: int, body: str) -> str:
    payload = json.dumps({"body": body})
    return http_request(
        hosts, "POST", f"http://{GITHUB_HOST}/repos/{repo}/issues/{int(number)}/comments",
        {"Content-Type": "application/json"}, payload,
    )


# --- git -----------------------------------------------------------------

GIT_TIMEOUT_S = 30.0
NETWORK_SUBCOMMANDS = frozenset({"push", "pull", "fetch", "clone", "ls-remote", "submodule", "remote"})


def git(workspace: str | os.PathLike, args: list[str]) -> str:
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise ToolError("args debe ser una lista de strings")
    # Nada de -C/-c/--git-dir/--work-tree: git solo corre dentro del workspace.
    for a in args:
        if a in ("-C", "-c") or a.startswith(("--git-dir", "--work-tree", "--exec-path", "--upload-pack", "--receive-pack", "--config")):
            raise ToolError(f"argumento de git no permitido: {a}")
    sub = next((a for a in args if not a.startswith("-")), "")
    if sub in NETWORK_SUBCOMMANDS:
        # Nada sale del banco de pruebas: la red de git se simula.
        return f"exit 0\n{sub} simulado (sin red): {' '.join(args)}"
    root = Path(workspace).resolve()
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        # No subir a buscar el repo del equipo si el workspace no es un repo propio.
        "GIT_CEILING_DIRECTORIES": str(root.parent),
    }
    try:
        res = subprocess.run(
            ["git", *args], cwd=root, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT_S, env=env,
        )
    except FileNotFoundError as e:
        raise ToolError("git no está instalado") from e
    except subprocess.TimeoutExpired as e:
        raise ToolError("git excedió el tiempo límite") from e
    out = res.stdout + (("\n" + res.stderr) if res.stderr else "")
    return f"exit {res.returncode}\n{out}".rstrip()
