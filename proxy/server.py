"""Servidor MCP por stdio: python -m proxy.server

Expone las seis herramientas y delega cada llamada en Proxy.handle.
Variables: AGENT_WORKSPACE (por defecto demo/repo), SESSION_ID, LOG_DIR,
PROXY_MODE (live = detector + rotación en vault.test; sin valor = allow_all),
SECRETS_MANIFEST (manifiesto de secretos; por defecto demo/secrets_manifest.json),
LEDGER_PATH (con live: cuenta compartida por archivo entre procesos, #138),
PROXY_RECORD=1 (graba la sesión en SESSIONS_DIR, por defecto logs/sessions).
Guía de inicio: docs/QUICKSTART.md.
"""

from __future__ import annotations

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

import os

from .core import Proxy


def default_proxy() -> Proxy:
    """PROXY_MODE=live -> detector real con rotación en el gestor; sin la variable, allow_all.
    PROXY_RECORD=1 -> graba cada sesión en SESSIONS_DIR (por defecto logs/sessions)."""
    if os.environ.get("PROXY_MODE", "").strip().lower() == "live":
        from .live import DEFAULT_MANIFEST, build_live_proxy

        proxy = build_live_proxy(manifest_path=os.environ.get("SECRETS_MANIFEST") or DEFAULT_MANIFEST)
    else:
        proxy = Proxy()
    if os.environ.get("PROXY_RECORD", "").strip().lower() in ("1", "true", "yes"):
        from .recorder import SessionRecorder

        proxy.recorder = SessionRecorder()
    return proxy


def build_server(proxy: Proxy | None = None):
    proxy = proxy or default_proxy()
    server = _Server("alicanto")

    @server.tool()
    def read_file(path: str) -> str:
        """Lee un archivo de texto del repositorio de trabajo."""
        return proxy.handle("read_file", {"path": path})[0]

    @server.tool()
    def list_dir(path: str = ".") -> str:
        """Lista un directorio del repositorio de trabajo."""
        return proxy.handle("list_dir", {"path": path})[0]

    @server.tool()
    def http_request(method: str, url: str, headers: dict[str, str] | None = None, body: str = "") -> str:
        """Hace una petición HTTP. Devuelve el código de estado en la primera línea y luego el cuerpo."""
        return proxy.handle("http_request", {"method": method, "url": url, "headers": headers or {}, "body": body})[0]

    @server.tool()
    def git(args: list[str]) -> str:
        """Corre git en el repositorio de trabajo, por ejemplo ["status"] o ["log", "-3"]."""
        return proxy.handle("git", {"args": args})[0]

    @server.tool()
    def github_issue(repo: str, title: str, body: str) -> str:
        """Crea un issue en GitHub (repo = "owner/nombre")."""
        return proxy.handle("github_issue", {"repo": repo, "title": title, "body": body})[0]

    @server.tool()
    def github_comment(repo: str, number: int, body: str) -> str:
        """Comenta un issue de GitHub."""
        return proxy.handle("github_comment", {"repo": repo, "number": number, "body": body})[0]

    server.proxy = proxy
    return server


def main() -> None:
    build_server().run("stdio")


if __name__ == "__main__":
    main()
