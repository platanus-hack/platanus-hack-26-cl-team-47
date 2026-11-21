"""Presupuesto acumulado de bits (réplica de Nimbus): suma por sesión contra un umbral fijo.

Mismo estimador que el medidor (engine.bits.BitsEngine), sin CUSUM y sin rotación, para
aislar el efecto de la regla. Al pasar el presupuesto bloquea esa llamada y todos los
sumideros siguientes de la sesión.
"""

from __future__ import annotations

from typing import Callable

from contracts import Decision, ToolCall
from engine.bits import BitsEngine

MANIFEST = "demo/secrets_manifest.json"


def make_decide(
    budget_bits: float = 96.0, secrets: dict[str, str] | None = None
) -> Callable[[ToolCall], Decision]:
    engine = BitsEngine(secrets) if secrets is not None else BitsEngine.from_manifest(MANIFEST)
    state = {"exhausted_by": None}

    def decide(call: ToolCall) -> Decision:
        report = engine.observe(call)
        leak = {}
        over = None
        for sid, r in report.items():
            total = float(r.get("bits", 0.0)) + float(r.get("candidate_bits", 0.0))
            H = engine.H(sid) or 160.0
            leak[sid] = {"bits": total, "fraction": min(total / H, 1.0)}
            if total >= budget_bits and over is None:
                over = (sid, total)

        if state["exhausted_by"] is None and over is not None:
            state["exhausted_by"] = over[0]
            return Decision(action="block", leak=leak,
                            reason=f"Presupuesto: {over[0]} acumula {over[1]:.0f} bits ≥ {budget_bits:.0f}.")
        if state["exhausted_by"] is not None and call.is_sink:
            return Decision(action="block", leak=leak,
                            reason=f"Presupuesto agotado antes por {state['exhausted_by']}: se bloquean los sumideros.")
        why = "no es un sumidero" if not call.is_sink else f"bajo el presupuesto de {budget_bits:.0f} bits"
        return Decision(action="allow", leak=leak, reason=f"Presupuesto: {why}.")

    return decide
