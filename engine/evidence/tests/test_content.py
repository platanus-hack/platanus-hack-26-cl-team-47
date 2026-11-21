import json

import pytest

from engine.bits import BitsEngine
from engine.evidence import content_features, shannon_entropy

SECRET = "b2dea8cc1d0308f0ad77be71bba6714a3bc837a6"  # sintético


def test_entropy_values():
    assert shannon_entropy("") == 0.0
    assert shannon_entropy("aaaaaaaa") == 0.0
    assert shannon_entropy("0123456789abcdef") == pytest.approx(4.0)


def test_arg_entropy_from_json_dumps():
    args = {"b": "zzz", "a": [1, 2]}
    f = content_features({"args": args}, {})
    assert f["arg_entropy"] == pytest.approx(shannon_entropy(json.dumps(args, sort_keys=True)))


def test_short_match_sums_candidate_bits():
    bits = {"S1": {"candidate_bits": 20.0}, "S2": {"candidate_bits": 4.0, "bits": 99}}
    assert content_features({"args": {}}, bits)["short_match"] == 24.0


def test_with_bits_engine_and_toolcall():
    contracts = pytest.importorskip("contracts")
    tc = contracts.ToolCall(id="a", t=1, tool="http_request", args={"body": f"x {SECRET[:5]} x"},
                            is_sink=True, session_id="s")
    bits = BitsEngine({"S": SECRET}).observe(tc)
    f = content_features(tc, bits)
    assert f["short_match"] == 20.0 and f["arg_entropy"] > 0
