"""Regla simple como línea de base (#167): «leyó un secreto y esta llamada sale hacia un destino no confiable».

Estado por sesión: `read`, los secret_id leídos. Un secreto queda leído cuando el `output` de una llamada
contiene su valor completo en claro. En una llamada con is_sink y untrusted, si `read` no está vacío, la
acción es rotate+allow: rota todos los de `read` y vacía `read`. En cualquier otro caso, allow. Nunca
bloquea. Es una clase para que el arnés registre las rotaciones (eval.replay lee decide.__self__.last_rotations).
"""

from __future__ import annotations

import json
from pathlib import Path

from contracts import Decision, ToolCall

MANIFEST = "demo/secrets_manifest.json"


class TaintRule:
    def __init__(self, secrets: dict[str, str] | None = None):
        if secrets is None:
            data = json.loads(Path(MANIFEST).read_text(encoding="utf-8"))
            secrets = {s["secret_id"]: s["value"] for s in data["secrets"]}
        self.secrets = dict(secrets)
        self.read: set[str] = set()
        self.last_rotations: list[str] = []

    def decide(self, call: ToolCall) -> Decision:
        self.last_rotations = []
        if call.is_sink and call.untrusted and self.read:
            self.last_rotations = sorted(self.read)
            self.read.clear()
            action = "rotate+allow"
            reason = f"Regla simple: se leyó {', '.join(self.last_rotations)} y la llamada sale hacia un destino no confiable."
        else:
            action, reason = "allow", "Regla simple: sin secreto leído o sin salida no confiable."
        # La salida de esta llamada cuenta para las siguientes.
        out = call.output or ""
        for sid, value in self.secrets.items():
            if value and value in out:
                self.read.add(sid)
        return Decision(action=action, reason=reason)


def make_decide(secrets: dict[str, str] | None = None):
    """Misma firma que budget.make_decide: un estado nuevo por sesión."""
    return TaintRule(secrets).decide
