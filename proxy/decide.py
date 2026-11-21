"""Funciones de decisión intercambiables: decide(call: ToolCall) -> Decision."""

from contracts import Decision, ToolCall


def allow_all(call: ToolCall) -> Decision:
    return Decision(action="allow", reason="allow_all")


def block_all(call: ToolCall) -> Decision:
    return Decision(action="block", reason="block_all")
