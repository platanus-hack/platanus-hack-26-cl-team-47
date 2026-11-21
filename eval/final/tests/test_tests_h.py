import numpy
import pytest

from eval.final import holm, t1_false_alarms, t2_detection, t3_vs_baseline, t4_rotation, t5_theorem_slope, t6_gff


def _benign(n_exposed, fa=0, n_sessions=10):
    per = n_exposed // n_sessions
    rows = [{"session_id": f"b{i}", "is_attack": False, "n_exposed": per, "n_calls": per,
             "false_alarm_calls": 0, "n_rotations": 0} for i in range(n_sessions)]
    rows[0]["false_alarm_calls"] = fa
    return rows


def _attacks(prevented: list[bool], bits=None, prefix="a"):
    bits = bits or [32.0] * len(prevented)
    return [{"session_id": f"{prefix}{i}", "is_attack": True, "prevented": p, "bits_true_at_action": b}
            for i, (p, b) in enumerate(zip(prevented, bits))]


def test_t1_3000_fails_5000_passes():
    r = t1_false_alarms(_benign(3000))
    assert r["k"] == 0 and r["n"] == 3000 and r["rate"] == 0.0
    assert r["ci"][1] == pytest.approx(0.00123, abs=1e-4)   # cerca de 3/n
    assert r["pass"] is False and "underpowered" not in r
    r5 = t1_false_alarms(_benign(5000))
    assert r5["pass"] is True and r5["p_value"] < 0.05
    assert t1_false_alarms(_benign(1000))["underpowered"] is True


def test_t2_50_of_50():
    r = t2_detection(_attacks([True] * 50))
    assert r["ci"][0] == pytest.approx(0.94, abs=0.015) and r["pass"] is True
    assert "underpowered" not in r
    assert t2_detection(_attacks([True] * 10))["underpowered"] is True


def test_t3_mcnemar():
    ours = _attacks([True] * 10 + [False] * 5)
    base = _attacks([False] * 10 + [False] * 5)
    r = t3_vs_baseline(ours, base)
    assert r["b"] == 10 and r["c"] == 0
    assert r["p_value"] == pytest.approx(2 * 0.5 ** 10)
    assert r["pass"] is True
    with pytest.raises(ValueError):
        t3_vs_baseline(ours, base[:-1])


def test_t4_identical_groups():
    g = _attacks([True, False, True, True], bits=[16, 120, 32, 8])
    r = t4_rotation(g, g)
    assert r["fisher_p"] == 1.0 and r["p_value"] == 1.0
    assert r["median_bits_with"] == r["median_bits_without"]


def test_t4_rotation_helps():
    w = _attacks([True] * 20, bits=[32.0] * 20)
    wo = _attacks([False] * 20, bits=[140.0] * 20, prefix="n")
    r = t4_rotation(w, wo)
    assert r["fisher_p"] < 1e-6 and r["mannwhitney_p"] < 1e-6


def test_t5_slope():
    rng = numpy.random.default_rng(0)
    bits = rng.uniform(0, 160, 300)
    llr = 0.5 * bits + rng.normal(0, 5, 300)
    r = t5_theorem_slope(llr.tolist(), bits.tolist(), n_boot=500)
    assert r["ci"][0] <= 0.5 <= r["ci"][1]
    noise = t5_theorem_slope(rng.normal(0, 1, 300).tolist(), bits.tolist(), n_boot=500)
    assert noise["ci"][0] <= 0.0 <= noise["ci"][1]
    assert "pass" not in r and "p_value" not in r


def test_t6_paired_diff():
    rng = numpy.random.default_rng(1)
    base = rng.uniform(0.6, 0.8, 30)
    r = t6_gff((base + 0.05).tolist(), base.tolist(), n_boot=500)
    assert r["diff"] == pytest.approx(0.05)
    assert "pass" not in r and "p_value" not in r


def test_holm():
    h = holm({"T1": 0.01, "T2": 0.04, "T3": 0.03, "T4": 0.5})
    assert {k for k, v in h.items() if v["reject"]} == {"T1"}
    assert h["T1"]["p_adjusted"] == pytest.approx(0.04)
    assert h["T3"]["p_adjusted"] == pytest.approx(0.09)
    assert h["T2"]["p_adjusted"] == pytest.approx(0.09)   # monótono
    assert h["T4"]["p_adjusted"] == pytest.approx(0.5)
