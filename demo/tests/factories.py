"""Fábricas de decisión de prueba para run_split (no son el detector)."""

from contracts import Decision, ToolCall


def rotate_at(t: int = 20):
    """make_decide: rotate+allow en la llamada t, allow en las demás."""

    def decide(call: ToolCall) -> Decision:
        if call.t == t:
            return Decision(action="rotate+allow", reason=f"prueba: rotar en t={t}", path=[call.id])
        return Decision(action="allow")

    return decide
