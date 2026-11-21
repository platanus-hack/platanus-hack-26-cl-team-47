"""#110: varias carpetas de ataque, sesiones sin etiquetas = benignas, split de labels.jsonl."""

import json
import shutil
from pathlib import Path

import pytest

from eval.fit import fit_model
from eval.fit.tests.test_fit import _direct_session, _drip_session, _write
from eval.replay.core import load_session
from eval.search.__main__ import assign_families, main as cli_main, split_from_id

BENIGN_DIR = Path("data/benign/sessions")


def _rename(session, sid):
    return [c.model_copy(update={"id": f"{sid}-{c.t}", "session_id": sid}) for c in session]


def _labels(sessions, family, split):
    return [{"session_id": c.session_id, "t": c.t, "family": family, "split": split, "label": "attack",
             "secret_id": "SECRET_1"} for s in sessions for c in s if c.label == "attack"]


def _write_jsonl(rows, path: Path):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_split_from_id():
    assert split_from_id("val-1-0080") == "val"
    assert split_from_id("train-0-0000") == "train"
    assert split_from_id("test-2-0001") == "test"
    assert split_from_id("benign-0003") is None
    assert split_from_id("val") is None


def test_unlabeled_attack_session_is_benign_in_its_part():
    benign = [_rename(_direct_session(0), "benign-0000")]
    atk = _rename(_direct_session(1), "val-1-0000")
    hard = _rename(_direct_session(2), "val-1-0080")      # B1/B2: sin líneas en labels
    other = _rename(_direct_session(3), "sim-0001")       # sin etiquetas y sin prefijo de parte
    labels = _labels([atk], "A1", "val")
    families, given = assign_families(benign, [atk, hard, other], labels)
    assert families["val-1-0080"] is None and given["val-1-0080"] == "val"
    assert families["sim-0001"] is None and "sim-0001" not in given
    assert families["val-1-0000"] == "A1" and given["val-1-0000"] == "val"


def test_without_labels_keeps_old_behaviour():
    atk = _rename(_direct_session(1), "prov-directa-1")
    families, given = assign_families([], [atk], [])
    assert families == {"prov-directa-1": "prov-directa"} and given == {}


@pytest.fixture(scope="module")
def two_dirs(tmp_path_factory):
    root = tmp_path_factory.mktemp("cli_split")
    benign = root / "benign"
    benign.mkdir()
    for p in sorted(BENIGN_DIR.glob("*.jsonl"))[::20][:4]:
        shutil.copy(p, benign / p.name)
    train = [_rename(_drip_session(i, start=4 * i, every=6 + i), f"train-0-{i:04d}") for i in range(2)]
    val = [_rename(_direct_session(i), f"val-1-{i:04d}") for i in range(3)]
    hard = _rename(load_session(sorted(BENIGN_DIR.glob("*.jsonl"))[1]), "val-1-0080")
    _write(train, root / "train" / "sessions")
    _write(val + [hard], root / "val" / "sessions")
    _write_jsonl(_labels(train, "A3", "train"), root / "train" / "labels.jsonl")
    _write_jsonl(_labels(val, "A1", "val"), root / "val" / "labels.jsonl")
    model, _ = fit_model(str(benign), str(root / "train" / "sessions"), str(root / "train" / "labels.jsonl"))
    (root / "model.json").write_text(json.dumps(model.to_dict()), encoding="utf-8")
    return root, benign


def test_cli_two_attack_dirs_concatenated(two_dirs, tmp_path, capsys):
    root, benign = two_dirs
    res = cli_main(["--benign", str(benign),
                    "--attack", str(root / "train" / "sessions"), str(root / "val" / "sessions"),
                    "--labels", str(root / "train" / "labels.jsonl"), str(root / "val" / "labels.jsonl"),
                    "--model", str(root / "model.json"), "--out", str(tmp_path / "search"),
                    "--workers", "1", "--limit-combos", "1"])
    fams, parts = res["families"], res["parts"]
    assert {"train-0-0000", "train-0-0001", "val-1-0000", "val-1-0001", "val-1-0002", "val-1-0080"} <= set(fams)
    assert all(parts[f"train-0-{i:04d}"] == "train" for i in range(2))
    assert all(parts[f"val-1-{i:04d}"] == "val" and fams[f"val-1-{i:04d}"] == "A1" for i in range(3))
    assert fams["val-1-0080"] is None and parts["val-1-0080"] == "val"
    assert "3 de ataque" in capsys.readouterr().out
    assert res["rows"][0]["prevented_rate"] is not None
