"""Arnés de reproducción (tarea 6): sesiones grabadas de ToolCall -> decide() -> eventos.

Sin LLM y sin ejecutar herramientas: cada ToolCall ya trae su `output` grabado.
"""

from __future__ import annotations

import importlib
import json
import time
from pathlib import Path
from typing import Callable, Iterable

from contracts import Decision, Event, ToolCall

Decide = Callable[[ToolCall], Decision]
MakeDecide = Callable[[], Decide]


def load_session(path: str | Path) -> list[ToolCall]:
    """Una sesión por archivo, un ToolCall por línea. Devuelve las llamadas en orden de t."""
    calls = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    calls.append(ToolCall.model_validate_json(line))
                except ValueError as exc:
                    raise ValueError(f"{path}:{n}: ToolCall inválido: {exc}") from exc
    return sorted(calls, key=lambda c: c.t)


def load_sessions(folder: str | Path) -> list[list[ToolCall]]:
    """Todas las sesiones *.jsonl de la carpeta, en orden de nombre de archivo."""
    files = sorted(Path(folder).glob("*.jsonl"))
    if not files:
        raise FileNotFoundError(f"no hay sesiones *.jsonl en {folder}")
    return [load_session(p) for p in files]


def replay(sessions: Iterable[list[ToolCall]], make_decide: MakeDecide) -> list[Event]:
    """Por cada llamada, un evento tool_call y uno decision (source="proxy").

    make_decide() se llama una vez por sesión: cada sesión parte con estado limpio.
    latency_ms se mide aquí (lo que tarda decide); ts es la hora de reproducción.
    """
    events: list[Event] = []
    for session in sessions:
        decide = make_decide()
        for call in sorted(session, key=lambda c: c.t):
            events.append(Event(ts=time.time(), session_id=call.session_id, source="proxy",
                                kind="tool_call", call_id=call.id, data=call.model_dump(mode="json")))
            t0 = time.perf_counter()
            decision = decide(call)
            latency = (time.perf_counter() - t0) * 1000
            if not isinstance(decision, Decision):
                decision = Decision.model_validate(decision)
            decision = decision.model_copy(update={"latency_ms": latency})
            events.append(Event(ts=time.time(), session_id=call.session_id, source="proxy",
                                kind="decision", call_id=call.id, data=decision.model_dump(mode="json")))
    return events


def write_events(events: Iterable[Event], out: str | Path) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for e in events:
            f.write(e.model_dump_json() + "\n")
    return out


def load_factory(spec: str) -> MakeDecide:
    """'modulo.sub:fabrica' -> la fábrica make_decide."""
    module, _, name = spec.partition(":")
    if not module or not name:
        raise ValueError(f"--decide debe ser modulo:fabrica, llegó {spec!r}")
    factory = getattr(importlib.import_module(module), name)
    if not callable(factory):
        raise TypeError(f"{spec} no es invocable")
    return factory


def comparable(events: Iterable[Event]) -> list[str]:
    """Forma canónica para comparar corridas: ignora ts y latency_ms."""
    out = []
    for e in events:
        d = e.model_dump(mode="json")
        d.pop("ts", None)
        if e.kind == "decision" and isinstance(d.get("data"), dict):
            d["data"].pop("latency_ms", None)
        out.append(json.dumps(d, sort_keys=True, ensure_ascii=False))
    return out
