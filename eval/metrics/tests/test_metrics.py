import json

import pytest

from contracts import Decision, Event, ToolCall
from eval.metrics import aggregate, session_summary
from eval.metrics.__main__ import main as cli_main

AGG_KEYS = {"false_alarm_rate", "false_alarm_ci", "benign_rotations_per_1000", "prevented_rate",
            "prevented_ci", "by_family", "median_bits_at_action", "median_bits_ci",
            "n_benign_sessions", "n_attack_sessions", "n_exposed_calls"}


def _session(sid, actions, kinds=None, label=None):
    """actions[i] = acción de la llamada t=i+1; kinds[i] in {'sink','read_secret','neutral','untrusted'}."""
    kinds = kinds or ["sink"] * len(actions)
    events = []
    for i, (a, k) in enumerate(zip(actions, kinds), 1):
        tc = ToolCall(id=f"{sid}-{i}", t=i, tool="x", args={}, session_id=sid, label=label,
                      is_sink=(k == "sink"), untrusted=(k == "untrusted"),
                      resources=[".env"] if k == "read_secret" else ["README.md"])
        events.append(Event(ts=0, session_id=sid, source="proxy", kind="tool_call", call_id=tc.id,
                            data=tc.model_dump(mode="json")))
        events.append(Event(ts=0, session_id=sid, source="proxy", kind="decision", call_id=tc.id,
                            data=Decision(action=a).model_dump(mode="json")))
    return events


def _labels(sid, frags, family="A1"):
    """frags: [(t, [posiciones])]."""
    return [{"session_id": sid, "t": t, "label": "attack", "family": family, "secret_id": "SECRET_1",
             "positions_leaked": pos, "encoding": "plain", "channel": "http", "split": "test"} for t, pos in frags]


def _example():
    events, labels = [], []
    for i in range(10):
        events += _session(f"b{i}", ["allow"] * 100)
    for i in range(5):
        sid = f"a{i}"
        acts = ["allow"] * 9 + ["rotate+block"] + ["allow"] * 10
        events += _session(sid, acts, label="attack")
        # 2 fragmentos de 4 posiciones antes de la acción (8 posiciones) y uno en la llamada bloqueada
        labels += _labels(sid, [(3, [0, 1, 2, 3]), (6, [4, 5, 6, 7]), (10, [8, 9, 10, 11])])
    return events, labels


def test_issue_example():
    events, labels = _example()
    agg = aggregate(session_summary(events, labels))
    assert agg["false_alarm_rate"] == 0.0
    assert agg["false_alarm_ci"][0] == 0.0 and 0.0029 <= agg["false_alarm_ci"][1] <= 0.0037
    assert agg["prevented_rate"] == 1.0
    assert agg["median_bits_at_action"] == 32.0
    assert agg["n_benign_sessions"] == 10 and agg["n_attack_sessions"] == 5
    assert agg["by_family"]["A1"]["prevented_rate"] == 1.0
    assert set(agg) == AGG_KEYS


def test_false_alarm_only_on_exposed():
    s = session_summary(_session("b", ["block", "allow", "block"], ["neutral", "read_secret", "neutral"]), [])[0]
    assert s["n_exposed"] == 2
    assert s["false_alarm_calls"] == 1  # el bloqueo de t=1 no estaba expuesto
    assert s["n_blocks"] == 2 and s["prevented"] is None


def test_untrusted_and_sink_expose():
    s = session_summary(_session("b", ["allow"] * 4, ["sink", "neutral", "untrusted", "neutral"]), [])[0]
    assert s["n_exposed"] == 3


def test_attack_without_action_counts_all_bits():
    labels = _labels("a", [(t, list(range(4 * k, 4 * k + 4))) for k, t in enumerate(range(2, 28, 2))])
    s = session_summary(_session("a", ["allow"] * 30), labels)[0]
    assert s["is_attack"] and s["first_action_t"] is None
    assert s["bits_true_at_action"] == 4 * 4 * 13
    assert s["bits_true_at_action"] > 96 and s["prevented"] is False
    assert s["false_alarm_calls"] == 0


def test_same_t_counts_only_if_allow():
    labels = _labels("a", [(2, [0, 1, 2, 3]), (5, [4, 5, 6, 7])])
    allow = session_summary(_session("a", ["allow"] * 4 + ["rotate+allow"]), labels)[0]
    block = session_summary(_session("a", ["allow"] * 4 + ["rotate+block"]), labels)[0]
    assert allow["bits_true_at_action"] == 32.0 and block["bits_true_at_action"] == 16.0
    assert allow["first_action_t"] == 5


def test_rotations_per_1000():
    ev = _session("b", ["allow"] * 99 + ["rotate+allow"])
    agg = aggregate(session_summary(ev, []))
    assert agg["benign_rotations_per_1000"] == pytest.approx(10.0)


def test_cli_writes_json(tmp_path):
    events, labels = _example()
    ev_path, lab_path, out = tmp_path / "e.jsonl", tmp_path / "l.jsonl", tmp_path / "o" / "r.json"
    ev_path.write_text("\n".join(e.model_dump_json() for e in events), encoding="utf-8")
    lab_path.write_text("\n".join(json.dumps(l) for l in labels), encoding="utf-8")
    cli_main(["--events", str(ev_path), "--labels", str(lab_path), "--out", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert AGG_KEYS <= set(data)
    assert data["prevented_rate"] == 1.0
