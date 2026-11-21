"""Allowlist + detect-secrets: bloquea si cualquiera de las dos bloquea."""

from __future__ import annotations

from typing import Callable

from contracts import Decision, ToolCall
from eval.baselines import allowlist, detect_secrets_baseline


def make_decide() -> Callable[[ToolCall], Decision]:
    def decide(call: ToolCall) -> Decision:
        if not call.is_sink:
            return Decision(action="allow", reason="Combinada: no es un sumidero: se permite.")
        ok_a, why_a = allowlist.check(call)
        ok_d, why_d = detect_secrets_baseline.check(call)
        action = "allow" if ok_a and ok_d else "block"
        return Decision(action=action, reason=f"Combinada: allowlist: {why_a} detect-secrets: {why_d}")

    return decide
