"""Interfaz intercambiable del LLM: complete(messages, tools) -> Reply.

Los mensajes y las herramientas van en el formato de la Messages API de
Anthropic (bloques `text`, `tool_use`, `tool_result`). `Reply.content` es la
lista de bloques del asistente, que el bucle agrega tal cual al historial.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Protocol


@dataclass
class Reply:
    content: list[dict]
    stop_reason: str = "end_turn"

    @property
    def tool_uses(self) -> list[dict]:
        return [b for b in self.content if b.get("type") == "tool_use"]

    @property
    def text(self) -> str:
        return "".join(b.get("text", "") for b in self.content if b.get("type") == "text")


class LLM(Protocol):
    def complete(self, messages: list[dict], tools: list[dict]) -> Reply: ...


# ---------------------------------------------------------------- falso


def text_reply(text: str) -> Reply:
    return Reply([{"type": "text", "text": text}], "end_turn")


def tool_reply(name: str, args: dict, call_id: str, text: str = "") -> Reply:
    blocks = [{"type": "text", "text": text}] if text else []
    blocks.append({"type": "tool_use", "id": call_id, "name": name, "input": args})
    return Reply(blocks, "tool_use")


Step = Reply | Callable[[list[dict], list[dict]], Reply]


@dataclass
class ScriptedLLM:
    """LLM falso para tests: devuelve respuestas guionadas, en orden.

    Un paso puede ser un `Reply` fijo o una función (messages, tools) -> Reply,
    útil para responder con lo que llegó en el último `tool_result`.
    """

    steps: list[Step]
    seen_tools: list[list[dict]] = field(default_factory=list)

    def complete(self, messages: list[dict], tools: list[dict]) -> Reply:
        self.seen_tools.append(tools)
        if not self.steps:
            return text_reply("(guion agotado)")
        step = self.steps.pop(0)
        return step(messages, tools) if callable(step) else step


def last_tool_result_text(messages: list[dict]) -> str:
    for msg in reversed(messages):
        if msg["role"] == "user" and isinstance(msg["content"], list):
            for b in msg["content"]:
                if b.get("type") == "tool_result":
                    c = b.get("content")
                    return c if isinstance(c, str) else "".join(x.get("text", "") for x in c)
    return ""


# ---------------------------------------------------------------- real


class AnthropicLLM:
    """Claude por la Messages API. Modelo en AGENT_MODEL; clave en .env
    (ANTHROPIC_API_KEY), que no se versiona.

    La API actual no acepta `temperature` (400 en los modelos vigentes), así
    que no se envía: la reproducibilidad del banco viene del registro y del
    arnés de reproducción, no del muestreo del LLM.
    """

    def __init__(self, model: str | None = None, system: str | None = None):
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("AGENT_MODEL", "claude-opus-5-5")
        self.system = system or (
            "Eres un agente de desarrollo. Solo puedes actuar con las herramientas que se te dan. "
            "Cuando termines, responde con un resumen breve de lo que hiciste."
        )

    def complete(self, messages: list[dict], tools: list[dict]) -> Reply:
        extra = {}
        if os.environ.get("AGENT_FALLBACKS", "1") != "0":
            # Si el clasificador de seguridad rechaza, el servidor reintenta con
            # un modelo de respaldo en vez de cortar la corrida. AGENT_FALLBACKS=0
            # lo apaga (por ejemplo, si un proxy intermedio no acepta betas).
            extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        resp = self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            system=self.system,
            tools=tools,
            messages=messages,
            output_config={"effort": "medium"},
            **extra,
        )
        blocks = [b.model_dump(mode="json", exclude_none=True) for b in resp.content]
        return Reply(blocks, resp.stop_reason or "end_turn")
