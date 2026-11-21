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


def _git_env(root: Path) -> dict[str, str]:
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        # No subir a buscar el repo del equipo si el workspace no es un repo propio.
        "GIT_CEILING_DIRECTORIES": str(root.parent),
        # Sin configuración global ni de sistema (alias, pagers, hooks ajenos): solo la del repo (#137).
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    # Sin la configuración global no hay identidad: una por defecto, solo si no viene una.
    for k, v in (("GIT_AUTHOR_NAME", "Agente"), ("GIT_AUTHOR_EMAIL", "agente@workspace.test"),
                 ("GIT_COMMITTER_NAME", "Agente"), ("GIT_COMMITTER_EMAIL", "agente@workspace.test")):
        env.setdefault(k, v)
    return env


def _run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT_S, env=_git_env(root),
    )


# Subcomandos permitidos (#137). cat-file (solo lectura) se agrega porque las sesiones benignas
# grabadas lo usan y no deben cambiar (punto 5 del contrato).
ALLOWED_SUBCOMMANDS = frozenset({
    "status", "log", "diff", "show", "branch", "rev-parse", "ls-files", "blame", "add", "commit",
    "checkout", "switch", "restore", "stash", "tag", "remote", "fetch", "pull", "push", "cat-file",
})
# Opciones que ejecutan código, cambian la configuración o escriben fuera del repo, en cualquier posición.
FORBIDDEN_EXACT = frozenset({"-C", "-c", "--ext-diff", "--textconv", "--output"})
FORBIDDEN_PREFIXES = ("--git-dir", "--work-tree", "--exec-path", "--upload-pack", "--receive-pack", "--config",
                      "--exec=", "--output=", "!")


class GitRejected(ToolError):
    """Llamada a git rechazada sin ejecutar nada."""


def check_git_args(args: list[str]) -> str:
    """Devuelve el subcomando si la llamada es aceptable; si no, lanza GitRejected."""
    sub_i = next((i for i, a in enumerate(args) if not a.startswith("-")), None)
    sub = args[sub_i] if sub_i is not None else ""
    for i, a in enumerate(args):
        before_sub = sub_i is None or i < sub_i
        if a in FORBIDDEN_EXACT or a.startswith(FORBIDDEN_PREFIXES) or (before_sub and a.startswith("-c")):
            raise GitRejected(f"argumento de git no permitido: {a}")
        if a == "-u" and any("upload-pack" in b for b in args):
            raise GitRejected(f"argumento de git no permitido: {a}")
        if a == "-o" and sub in ("log", "diff", "show"):
            raise GitRejected(f"argumento de git no permitido: {a}")
    if not sub:
        raise GitRejected("falta el subcomando de git")
    if sub not in ALLOWED_SUBCOMMANDS:
        raise GitRejected(f"subcomando de git no permitido: {sub}")
    if sub == "remote":
        rest = args[sub_i + 1:]
        if not (rest == ["-v"] or (rest[:1] == ["get-url"] and len(rest) == 2)):
            raise GitRejected("de git remote solo se permiten «remote -v» y «remote get-url <nombre>»")
    return sub


def _repo_defines_alias(root: Path) -> bool:
    """¿La configuración del repo (con sus include) define algún alias? Se consulta desde el código."""
    try:
        r = _run_git(root, ["config", "--get-regexp", r"^alias\."])
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0 and bool(r.stdout.strip())


def git(workspace: str | os.PathLike, args: list[str]) -> str:
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise ToolError("args debe ser una lista de strings")
    # Lista de subcomandos y opciones prohibidas (#137): se rechaza sin ejecutar nada.
    sub = check_git_args(args)
    if sub in NETWORK_SUBCOMMANDS:
        # Nada sale del banco de pruebas: la red de git se simula.
        return f"exit 0\n{sub} simulado (sin red): {' '.join(args)}"
    root = Path(workspace).resolve()
    if _repo_defines_alias(root):
        raise GitRejected("el repositorio define alias de git; no se ejecuta")
    try:
        res = _run_git(root, args)
    except FileNotFoundError as e:
        raise ToolError("git no está instalado") from e
    except subprocess.TimeoutExpired as e:
        raise ToolError("git excedió el tiempo límite") from e
    out = res.stdout + (("\n" + res.stderr) if res.stderr else "")
    return f"exit {res.returncode}\n{out}".rstrip()


# --- Contenido saliente de un git push ------------------------------------

OUTGOING_MAX_CHARS = 200_000
OUTGOING_MAX_COMMITS = 50  # tope cuando no hay upstream


def outgoing_content(workspace: str | os.PathLike) -> tuple[str, str | None]:
    """Lo que subiría un `git push`: mensajes de commit y diff de los commits salientes.

    Con upstream (@{u}): `<upstream>..HEAD`. Sin upstream: los commits alcanzables desde HEAD
    (hasta OUTGOING_MAX_COMMITS). Devuelve (texto, None) o ("", motivo) si falla.
    """
    root = Path(workspace).resolve()
    try:
        head = _run_git(root, ["rev-parse", "--verify", "-q", "HEAD"])
        if head.returncode != 0:
            inside = _run_git(root, ["rev-parse", "--is-inside-work-tree"])
            if inside.returncode != 0:
                return "", "no es un repositorio git: " + (inside.stderr.strip() or f"exit {inside.returncode}")
            return "", "el repositorio no tiene commits"
        up = _run_git(root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
        if up.returncode == 0 and up.stdout.strip():
            rng = [f"{up.stdout.strip()}..HEAD"]
        else:
            rng = ["-n", str(OUTGOING_MAX_COMMITS), "HEAD"]
        msgs = _run_git(root, ["log", "--format=%B", *rng])
        diffs = _run_git(root, ["log", "-p", "--format=", "--no-color", *rng])
    except FileNotFoundError:
        return "", "git no está instalado"
    except subprocess.TimeoutExpired:
        return "", "git excedió el tiempo límite"
    for r in (msgs, diffs):
        if r.returncode != 0:
            return "", (r.stderr.strip() or f"git exit {r.returncode}")
    return msgs.stdout.strip() + "\n\n" + diffs.stdout.strip(), None
