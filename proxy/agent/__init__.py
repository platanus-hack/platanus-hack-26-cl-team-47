"""Agente mínimo del banco de pruebas (tarea 3b). Solo actúa por MCP."""

from .llm import LLM, AnthropicLLM, Reply, ScriptedLLM, text_reply, tool_reply
from .loop import RunResult, run_agent

__all__ = ["LLM", "AnthropicLLM", "Reply", "ScriptedLLM", "text_reply", "tool_reply", "RunResult", "run_agent"]
