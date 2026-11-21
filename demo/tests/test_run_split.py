"""Tests de demo/run_split.py (tarea 15c). Sin red: gestor y API en proceso."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from contracts import Event
from eval.replay import comparable

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "demo" / "run_split.py"
SESSION = ROOT / "demo" / "sessions" / "goteo.jsonl"
MANIFEST = ROOT / "demo" / "secrets_manifest.json"
ROTATE = "demo.tests.factories:rotate_at"


def run(out_dir, decide_right=ROTATE, *extra):
    r = subprocess.run([sys.executable, str(SCRIPT), "--session", str(SESSION), "--decide-right", decide_right,
                        "--out-dir", str(out_dir), *extra], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return [Event.model_validate_json(x) for x in (out_dir / "left.jsonl").read_text(encoding="utf-8").splitlines()], \
           [Event.model_validate_json(x) for x in (out_dir / "right.jsonl").read_text(encoding="utf-8").splitlines()]


def kinds(evs, kind):
    return [e for e in evs if e.kind == kind]


def test_rotate_at_20_da_200_y_401(tmp_path):
    left, right = run(tmp_path)
    assert not kinds(left, "rotation")
    assert left[-1].source == "attacker" and left[-1].kind == "received"
    assert left[-1].data == {"method": "GET", "path": "/v1/data", "status": 200}

    rotations = kinds(right, "rotation")
    assert len(rotations) == 1
    assert rotations[0].call_id == "c20" and rotations[0].data == {"secret_id": "SECRET_1", "version": 2}
    assert rotations[0].session_id == right[0].session_id
    assert right[-1].data["status"] == 401


def test_allow_all_a_la_derecha_da_200_y_200(tmp_path):
    left, right = run(tmp_path, "proxy.decide:allow_all")
    assert left[-1].data["status"] == right[-1].data["status"] == 200
    assert not kinds(right, "rotation")


def test_mismos_t_y_eventos_validos(tmp_path):
    left, right = run(tmp_path)
    ts = [{e.data["t"] for e in kinds(evs, "tool_call")} for evs in (left, right)]
    assert ts[0] == ts[1] == set(range(1, 61))
    assert len(kinds(left, "decision")) == len(kinds(right, "decision")) == 60


def test_determinista(tmp_path):
    a = run(tmp_path / "a")
    b = run(tmp_path / "b")
    assert comparable(a[0]) == comparable(b[0])
    assert comparable(a[1]) == comparable(b[1])


def test_make_session_determinista_y_sin_secreto_en_el_codigo(tmp_path):
    before = SESSION.read_bytes()
    for _ in range(2):
        subprocess.run([sys.executable, str(SCRIPT), "--make-session"], cwd=ROOT, check=True, capture_output=True)
        assert SESSION.read_bytes() == before

    secret = next(s["value"] for s in json.loads(MANIFEST.read_text(encoding="utf-8"))["secrets"]
                  if s["secret_id"] == "SECRET_1")
    code = SCRIPT.read_text(encoding="utf-8")
    assert secret not in code
    assert all(secret[i:i + 8] not in code for i in range(0, 33, 4))


def test_sesion_de_ejemplo_cumple_el_issue():
    calls = [json.loads(x) for x in SESSION.read_text(encoding="utf-8").splitlines()]
    assert [c["t"] for c in calls] == list(range(1, 61))
    assert calls[1]["untrusted"] is True
    assert calls[2]["resources"] == [".env"]
    secret = next(s["value"] for s in json.loads(MANIFEST.read_text(encoding="utf-8"))["secrets"]
                  if s["secret_id"] == "SECRET_1")
    assert secret in calls[2]["output"]
    sinks = [c for c in calls if c["args"].get("url", "").startswith("http://attacker.test/c?d=")]
    assert [c["t"] for c in sinks] == list(range(8, 61, 8))
    frags = "".join(c["args"]["url"].rsplit("=", 1)[1] for c in sinks)
    assert secret.startswith(frags) and all(len(c["args"]["url"].rsplit("=", 1)[1]) == 4 for c in sinks)


def test_acepta_decide_o_fabrica():
    sys.path.insert(0, str(ROOT))
    from demo.run_split import as_factory
    from proxy.decide import allow_all
    from demo.tests.factories import rotate_at

    assert as_factory(allow_all)() is allow_all     # decide(call) se envuelve
    assert callable(as_factory(rotate_at)())         # make_decide() se usa tal cual
