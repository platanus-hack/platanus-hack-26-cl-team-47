"""Punta a punta: agente mínimo (3b) -> python -m proxy.server (stdio) -> herramienta.

La lectura debe quedar en el registro del proxy con el mismo session_id que
la transcripción del agente (prueba de «sin herramientas escondidas»).
"""

import asyncio
import sys

import pytest

from contracts import ToolCall, read_events

agent_llm = pytest.importorskip("proxy.agent.llm")
agent_loop = pytest.importorskip("proxy.agent.loop")


def test_agent_reads_through_real_proxy(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "notes.txt").write_text("contenido-unico-42\n")
    logs = tmp_path / "logs"
    monkeypatch.setenv("LOG_DIR", str(logs))
    monkeypatch.setenv("AGENT_WORKSPACE", str(ws))

    llm = agent_llm.ScriptedLLM([
        agent_llm.tool_reply("read_file", {"path": "notes.txt"}, "tu1"),
        agent_llm.text_reply("listo"),
    ])
    res = asyncio.run(agent_loop.run_agent(
        "lee notes.txt", f'"{sys.executable}" -m proxy.server', llm, max_steps=4, session_id="e2e"))
    assert res.session_id == "e2e"

    proxy_ev = read_events(logs / "proxy.jsonl")
    calls = [ToolCall.model_validate(e.data) for e in proxy_ev if e.kind == "tool_call"]
    assert [(c.tool, c.args, c.session_id) for c in calls] == [("read_file", {"path": "notes.txt"}, "e2e")]
    assert [e.kind for e in proxy_ev] == ["tool_call", "decision"]

    agent_ev = read_events(logs / "agent.jsonl")
    results = [e for e in agent_ev if e.kind == "tool_result"]
    assert results and "contenido-unico-42" in results[0].data["output"]
    assert {e.session_id for e in agent_ev} == {"e2e"}
