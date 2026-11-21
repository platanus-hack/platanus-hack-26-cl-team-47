import pytest

from contracts import ToolCall
from engine.detector import Params, extract

KEYS = {"m", "m_sd", "jump", "U", "n_S", "is_sink", "prev_source_now_sink", "arg_entropy", "short_match"}


def tc(**kw):
    base = dict(id="c1", t=1, tool="http_request", args={"url": "http://x.test/"}, session_id="s")
    base.update(kw)
    return ToolCall(**base)


def test_params_defaults_frozen():
    p = Params()
    assert (p.b, p.b_rot, p.lambda_rot, p.alpha, p.T, p.beta_bits) == (9.2, 4.0, 0.3, 0.2, 200, 64.0)
    with pytest.raises(Exception):
        p.b = 1.0


def test_extract_all_floats():
    f = extract(tc(is_sink=True), {"m": 0.9, "m_sd": 0.1, "jump": 2.0},
                {"kind": "sink", "U": True, "S": ["SECRET_1", "SECRET_2"], "path": []},
                {"SECRET_1": {"bits": 0, "candidate_bits": 8.0}}, "source")
    assert set(f) == KEYS
    assert all(isinstance(v, float) for v in f.values())
    assert f["m"] == 0.9 and f["jump"] == 2.0 and f["U"] == 1.0 and f["n_S"] == 2.0
    assert f["is_sink"] == 1.0 and f["prev_source_now_sink"] == 1.0 and f["short_match"] == 8.0


def test_extract_neutral():
    f = extract(tc(), {"m": 0.0, "m_sd": 0.0, "jump": 0.0},
                {"kind": "neutral", "U": False, "S": [], "path": []}, {}, None)
    assert f["U"] == 0.0 and f["n_S"] == 0.0 and f["is_sink"] == 0.0
    assert f["prev_source_now_sink"] == 0.0 and f["short_match"] == 0.0


def test_prev_source_requires_sink_now():
    f = extract(tc(), {}, {"kind": "neutral", "S": []}, {}, "source")
    assert f["prev_source_now_sink"] == 0.0
