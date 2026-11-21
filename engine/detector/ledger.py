"""Cuenta global por secreto para un enjambre de agentes (tarea #114, paso 9o).

Varios `Detector` (uno por agente o sesión) comparten un solo `SharedLedger`. El ledger tiene el
único `BitsEngine` del enjambre: lo que cada agente envía se suma en las mismas posiciones `K` y
`cand` de cada secreto, así que la fracción filtrada que miran las reglas es la del enjambre entero.
También son compartidos la exposición, la versión de cada secreto, el historial de rotaciones y el
reloj (`step`, llamadas vistas por todo el enjambre). La evidencia por sesión (CUSUM, DAG, camino
explicativo) sigue siendo de cada `Detector`.

Es una capacidad general: no responde a ninguna familia de ataque concreta.

Concurrencia: un solo proceso y un solo hilo. No hay locks; varios procesos o máquinas a la vez
quedan fuera de alcance.

`save` guarda la cuenta en JSON para retomarla en otra sesión. Nunca escribe valores de secretos:
solo posiciones, versiones, exposición, pasos de rotación y relojes.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Iterable, Mapping

from engine.bits import BitsEngine


class SharedLedger:
    def __init__(self, secrets: dict[str, str], allowed_hosts: Mapping[str, Iterable[str]] | None = None,
                 k: int = 8, W: int = 50):
        self.allowed_hosts: dict[str, set[str]] = {
            sid: {h.lower() for h in (allowed_hosts or {}).get(sid, ())} for sid in secrets
        }
        self.bits = BitsEngine(dict(secrets), k=k, W=W, allowed_hosts=self.allowed_hosts)
        self.values: dict[str, str] = dict(secrets)          # solo en memoria; nunca se guarda
        self.version: dict[str, int] = {sid: 1 for sid in secrets}
        self.exposed: set[str] = set()
        self.step = 0
        self.rotation_steps: dict[str, list[int]] = {sid: [] for sid in secrets}
        # Valores nuevos por defecto de todo el enjambre: un solo generador, para que dos agentes
        # con la misma semilla no repitan el valor que otro ya puso.
        self.rng = random.Random(0)

    @classmethod
    def from_manifest(cls, path: str = "demo/secrets_manifest.json", **kw: Any) -> "SharedLedger":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        secrets = {s["secret_id"]: s["value"] for s in data["secrets"]}
        allowed = {s["secret_id"]: s.get("allowed_hosts", []) for s in data["secrets"]}
        kw.setdefault("allowed_hosts", allowed)
        return cls(secrets, **kw)

    def tick(self) -> int:
        """Una llamada más del enjambre. La llama cada Detector al empezar decide()."""
        self.step += 1
        return self.step

    def rotate(self, secret_id: str, new_value: str) -> int:
        """Reinicia la cuenta del secreto con su valor nuevo y devuelve la versión nueva."""
        self.bits.rotate(secret_id, new_value)
        self.values[secret_id] = new_value
        self.version[secret_id] += 1
        self.exposed.discard(secret_id)
        self.rotation_steps[secret_id].append(self.step)
        return self.version[secret_id]

    # --- persistencia ------------------------------------------------------

    def save(self, path: str) -> None:
        state = {
            "step": self.step,
            "version": dict(sorted(self.version.items())),
            "exposed": sorted(self.exposed),
            "rotation_steps": {sid: list(v) for sid, v in sorted(self.rotation_steps.items())},
            "bits": self.bits.export_state(),
        }
        Path(path).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    def load_state(self, path: str, versions: dict[str, int] | None = None) -> None:
        """Restaura lo guardado por save(). `versions` son las versiones vigentes en el gestor: si la de
        un secreto no coincide con la guardada, el estado guardado de ese secreto se descarta (queda en
        cero con la versión del gestor). Los secretos que este ledger no conoce se ignoran."""
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        saved_version = {sid: int(v) for sid, v in state.get("version", {}).items()}
        keep = {sid for sid in self.values if sid in saved_version}
        if versions is not None:
            for sid, v in versions.items():
                if sid in self.version:
                    self.version[sid] = int(v)
            keep = {sid for sid in keep if versions.get(sid, saved_version[sid]) == saved_version[sid]}

        self.step = int(state.get("step", 0))
        for sid in keep:
            self.version[sid] = saved_version[sid]
        self.exposed = {sid for sid in state.get("exposed", []) if sid in keep}
        saved_rot = state.get("rotation_steps", {})
        self.rotation_steps = {sid: ([int(x) for x in saved_rot.get(sid, [])] if sid in keep else [])
                               for sid in self.values}

        bits = state.get("bits") or {}
        self.bits.import_state({"step": bits.get("step", 0),
                                "secrets": {sid: s for sid, s in (bits.get("secrets") or {}).items() if sid in keep}})
        for sid in set(self.values) - keep:   # descartados: en cero con el valor vigente
            self.bits.rotate(sid, self.values[sid])
