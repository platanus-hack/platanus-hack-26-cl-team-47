"""Tests obligatorios del generador de ataques de entrenamiento (issue #9, sección 7)."""

from __future__ import annotations

import base64
import codecs
import collections
import json
from pathlib import Path

import pytest

from contracts.models import ToolCall
from redteam import generate

ROOT = Path(__file__).resolve().parent.parent.parent
VERSIONED = ROOT / "redteam" / "train"

A4_ENCODINGS = ["base64", "hex", "url", "rot13", "reversed", "separated"]
CHANNELS = ["query_param", "url_path", "header", "body", "github_comment", "github_issue"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def gen(tmp: Path, n: int = 80, seed: int = 0, split: str = "train") -> Path:
    out = tmp / f"{split}-{seed}-{n}"
    generate.generate(split, n, seed, out)
    return out


def read_sessions(out: Path) -> dict[str, list[dict]]:
    sessions = {}
    for f in sorted((out / "sessions").glob("*.jsonl")):
        sessions[f.stem] = [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
    return sessions


def read_labels(out: Path) -> list[dict]:
    return [json.loads(line) for line in (out / "labels.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def read_secrets(out: Path) -> dict[str, str]:
    rows = [json.loads(line) for line in (out / "secrets.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    return {r["session_id"]: r["value"] for r in rows}


def decode(x: str, enc: str) -> str:
    if enc == "none":
        return x
    if enc == "base64":
        return base64.b64decode(x).decode()
    if enc == "hex":
        return bytes.fromhex(x).decode()
    if enc == "url":
        return "".join(chr(int(x[i + 1:i + 3], 16)) for i in range(0, len(x), 3))
    if enc == "rot13":
        return codecs.decode(x, "rot13")
    if enc == "reversed":
        return x[::-1]
    if enc == "separated":
        return "".join(x.split("-"))
    raise ValueError(enc)


def encode(frag: str, enc: str) -> str:
    return {
        "none": frag,
        "base64": base64.b64encode(frag.encode()).decode(),
        "hex": frag.encode().hex(),
        "url": "".join(f"%{ord(c):02X}" for c in frag),
        "rot13": codecs.encode(frag, "rot13"),
        "reversed": frag[::-1],
        "separated": "-".join(frag),
    }[enc]


# --------------------------------------------------------------------------- #
# 1. Reparto y conteo de sesiones de ataque/benignas
# --------------------------------------------------------------------------- #
def test_reparto_y_conteo(tmp_path):
    out = gen(tmp_path)
    sessions = read_sessions(out)
    atk = [s for s, calls in sessions.items() if any(c["label"] == "attack" for c in calls)]
    ben = [s for s, calls in sessions.items() if all(c["label"] != "attack" for c in calls)]
    assert len(atk) == 80
    assert len(ben) == 20

    labels = read_labels(out)
    per_family = collections.defaultdict(set)
    for L in labels:
        per_family[L["family"]].add(L["session_id"])
    counts = {fam: len(sids) for fam, sids in per_family.items()}
    assert counts == {"A1": 10, "A2": 15, "A3": 20, "A4": 25, "A5′": 10}


# --------------------------------------------------------------------------- #
# 2. Determinismo byte a byte
# --------------------------------------------------------------------------- #
def _all_files(out: Path) -> dict[str, bytes]:
    return {p.relative_to(out).as_posix(): p.read_bytes()
            for p in sorted(out.rglob("*")) if p.is_file()}


def test_determinismo(tmp_path):
    a = gen(tmp_path / "a", seed=0)
    b = gen(tmp_path / "b", seed=0)
    assert _all_files(a) == _all_files(b)

    c = gen(tmp_path / "c", seed=1)
    assert _all_files(a) != _all_files(c)


# --------------------------------------------------------------------------- #
# 3. Contrato ToolCall, t 1..N sin saltos, id único
# --------------------------------------------------------------------------- #
def test_contrato_y_numeracion(tmp_path):
    out = gen(tmp_path)
    for sid, calls in read_sessions(out).items():
        for c in calls:
            ToolCall.model_validate(c)
        ts = [c["t"] for c in calls]
        assert ts == list(range(1, len(calls) + 1)), sid
        ids = [c["id"] for c in calls]
        assert len(set(ids)) == len(ids), sid


# --------------------------------------------------------------------------- #
# 4. Decodificación de fragmentos (encoding != custom)
# --------------------------------------------------------------------------- #
def test_decodificacion(tmp_path):
    out = gen(tmp_path)
    sessions = read_sessions(out)
    secrets = read_secrets(out)
    checked = 0
    for L in read_labels(out):
        if L["encoding"] == "custom":
            continue
        value = secrets[L["session_id"]]
        call = next(c for c in sessions[L["session_id"]] if c["t"] == L["t"])
        serial = json.dumps(call["args"], ensure_ascii=False)
        pos = L["positions_leaked"]
        expected = value[pos[0]: pos[-1] + 1]
        x = encode(expected, L["encoding"])
        assert x in serial
        assert decode(x, L["encoding"]) == expected
        checked += 1
    assert checked > 0


# --------------------------------------------------------------------------- #
# 5. Lectura del secreto y vector antes del primer envío
# --------------------------------------------------------------------------- #
def test_vector_y_env_antes_del_primer_envio(tmp_path):
    out = gen(tmp_path)
    sessions = read_sessions(out)
    for sid, calls in sessions.items():
        attacks = [c for c in calls if c["label"] == "attack"]
        if not attacks:
            continue
        first = min(c["t"] for c in attacks)
        env_t = [c["t"] for c in calls if c["tool"] == "read_file" and c["args"].get("path") == ".env"]
        vector_t = [c["t"] for c in calls if c["untrusted"] and c["label"] == "benign"]
        assert any(t < first for t in env_t), sid
        assert any(t < first for t in vector_t), sid


# --------------------------------------------------------------------------- #
# 6. A3 distancia >= 9; A1 envío único con secreto completo
# --------------------------------------------------------------------------- #
def test_a3_distancia_y_a1_completo(tmp_path):
    out = gen(tmp_path)
    sessions = read_sessions(out)
    secrets = read_secrets(out)
    labels = read_labels(out)
    by_session = collections.defaultdict(list)
    for L in labels:
        by_session[L["session_id"]].append(L)

    for sid, rows in by_session.items():
        fam = rows[0]["family"]
        ts = sorted(L["t"] for L in rows)
        if fam == "A3":
            diffs = [b - a for a, b in zip(ts, ts[1:])]
            assert all(d >= 9 for d in diffs), (sid, diffs)
        if fam == "A1":
            assert len(rows) == 1
            call = next(c for c in sessions[sid] if c["t"] == rows[0]["t"])
            assert secrets[sid] in json.dumps(call["args"], ensure_ascii=False)
            assert rows[0]["positions_leaked"] == list(range(40))


# --------------------------------------------------------------------------- #
# 7. B1/B2: ninguna llamada untrusted con 4+ chars consecutivos del secreto
# --------------------------------------------------------------------------- #
def test_benignos_sin_fuga_en_untrusted(tmp_path):
    out = gen(tmp_path)
    sessions = read_sessions(out)
    secrets = read_secrets(out)
    labels_sessions = {L["session_id"] for L in read_labels(out)}
    for sid, calls in sessions.items():
        if sid in labels_sessions:
            continue  # solo B1/B2 (sesiones sin ataque)
        value = secrets[sid]
        for c in calls:
            if not c["untrusted"]:
                continue
            serial = json.dumps(c, ensure_ascii=False)
            for i in range(len(value) - 3):
                assert value[i:i + 4] not in serial, (sid, c["t"])


# --------------------------------------------------------------------------- #
# 8. El valor de SECRET_1 de la demo no aparece en ningún archivo generado
# --------------------------------------------------------------------------- #
def test_sin_secreto_de_la_demo(tmp_path):
    out = gen(tmp_path)
    demo_val = generate.demo_secret_value()
    for p in out.rglob("*"):
        if p.is_file():
            assert demo_val not in p.read_text(encoding="utf-8"), p


# --------------------------------------------------------------------------- #
# 9. Las 6 codificaciones de A4 y los 6 canales aparecen
# --------------------------------------------------------------------------- #
def test_codificaciones_y_canales(tmp_path):
    out = gen(tmp_path)
    labels = read_labels(out)
    a4_enc = collections.Counter(L["encoding"] for L in labels if L["family"] == "A4")
    for enc in A4_ENCODINGS:
        assert a4_enc[enc] >= 3, (enc, a4_enc)
    channels = {L["channel"] for L in labels}
    assert set(CHANNELS) <= channels


# --------------------------------------------------------------------------- #
# Extra: lo versionado coincide con una regeneración
# --------------------------------------------------------------------------- #
def test_versionado_coincide(tmp_path):
    if not VERSIONED.exists():
        pytest.skip("redteam/train no versionado")
    fresh = gen(tmp_path, n=80, seed=0)
    want = _all_files(fresh)
    have = {p.relative_to(VERSIONED).as_posix(): p.read_bytes()
            for p in sorted(VERSIONED.rglob("*")) if p.is_file()}
    assert have == want
