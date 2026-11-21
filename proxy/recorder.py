"""Grabación de sesiones como trazas reproducibles (tarea 9d).

Un archivo por sesión, <out_dir>/<session_id>.jsonl, un ToolCall por línea con
`output` ya completado (null si la llamada fue bloqueada). Se carga con
eval.replay.core.load_session sin cambios.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from contracts import ToolCall

DEFAULT_SESSIONS_DIR = "logs/sessions"


class SessionRecorder:
    def __init__(self, out_dir: str | None = None):
        self.out_dir = Path(out_dir or os.environ.get("SESSIONS_DIR") or DEFAULT_SESSIONS_DIR)
        self._lock = threading.Lock()

    def path(self, session_id: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in session_id)
        return self.out_dir / f"{safe}.jsonl"

    def record(self, call: ToolCall, output: str | None, executed: bool) -> None:
        recorded = call.model_copy(update={"output": output if executed else None})
        line = json.dumps(recorded.model_dump(mode="json"), ensure_ascii=False)
        p = self.path(call.session_id)
        with self._lock:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(line + "\n")
