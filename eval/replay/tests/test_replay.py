"""Tests del arnés de reproducción (tarea 6)."""

import subprocess
import sys
import time
from pathlib import Path

import pytest

from contracts import read_events
from eval.replay import comparable, load_session, load_sessions, replay

from .helpers import allow_all, counting, explodes_if_executed, make_session, write_session

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


@pytest.fixture
def two_sessions(tmp_path):
    folder = tmp_path / "sessions"
    write_session(folder, make_session("s1", 50, seed=1))
    write_session(folder, make_session("s2", 50, seed=2))
    return folder


def test_ejemplo_del_issue(two_sessions):
    """2 sesiones de 50 llamadas y allow siempre -> 200 eventos, 100 decision allow."""
    events = replay(load_sessions(two_sessions), allow_all)
    assert len(events) == 200
    decisions = [e for e in events if e.kind == "decision"]
    assert len(decisions) == 100 and all(e.data["action"] == "allow" for e in decisions)
    assert all(e.source == "proxy" for e in events)
    # Un tool_call seguido de su decision, con el mismo call_id.
    for call_ev, dec_ev in zip(events[::2], events[1::2]):
        assert (call_ev.kind, dec_ev.kind) == ("tool_call", "decision")
        assert call_ev.call_id == dec_ev.call_id == call_ev.data["id"]


def test_orden_por_t(tmp_path):
    path = write_session(tmp_path, make_session("s1", 30), shuffle=True)
    events = replay([load_session(path)], allow_all)
    ts = [e.data["t"] for e in events if e.kind == "tool_call"]
    assert ts == list(range(1, 31))


def test_estado_nuevo_por_sesion(two_sessions):
    """make_decide se llama una vez por sesión: el contador no pasa de una sesión a otra."""
    calls = 0

    def factory():
        nonlocal calls
        calls += 1
        return counting()

    sessions = load_sessions(two_sessions)
    events = replay(sessions, factory)
    assert calls == 2
    for session in sessions:
        sid = session[0].session_id
        env_reads = [c for c in session if c.args.get("path") == ".env"]
        dec = [e for e in events if e.kind == "decision" and e.session_id == sid]
        first_block = next(i for i, e in enumerate(dec) if e.data["action"] == "block")
        # Bloquea justo en la tercera lectura de .env de ESTA sesión.
        assert dec[first_block].call_id == env_reads[2].id


def test_usa_output_grabado(two_sessions):
    replay(load_sessions(two_sessions), explodes_if_executed)


def test_mismo_resultado_dos_veces(two_sessions):
    sessions = load_sessions(two_sessions)
    a = replay(sessions, counting)
    b = replay(load_sessions(two_sessions), counting)
    assert comparable(a) == comparable(b)
    assert any(e.data["action"] == "block" for e in a if e.kind == "decision")


def test_mil_llamadas_por_minuto(tmp_path):
    folder = tmp_path / "sessions"
    for i in range(10):
        write_session(folder, make_session(f"s{i:02d}", 200, seed=i))
    t0 = time.perf_counter()
    events = replay(load_sessions(folder), allow_all)
    secs = time.perf_counter() - t0
    rate = 2000 / secs * 60
    assert len(events) == 4000
    assert rate >= 1000, f"{rate:.0f} llamadas/min"


def test_cli(two_sessions, tmp_path):
    out = tmp_path / "out" / "events.jsonl"
    r = subprocess.run([sys.executable, "-m", "eval.replay", "--sessions", str(two_sessions),
                        "--decide", "eval.replay.tests.helpers:allow_all", "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    events = read_events(out)
    assert len(events) == 200
    assert "200 eventos" in r.stdout


def test_toolcall_invalido_falla_con_ubicacion(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"id": "x", "t": 0}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="bad.jsonl:1"):
        load_session(bad)
