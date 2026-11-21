import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts import Decision, Event, ToolCall, load_hosts, read_events, write_event

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_examples_validate():
    tc = ToolCall.model_validate(_load("tool_call.json"))
    d = Decision.model_validate(_load("decision.json"))
    e = Event.model_validate(_load("event.json"))
    assert tc.is_sink and tc.label == "attack"
    assert d.leak["SECRET_1"].bits == 96.0
    assert not d.allowed
    assert e.data["secret_id"] == "SECRET_1"


def test_unknown_action_fails():
    data = _load("decision.json")
    data["action"] = "maybe"
    with pytest.raises(ValidationError):
        Decision.model_validate(data)


def test_unknown_label_fails_and_null_label_ok():
    data = _load("tool_call.json")
    data["label"] = None
    assert ToolCall.model_validate(data).label is None
    data["label"] = "suspicious"
    with pytest.raises(ValidationError):
        ToolCall.model_validate(data)


def test_extra_fields_rejected():
    data = _load("tool_call.json")
    data["unexpected"] = 1
    with pytest.raises(ValidationError):
        ToolCall.model_validate(data)


def test_leak_fraction_bounds():
    data = _load("decision.json")
    data["leak"]["SECRET_1"]["fraction"] = 1.5
    with pytest.raises(ValidationError):
        Decision.model_validate(data)


def test_kind_must_match_source():
    with pytest.raises(ValidationError):
        Event(ts=1.0, session_id="s", source="agent", kind="decision")
    Event(ts=1.0, session_id="s", source="attacker", kind="received", data={"bytes": "x"})


@pytest.mark.parametrize("allowed,action", [(True, "allow"), (True, "rotate+allow"), (False, "block"), (False, "rotate+block")])
def test_allowed_property(allowed, action):
    assert Decision(action=action).allowed is allowed


def test_write_read_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    tc = ToolCall.model_validate(_load("tool_call.json"))
    d = Decision.model_validate(_load("decision.json"))
    e1 = Event(ts=1.5, session_id="s1", source="proxy", kind="tool_call", call_id=tc.id, data=tc.model_dump())
    e2 = Event(ts=1.6, session_id="s1", source="proxy", kind="decision", call_id=tc.id, data=d.model_dump())
    e3 = Event(ts=1.7, session_id="s1", source="agent", kind="message", data={"text": "hola"})
    for e in (e1, e2, e3):
        write_event(e)

    proxy_events = read_events(tmp_path / "proxy.jsonl")
    assert proxy_events == [e1, e2]
    assert ToolCall.model_validate(proxy_events[0].data) == tc
    assert Decision.model_validate(proxy_events[1].data) == d
    assert read_events(tmp_path / "agent.jsonl") == [e3]


def test_hosts():
    hosts = load_hosts()
    assert set(hosts) == {"vault.test", "api.empresa.test", "attacker.test", "github.test", "web.test"}
    assert all(h.endswith(".test") for h in hosts)
    assert all(u.startswith("http://127.0.0.1:") for u in hosts.values())
