"""Transcripción del agente en logs/agent.jsonl con el formato Event de contracts.

Event = {ts, session_id, source, kind, call_id, data}. Usa contracts.write_event
cuando el paquete existe (tarea 1a); si no, escribe la misma línea JSON.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


class Transcript:
    def __init__(self, session_id: str):
        self.session_id = session_id

    def emit(self, kind: str, data: dict, call_id: str | None = None) -> None:
        event = {"ts": time.time(), "session_id": self.session_id, "source": "agent",
                 "kind": kind, "call_id": call_id, "data": data}
        try:
            from contracts import Event, write_event
        except ImportError:
            log_dir = Path(os.environ.get("LOG_DIR", "logs"))
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / "agent.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        else:
            write_event(Event(**event))
