import json

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from engine.evidence import FeatureModel


def test_issue_example():
    m = FeatureModel().fit([{"x": 0.0}] * 100, [{"x": 1.0}] * 100)
    hi, lo = m.llr({"x": 1.0}), m.llr({"x": 0.0})
    assert hi > 0 > lo
    assert -3 <= lo and hi <= 3


def _gauss_model(seed=0):
    rng = np.random.default_rng(seed)
    benign = [{"x": float(v)} for v in rng.normal(0, 1, 2000)]
    attack = [{"x": float(v)} for v in rng.normal(2, 1, 2000)]
    return FeatureModel().fit(benign, attack), rng


def test_separation_two_gaussians():
    m, rng = _gauss_model()
    lb = [m.llr({"x": float(v)}) for v in rng.normal(0, 1, 1000)]
    la = [m.llr({"x": float(v)}) for v in rng.normal(2, 1, 1000)]
    assert np.mean(lb) < 0 < np.mean(la)


_MODEL, _ = _gauss_model(1)


@settings(max_examples=300)
@given(st.dictionaries(st.sampled_from(["x", "y", "z"]), st.floats(allow_nan=True, allow_infinity=True)))
def test_clip_in_range(feats):
    assert -3.0 <= _MODEL.llr(feats) <= 3.0


@given(st.integers(1, 6), st.floats(0.5, 10))
def test_clip_many_features(n, B):
    benign = [{f"f{i}": 0.0 for i in range(n)}] * 50
    attack = [{f"f{i}": 1.0 for i in range(n)}] * 50
    m = FeatureModel(B=B).fit(benign, attack)
    assert -B <= m.llr({f"f{i}": 1.0 for i in range(n)}) <= B
    assert -B <= m.llr({f"f{i}": 0.0 for i in range(n)}) <= B


def test_missing_feature_contributes_zero():
    m, _ = _gauss_model()
    assert m.llr({}) == 0.0
    assert m.llr({"desconocida": 5.0}) == 0.0
    assert m.llr({"x": 1.7, "otra": 1.0}) == m.llr({"x": 1.7})


def test_out_of_range_goes_to_extreme_bin():
    m, _ = _gauss_model()
    assert m.llr({"x": 1e9}) == m.llr({"x": 100.0})
    assert m.llr({"x": -1e9}) == m.llr({"x": -100.0})


def test_roundtrip():
    m, rng = _gauss_model()
    m2 = FeatureModel.from_dict(json.loads(json.dumps(m.to_dict())))
    assert m2.to_dict() == m.to_dict()
    for v in rng.normal(1, 2, 200):
        assert m2.llr({"x": float(v)}) == m.llr({"x": float(v)})
