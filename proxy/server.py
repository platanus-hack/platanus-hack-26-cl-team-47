"""Servidor MCP por stdio: python -m proxy.server

Expone las seis herramientas y delega cada llamada en Proxy.handle.
Variables: AGENT_WORKSPACE (por defecto demo/repo), SESSION_ID, LOG_DIR.
"""

from __future__ import annotations

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from .core import Proxy


def build_server(proxy: Proxy | None = None):
    proxy = proxy or Proxy()
    server = _Server("leak-meter-proxy")

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
