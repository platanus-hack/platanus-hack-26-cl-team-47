"""Tests del agente mínimo (3b): sin red, con el LLM falso y un servidor MCP de prueba."""

import asyncio
import json
import re
import sys
import uuid
from pathlib import Path

import pytest

from proxy.agent import ScriptedLLM, run_agent, text_reply, tool_reply
from proxy.agent.llm import last_tool_result_text

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parent
SERVER = f'"{sys.executable}" "{HERE / "fake_server.py"}"'


@pytest.fixture
def env(tmp_path, monkeypatch):
    nonce = uuid.uuid4().hex
    server_log = tmp_path / "server.jsonl"
    monkeypatch.setenv("NONCE", nonce)
    monkeypatch.setenv("FAKE_MCP_LOG", str(server_log))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.delenv("SESSION_ID", raising=False)
    return {"nonce": nonce, "server_log": server_log, "agent_log": tmp_path / "logs" / "agent.jsonl"}


def lines(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def run(task, llm, **kw):
    return asyncio.run(run_agent(task, SERVER, llm, **kw))


def test_sin_herramientas_escondidas(env):
    """Se le pide leer un archivo: la lectura aparece en el servidor MCP, no solo
    en la transcripción, y el contenido (que solo existe en el servidor) llega
    a la respuesta final."""
    llm = ScriptedLLM([
        tool_reply("read_file", {"path": "notas.txt"}, "tu_1"),
        lambda messages, tools: text_reply("El archivo dice: " + last_tool_result_text(messages)),
    ])
    result = run("Lee notas.txt y dime qué dice.", llm)

    reads = [e for e in lines(env["server_log"]) if e["tool"] == "read_file"]
    assert [r["path"] for r in reads] == ["notas.txt"]
    assert env["nonce"] in result.final_text
    assert result.stopped == "end_turn" and result.steps == 2

    events = lines(env["agent_log"])
    kinds = [e["kind"] for e in events]
    assert kinds == ["message", "tool_use", "tool_result", "message"]
    assert all(e["source"] == "agent" and e["session_id"] == result.session_id for e in events)
    use, res = events[1], events[2]
    assert use["call_id"] == res["call_id"] == "tu_1"
    assert env["nonce"] in res["data"]["output"]


def test_mismo_session_id_en_agente_y_servidor(env):
    llm = ScriptedLLM([tool_reply("read_file", {"path": "notas.txt"}, "tu_1"), text_reply("listo")])
    result = run("lee", llm, session_id="sesion-test-47")
    assert result.session_id == "sesion-test-47"
    assert {e["session_id"] for e in lines(env["server_log"])} == {"sesion-test-47"}


def test_solo_ofrece_las_herramientas_del_mcp(env):
    llm = ScriptedLLM([text_reply("nada que hacer")])
    run("hola", llm)
    assert [t["name"] for t in llm.seen_tools[0]] == ["read_file"]
    assert llm.seen_tools[0][0]["input_schema"]["properties"]["path"]["type"] == "string"


def test_error_de_herramienta_vuelve_al_llm(env):
    llm = ScriptedLLM([
        tool_reply("read_file", {"path": "no-existe.txt"}, "tu_1"),
        tool_reply("herramienta_inventada", {}, "tu_2"),
        text_reply("me rindo"),
    ])
    result = run("lee algo", llm)
    results = [e for e in lines(env["agent_log"]) if e["kind"] == "tool_result"]
    assert [r["data"]["is_error"] for r in results] == [True, True]
    assert result.final_text == "me rindo"


def test_corta_en_max_steps(env):
    llm = ScriptedLLM([tool_reply("read_file", {"path": "notas.txt"}, f"tu_{i}") for i in range(10)])
    result = run("lee para siempre", llm, max_steps=3)
    assert result.stopped == "max_steps" and result.steps == 3
    assert len(lines(env["server_log"])) == 3


def test_el_bucle_no_tiene_io_propio():
    """El bucle y el LLM no abren archivos ni hacen red por su cuenta
    (el SDK de Anthropic solo habla con la API del LLM)."""
    banned = re.compile(r"\bopen\(|read_text|write_text|\bhttpx\b|\brequests\b|\burllib\b|\bsocket\b|"
                        r"\bsubprocess\b|os\.system|os\.popen")
    for name in ("loop.py", "llm.py", "__main__.py"):
        src = (AGENT_DIR / name).read_text(encoding="utf-8")
        assert not banned.search(src), f"{name} tiene E/S propia: {banned.search(src).group(0)}"
