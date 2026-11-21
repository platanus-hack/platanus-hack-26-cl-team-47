import json

from eval.final import build_report, t1_false_alarms, t2_detection, t5_theorem_slope, to_markdown
from eval.final.__main__ import main as cli_main


def _summary(n_benign=10, per=100, attacks=5):
    rows = [{"session_id": f"b{i}", "is_attack": False, "family": None, "n_calls": per, "n_exposed": per,
             "false_alarm_calls": 0, "n_rotations": 0, "prevented": None, "bits_true_at_action": 0.0}
            for i in range(n_benign)]
    rows += [{"session_id": f"a{i}", "is_attack": True, "family": "A1", "n_calls": 20, "n_exposed": 20,
              "false_alarm_calls": 0, "n_rotations": 1, "prevented": True, "bits_true_at_action": 32.0}
             for i in range(attacks)]
    return rows


def test_markdown_has_six_rows_and_marks_underpowered():
    s = _summary()
    rep = build_report({
        "T1": t1_false_alarms([r for r in s if not r["is_attack"]]),
        "T2": t2_detection([r for r in s if r["is_attack"]]),
        "T5": t5_theorem_slope([0.1, 0.5, 1.0, 1.4], [0, 40, 80, 120], n_boot=100),
    })
    md = to_markdown(rep)
    for name in ("T1", "T2", "T3", "T4", "T5", "T6"):
        assert f"| {name} |" in md
    assert md.count("datos insuficientes") >= 2      # T1 (1.000 < 3.000) y T2 (5 < 50)
    assert md.count("no corrida") == 3               # T3, T4 y T6 sin datos: la fila aparece igual
    assert set(rep["holm"]) == {"T1", "T2"}


def test_negative_result_is_reported():
    s = _summary()
    for r in s:
        if r["is_attack"]:
            r["prevented"] = False
    rep = build_report({"T2": t2_detection([r for r in s if r["is_attack"]])})
    md = to_markdown(rep)
    assert "| T2 |" in md and "| no |" in md


def test_cli_writes_report(tmp_path):
    ours = tmp_path / "ours.json"
    base = tmp_path / "base.json"
    s = _summary(attacks=6)
    ours.write_text(json.dumps({"sessions": s}), encoding="utf-8")
    b = [dict(r) for r in s]
    for r in b:
        if r["is_attack"]:
            r["prevented"] = False
    base.write_text(json.dumps({"sessions": b}), encoding="utf-8")
    out = tmp_path / "final"
    rep = cli_main(["--ours", str(ours), "--baseline", str(base), "--no-rotation", str(base), "--out", str(out)])
    assert (out / "report.json").is_file() and (out / "report.md").is_file()
    assert rep["tests"]["T3"]["b"] == 6
    data = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert set(data["tests"]) == {"T1", "T2", "T3", "T4", "T5", "T6"}
