"""Contratos congelados (tarea 1a). No cambiar sin aviso en el board y visto bueno del líder."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

Label = Literal["benign", "attack"]
Action = Literal["allow", "block", "rotate+allow", "rotate+block"]
Source = Literal["proxy", "agent", "attacker"]

KINDS: dict[str, frozenset[str]] = {
    "proxy": frozenset({"tool_call", "decision", "rotation"}),
    "agent": frozenset({"message", "tool_use", "tool_result"}),
    "attacker": frozenset({"received"}),
}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolCall(_Strict):
    id: str
    t: int = Field(ge=1, description="Índice de la llamada en la sesión, desde 1")
    tool: str
    args: dict[str, Any]
    output: Optional[str] = None
    resources: list[str] = Field(default_factory=list, description="path | env | service")
    is_sink: bool = False
    untrusted: bool = False
    session_id: str
    label: Optional[Label] = None  # None en corridas en vivo


class Leak(_Strict):
    bits: float = Field(ge=0)
    fraction: float = Field(ge=0, le=1)


class Decision(_Strict):
    action: Action
    S: float = 0.0
    R_plus: float = 0.0
    leak: dict[str, Leak] = Field(default_factory=dict)
    path: list[str] = Field(default_factory=list)
    reason: str = ""
    latency_ms: float = 0.0

    @property
    def allowed(self) -> bool:
        return self.action.endswith("allow")


class Event(_Strict):
    ts: float = Field(description="Epoch en segundos")
    session_id: str
    source: Source
    kind: str
    call_id: Optional[str] = None
    data: Any = None

    @model_validator(mode="after")
    def _kind_matches_source(self) -> "Event":
        if self.kind not in KINDS[self.source]:
            raise ValueError(
                f"kind {self.kind!r} no es válido para source {self.source!r}; "
                f"válidos: {sorted(KINDS[self.source])}"
            )
        return self


def log_dir() -> Path:
    return Path(os.environ.get("LOG_DIR", "logs"))


def log_path(source: str) -> Path:
    return log_dir() / f"{source}.jsonl"


def write_event(event: Event) -> Path:
    """Agrega el evento como una línea JSON a logs/<source>.jsonl (carpeta: LOG_DIR)."""
    path = log_path(event.source)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = event.model_dump_json()
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return path


def read_events(path: str | os.PathLike) -> list[Event]:
    """Lee un archivo .jsonl de eventos. Ignora líneas vacías."""
    events: list[Event] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(Event.model_validate(json.loads(line)))
    return events


_HOSTS_FILE = Path(__file__).with_name("hosts.json")


def load_hosts() -> dict[str, str]:
    """Mapa host .test -> URL base local."""
    with open(_HOSTS_FILE, encoding="utf-8") as f:
        return json.load(f)
