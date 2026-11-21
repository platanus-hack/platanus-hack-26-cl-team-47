"""Servidor MCP de prueba (stdio) con una sola herramienta: read_file.

Los archivos son virtuales (no existen en disco) y su contenido incluye el
NONCE del entorno: si el agente lo conoce, lo obtuvo por MCP. Cada llamada
queda en FAKE_MCP_LOG junto con el SESSION_ID que recibió el servidor.
"""

import json
import os

from mcp.server.mcpserver import MCPServer

NONCE = os.environ.get("NONCE", "sin-nonce")
FILES = {"notas.txt": f"contenido secreto de prueba {NONCE}\n"}

server = MCPServer("fake-proxy")


def _log(entry: dict) -> None:
    path = os.environ.get("FAKE_MCP_LOG")
    if path:
        entry["session_id"] = os.environ.get("SESSION_ID")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


@server.tool()
def read_file(path: str) -> str:
    """Lee un archivo del repositorio."""
    _log({"tool": "read_file", "path": path})
    if path not in FILES:
        raise ValueError(f"no existe: {path}")
    return FILES[path]


if __name__ == "__main__":
    server.run("stdio")
