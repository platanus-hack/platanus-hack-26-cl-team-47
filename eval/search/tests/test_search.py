"""Búsqueda de umbrales con datos provisionales (no se versiona ningún resultado)."""

import json
import shutil
from pathlib import Path

import pytest

from engine.detector import Params
from eval.fit import fit_model
from eval.fit.tests.test_fit import _direct_session, _drip_session, _write
from eval.replay.core import load_sessions
from eval.search import choose, combos, evaluate, freeze, pareto, search
from eval.search.__main__ import main as cli_main

BENIGN_DIR = Path("data/benign/sessions")


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    root = tmp_path_factory.mktemp("search")
    benign = root / "benign"
    benign.mkdir()
    for p in sorted(BENIGN_DIR.glob("*.jsonl"))[::20][:6]:
        shutil.copy(p, benign / p.name)
    attack = [_drip_session(i, start=4 * i, every=6 + i) for i in range(2)] + [_direct_session(i) for i in range(2)]
    _write(attack, root / "attack")
    model, _ = fit_model(str(benign), str(root / "attack"))
    model_path = root / "model.json"
    model_path.write_text(json.dumps(model.to_dict()), encoding="utf-8")
    sessions = load_sessions(benign) + load_sessions(root / "attack")
    return root, benign, root / "attack", model, model_path, sessions


GRID4 = {"b": [6, 11], "b_rot": [3], "lambda_rot": [0.2, 0.4], "T": [200]}


def _row(fa, rot, med, prev=1.0, **kw):
    return {"false_alarm_rate": fa, "benign_rotations_per_1000": rot, "median_max_bits_true": med,
            "prevented_rate": prev, **kw}


def test_combos_full_grid_is_750():
    from eval.search import GRID
    assert len(combos(GRID)) == 750


def test_pareto_hand_built():
    a = _row(0.0, 1.0, 32, id="a")
    b = _row(0.0, 2.0, 32, id="b")      # dominada por a
    c = _row(0.001, 0.5, 16, id="c")
    d = _row(0.002, 0.5, 16, id="d")    # dominada por c
    e = _row(0.0, 0.0, 64, id="e")
    f = _row(0.0, 1.0, 32, id="f")      # igual que a: ninguna domina a la otra
    front = {r["id"] for r in pareto([a, b, c, d, e, f])}
    assert front == {"a", "c", "e", "f"}


def test_choose():
    assert choose([_row(0.01, 1, 10), _row(0.0, 9, 10)]) is None
    rows = [_row(0.0, 1, 40, id="x"), _row(0.0005, 4, 16, 0.8, id="y"), _row(0.0, 2, 16, 0.9, id="z"),
            _row(0.5, 1, 8, id="muchas_falsas_alarmas"), _row(0.0, 6, 4, id="muchas_rotaciones")]
    assert choose(rows)["id"] == "z"


def test_evaluate_one_combo(data):
    _, _, _, model, _, sessions = data
    row = evaluate(Params(), model, sessions, [], None)
    assert {"b", "b_rot", "lambda_rot", "T", "false_alarm_rate", "benign_rotations_per_1000",
            "prevented_rate", "median_max_bits_true"} <= set(row)
    assert row["prevented_rate"] is not None


def test_search_4_combos_same_with_1_and_2_workers(data):
    _, _, _, model, _, sessions = data
    r1 = search(model, sessions, [], None, grid=GRID4, workers=1)
    r2 = search(model, sessions, [], None, grid=GRID4, workers=2)
    assert len(r1) == 4 and r1 == r2


def test_freeze_hashes(data, tmp_path):
    _, benign, attack, _, model_path, _ = data
    p = {"b": 9.2, "b_rot": 4.0, "lambda_rot": 0.3, "T": 200}
    f1 = freeze(p, str(model_path), [str(benign), str(attack)], str(tmp_path / "f1.json"), date="2026-11-21")
    f2 = freeze(p, str(model_path), [str(benign), str(attack)], str(tmp_path / "f2.json"), date="2026-11-21")
    assert f1["model_sha256"] == f2["model_sha256"] and f1["data_sha256"] == f2["data_sha256"]
    assert f1["hash"] == f2["hash"]
    f3 = freeze({**p, "b": 11}, str(model_path), [str(benign), str(attack)], str(tmp_path / "f3.json"),
                date="2026-11-21")
    assert f3["hash"] != f1["hash"] and f3["model_sha256"] == f1["model_sha256"]
    assert json.loads((tmp_path / "f1.json").read_text(encoding="utf-8"))["hash"] == f1["hash"]


def test_cli_limit_combos(data, tmp_path):
    _, benign, attack, _, model_path, _ = data
    out = tmp_path / "search"
    res = cli_main(["--benign", str(benign), "--attack", str(attack), "--model", str(model_path),
                    "--out", str(out), "--workers", "1", "--limit-combos", "3"])
    assert len(json.loads((out / "rows.json").read_text(encoding="utf-8"))) == 3
    assert (out / "pareto.json").is_file()
    assert (out / "frozen.json").is_file() == (res["chosen"] is not None)
