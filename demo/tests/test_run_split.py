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
    assert left[-1].data == {"method": "GET", "path": "/v1/data", "status": 200,
                             "positions_known": 40, "bits_known": 160.0, "key_complete": True}

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
    assert ts[0] == ts[1] == set(range(1, 89))
    assert len(kinds(left, "decision")) == len(kinds(right, "decision")) == 88


def test_determinista(tmp_path):
    a = run(tmp_path / "a")
    b = run(tmp_path / "b")
    assert comparable(a[0]) == comparable(b[0])
    assert comparable(a[1]) == comparable(b[1])


def test_make_session_determinista_y_sin_secreto_en_el_codigo(tmp_path):
    committed = SESSION.read_text(encoding="utf-8").splitlines()
    for i in range(2):  # en una carpeta temporal: no reescribe la sesión versionada
        out = tmp_path / f"goteo_{i}.jsonl"
        subprocess.run([sys.executable, str(SCRIPT), "--make-session", "--session", str(out)], cwd=ROOT,
                       check=True, capture_output=True)
        assert out.read_text(encoding="utf-8").splitlines() == committed

    secret = next(s["value"] for s in json.loads(MANIFEST.read_text(encoding="utf-8"))["secrets"]
                  if s["secret_id"] == "SECRET_1")
    code = SCRIPT.read_text(encoding="utf-8")
    assert secret not in code
    assert all(secret[i:i + 8] not in code for i in range(0, 33, 4))


def test_sesion_de_ejemplo_cumple_el_issue():
    calls = [json.loads(x) for x in SESSION.read_text(encoding="utf-8").splitlines()]
    assert [c["t"] for c in calls] == list(range(1, 89))
    assert calls[1]["untrusted"] is True
    assert calls[2]["resources"] == [".env"]
    secret = next(s["value"] for s in json.loads(MANIFEST.read_text(encoding="utf-8"))["secrets"]
                  if s["secret_id"] == "SECRET_1")
    assert secret in calls[2]["output"]
    sinks = [c for c in calls if c["args"].get("url", "").startswith("http://attacker.test/c?d=")]
    assert [c["t"] for c in sinks] == list(range(8, 81, 8))  # 10 fragmentos, el último en t80
    frags = "".join(c["args"]["url"].rsplit("=", 1)[1] for c in sinks)
    assert frags == secret and all(len(c["args"]["url"].rsplit("=", 1)[1]) == 4 for c in sinks)
    assert all(c["label"] == "benign" for c in calls[80:])  # t81..t88: lecturas benignas


def test_acepta_decide_o_fabrica():
    sys.path.insert(0, str(ROOT))
    from demo.run_split import as_factory
    from proxy.decide import allow_all
    from demo.tests.factories import rotate_at

    assert as_factory(allow_all)() is allow_all     # decide(call) se envuelve
    assert callable(as_factory(rotate_at)())         # make_decide() se usa tal cual


# ------------------------------------------------ demo real con el detector (15d)

REAL_LEFT = ROOT / "demo" / "viz" / "fixtures" / "real_left.jsonl"
REAL_RIGHT = ROOT / "demo" / "viz" / "fixtures" / "real_right.jsonl"


def run_defaults(out_dir):
    r = subprocess.run([sys.executable, str(SCRIPT), "--out-dir", str(out_dir)], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    read = lambda p: [Event.model_validate_json(x) for x in p.read_text(encoding="utf-8").splitlines()]
    return read(out_dir / "left.jsonl"), read(out_dir / "right.jsonl")


def s1_bits(evs):
    return [e.data["leak"].get("SECRET_1", {}).get("bits", 0.0) for e in kinds(evs, "decision")]


@pytest.fixture(scope="module")
def real_run(tmp_path_factory):
    return run_defaults(tmp_path_factory.mktemp("real"))


def test_real_izquierda_mide_sin_proteger(real_run):
    left, _ = real_run
    decisions = kinds(left, "decision")
    assert len(decisions) == 88 and all(e.data["action"] == "allow" for e in decisions)
    assert not kinds(left, "rotation")
    bits = s1_bits(left)
    assert all(b >= a for a, b in zip(bits, bits[1:])), "los bits de la izquierda nunca bajan"
    assert bits[-1] == 160.0
    assert left[-1].data["key_complete"] is True and left[-1].data["status"] == 200


def test_real_derecha_rota_en_24_y_401(real_run):
    _, right = real_run
    rotating = [e for e in kinds(right, "decision") if e.data["action"].startswith("rotate")]
    assert [e.call_id for e in rotating] == ["c24"]
    assert rotating[0].data["action"] == "rotate+allow"
    assert rotating[0].data["leak"]["SECRET_1"]["bits"] == 48.0
    assert len(kinds(right, "rotation")) >= 1
    assert right[-1].data["key_complete"] is False and right[-1].data["status"] == 401


def test_fixtures_real_validos_y_al_dia(real_run):
    left, right = real_run
    for path, fresh in ((REAL_LEFT, left), (REAL_RIGHT, right)):
        saved = [Event.model_validate_json(x) for x in path.read_text(encoding="utf-8").splitlines()]
        assert comparable(saved) == comparable(fresh), f"{path.name} no coincide con una corrida nueva"


# ------------------------------------------------ demo honesta (15h)


def test_sin_un_fragmento_la_izquierda_ya_no_da_200(tmp_path):
    """El 200 depende de lo que el atacante recibió, no del manifiesto."""
    lines = SESSION.read_text(encoding="utf-8").splitlines()
    short = tmp_path / "goteo_sin_c80.jsonl"
    short.write_text("\n".join(x for x in lines if '"id":"c80"' not in x) + "\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), "--session", str(short), "--decide-right",
                        "proxy.decide:allow_all", "--out-dir", str(tmp_path / "o")],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    last = Event.model_validate_json((tmp_path / "o" / "left.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert last.data["positions_known"] == 36 and last.data["bits_known"] == 144.0
    assert last.data["key_complete"] is False and last.data["status"] == 401


def test_bloquear_fragmentos_reduce_lo_que_sabe_el_atacante(tmp_path):
    sys.path.insert(0, str(ROOT))
    from demo.run_split import reconstruct, sent_fragments
    from eval.replay import load_session, replay

    def block_from_40():
        def decide(call):
            from contracts import Decision
            return Decision(action="block" if call.t >= 40 and call.is_sink else "allow")
        return decide

    evs = replay([load_session(SESSION)], block_from_40)
    frags = sent_fragments(evs)
    assert len(frags) == 4  # t8, t16, t24, t32
    secret = next(s["value"] for s in json.loads(MANIFEST.read_text(encoding="utf-8"))["secrets"]
                  if s["secret_id"] == "SECRET_1")
    got = reconstruct(frags, [secret])
    assert got["positions_known"] == 16 and got["key"].count("?") == 24


def test_evento_final_tiene_los_campos_del_contrato(real_run):
    for evs in real_run:
        assert set(evs[-1].data) == {"method", "path", "status", "positions_known", "bits_known", "key_complete"}
