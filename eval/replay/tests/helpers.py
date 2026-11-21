"""Sesiones sintéticas pequeñas para los tests (no dependen de redteam/)."""

from __future__ import annotations

import random
from pathlib import Path

from contracts import Decision, ToolCall

TOOLS = [
    ("read_file", lambda i: {"path": f"docs/nota_{i}.md"}, lambda i: f"contenido de la nota {i}", ["docs/"], False),
    ("list_dir", lambda i: {"path": "src"}, lambda i: "app/\ntests/", ["src/"], False),
    ("read_file", lambda i: {"path": ".env"}, lambda i: "API_EMPRESA_KEY=<SECRET_1>", [".env"], False),
    ("http_request", lambda i: {"method": "GET", "url": "https://api.empresa.test/v1/estado", "headers": {}, "body": ""},
     lambda i: '{"ok": true}', ["api.empresa.test"], True),
]


def make_session(session_id: str, n: int, seed: int = 0, label: str | None = "benign") -> list[ToolCall]:
    rng = random.Random(seed)
    calls = []
    for t in range(1, n + 1):
        tool, args, out, res, sink = TOOLS[rng.randrange(len(TOOLS))]
        calls.append(ToolCall(id=f"{session_id}-{t:04d}", t=t, tool=tool, args=args(t), output=out(t),
                              resources=res, is_sink=sink, untrusted=False, session_id=session_id, label=label))
    return calls


def write_session(folder: Path, calls: list[ToolCall], shuffle: bool = False) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    rows = list(calls)
    if shuffle:
        random.Random(1).shuffle(rows)
    path = folder / f"{calls[0].session_id}.jsonl"
    path.write_text("".join(c.model_dump_json() + "\n" for c in rows), encoding="utf-8")
    return path


# ------------------------------------------------- fábricas de decide para tests


def allow_all():
    return lambda call: Decision(action="allow", reason="allow_all")


def counting():
    """Con estado: bloquea a partir de la tercera lectura de .env en la sesión."""
    seen = {"env": 0}

    def decide(call: ToolCall) -> Decision:
        if call.tool == "read_file" and call.args.get("path") == ".env":
            seen["env"] += 1
        if seen["env"] >= 3:
            return Decision(action="block", reason=f"lecturas de .env: {seen['env']}", path=[call.id])
        return Decision(action="allow")

    return decide


def explodes_if_executed():
    """Verifica que el arnés pase el output grabado y no intente ejecutar nada."""
    def decide(call: ToolCall) -> Decision:
        assert call.output is not None, "el arnés debe entregar el output grabado"
        return Decision(action="allow")

    return decide
