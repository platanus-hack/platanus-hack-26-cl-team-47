"""Regla simple «leyó un secreto y sale hacia un destino no confiable» (#167)."""

from contracts import ToolCall
from eval.baselines.taint_rule import make_decide
from eval.replay import replay

SECRET = "73a71492ba32ec39bde7f7a93248b56fa2439a16"
SECRETS = {"SECRET_1": SECRET, "SECRET_2": "b" * 40}


def call(t, tool="http_request", *, sink=True, untrusted=True, output="ok"):
    return ToolCall(id=f"s-{t}", t=t, tool=tool, args={}, resources=[], is_sink=sink, untrusted=untrusted,
                    session_id="s", output=output)


def test_lee_rota_en_el_primer_sumidero_no_confiable_y_el_siguiente_ya_no():
    d = make_decide(SECRETS)
    assert d(call(1, "read_file", sink=False, untrusted=False, output=f"KEY={SECRET}")).action == "allow"
    first = d(call(2))
    assert first.action == "rotate+allow" and d.__self__.last_rotations == ["SECRET_1"]
    assert d(call(3)).action == "allow" and d.__self__.last_rotations == []


def test_sin_lectura_o_sin_salida_no_confiable_no_rota():
    d = make_decide(SECRETS)
    assert d(call(1)).action == "allow"                                   # no leyó nada
    d(call(2, "read_file", sink=False, untrusted=False, output=SECRET))
    assert d(call(3, untrusted=False)).action == "allow"                  # sumidero confiable
    assert d(call(4, sink=False, untrusted=True)).action == "allow"       # no confiable pero no sale nada
    assert d(call(5)).action == "rotate+allow"


def test_un_fragmento_no_cuenta_como_lectura_y_nunca_bloquea():
    d = make_decide(SECRETS)
    d(call(1, "read_file", sink=False, untrusted=False, output=SECRET[:20]))
    assert d(call(2)).action == "allow"
    acts = [d(call(t, output=SECRET)).action for t in range(3, 8)]
    assert all(not a.endswith("block") for a in acts)


def test_el_arnes_registra_sus_rotaciones():
    s = [call(1, "read_file", sink=False, untrusted=False, output=f"KEY={SECRET}"), call(2), call(3)]
    evs = replay([s], lambda: make_decide(SECRETS), emit_rotations=True)
    rot = [e for e in evs if e.kind == "rotation"]
    assert [(e.call_id, e.data["secret_id"]) for e in rot] == [("s-2", "SECRET_1")]
