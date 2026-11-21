"""Bucle del agente mínimo: tarea + herramientas MCP -> LLM -> herramienta por MCP -> repetir.

El agente no tiene herramientas propias: este módulo no lee archivos ni hace
peticiones de red. Todo lo que el LLM pide pasa por el servidor MCP (el proxy).
"""

from __future__ import annotations

import os
import shlex
import sys
import uuid
from dataclasses import dataclass

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .llm import LLM
from .transcript import Transcript


@dataclass
class RunResult:
    session_id: str
    final_text: str
    steps: int
    stopped: str  # "end_turn" | "max_steps" | "refusal" | otro stop_reason


def mcp_params(command: str, session_id: str) -> StdioServerParameters:
    """El servidor MCP recibe el mismo SESSION_ID para que proxy y agente
    escriban eventos de la misma sesión."""
    # En Windows shlex no-posix conserva las comillas: se quitan a mano.
    argv = [a.strip('"') for a in shlex.split(command, posix=os.name != "nt")]
    if argv and argv[0] in ("python", "python3"):
        argv[0] = sys.executable
    env = {**os.environ, "SESSION_ID": session_id}
    return StdioServerParameters(command=argv[0], args=argv[1:], env=env)


def to_llm_tool(tool) -> dict:
    # mcp 2.x usa snake_case; mcp 1.x, camelCase.
    schema = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None) or {"type": "object"}
    return {"name": tool.name, "description": tool.description or "", "input_schema": schema}


def result_text(result) -> str:
    parts = []
    for c in getattr(result, "content", None) or []:
        parts.append(c.text if getattr(c, "type", "") == "text" else f"[{getattr(c, 'type', 'contenido')}]")
    return "\n".join(parts)


async def run_agent(task: str, mcp_command: str, llm: LLM, max_steps: int = 30,
                    session_id: str | None = None) -> RunResult:
    session_id = session_id or os.environ.get("SESSION_ID") or uuid.uuid4().hex
    log = Transcript(session_id)
    messages: list[dict] = [{"role": "user", "content": task}]
    log.emit("message", {"role": "user", "text": task})

    async with stdio_client(mcp_params(mcp_command, session_id)) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            tools = [to_llm_tool(t) for t in (await mcp.list_tools()).tools]

            reply = None
            for step in range(1, max_steps + 1):
                reply = llm.complete(messages, tools)
                messages.append({"role": "assistant", "content": reply.content})
                if reply.text:
                    log.emit("message", {"role": "assistant", "text": reply.text})

                if not reply.tool_uses:
                    return RunResult(session_id, reply.text, step, reply.stop_reason)

                results = []
                for use in reply.tool_uses:
                    log.emit("tool_use", {"name": use["name"], "input": use["input"]}, use["id"])
                    try:
                        res = await mcp.call_tool(use["name"], use["input"])
                        text = result_text(res)
                        is_error = bool(getattr(res, "is_error", None) or getattr(res, "isError", None))
                    except Exception as exc:  # error de transporte o herramienta desconocida
                        text, is_error = f"error: {exc}", True
                    log.emit("tool_result", {"name": use["name"], "output": text, "is_error": is_error}, use["id"])
                    results.append({"type": "tool_result", "tool_use_id": use["id"],
                                    "content": text, "is_error": is_error})
                # Todos los resultados en un solo mensaje de usuario.
                messages.append({"role": "user", "content": results})

    return RunResult(session_id, reply.text if reply else "", max_steps, "max_steps")
