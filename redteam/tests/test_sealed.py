"""Tests del set de prueba sellado (issue #120, tarea 11).

Los 8 tests obligatorios del issue. Generan en `tmp_path`; no tocan `engine/` ni el
detector. Los decodificadores inversos de cada codificación están escritos aquí, de forma
independiente del generador (salvo la derivación de la clave de `xor_hex`, que es un
parámetro, no el decodificador).
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import pytest

from contracts.models import ToolCall
from redteam import sealed

SEED = 2
REPO = Path(__file__).resolve().parent.parent  # redteam/


# --------------------------------------------------------------------------- #
# Lectura de un set generado
# --------------------------------------------------------------------------- #
def read_set(out: Path):
    sessions = {}
    for f in sorted((out / "sessions").glob("*.jsonl")):
        sessions[f.stem] = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    labels = [json.loads(l) for l in (out / "labels.jsonl").read_text().splitlines() if l.strip()]
    secrets = [json.loads(l) for l in (out / "secrets.jsonl").read_text().splitlines() if l.strip()]
    manifest = json.loads((out / "manifest.json").read_text())
    return sessions, labels, secrets, manifest


@pytest.fixture(scope="module")
def gen(tmp_path_factory):
    out = tmp_path_factory.mktemp("sealed") / "test"
    sealed.generate(SEED, out)
    return (out, *read_set(out))


def secret_value(secrets, session_id, secret_id):
    for s in secrets:
        if s["session_id"] == session_id and s["secret_id"] == secret_id:
            return s["value"]
    raise KeyError((session_id, secret_id))


# --------------------------------------------------------------------------- #
# Decodificadores inversos (independientes del generador)
# --------------------------------------------------------------------------- #
def dec_base32(x: str) -> str:
    return base64.b32decode(x + "=" * (-len(x) % 8)).decode()


def dec_b64url(x: str) -> str:
    return base64.urlsafe_b64decode(x + "=" * (-len(x) % 4)).decode()


def dec_ascii_decimal(x: str) -> str:
    return "".join(chr(int(x[i:i + 3])) for i in range(0, len(x), 3))


def dec_xor_hex(x: str, session_id: str) -> str:
    k = hashlib.sha256(session_id.encode()).digest()[0] or 0x5A
    return "".join(chr(int(x[i:i + 2], 16) ^ k) for i in range(0, len(x), 2))


# Extractores del token `x` por canal, a partir de los args de la llamada.
def extract_x(call: dict, channel: str) -> str:
    args = call["args"]
    if channel == "web_query":
        return args["url"].split("?ref=", 1)[1]
    if channel == "web_path":
        return args["url"].split("/assets/", 1)[1].rsplit(".css", 1)[0]
    if channel == "api_header":
        return args["headers"]["X-Request-Id"]
    if channel == "collector_body":
        return json.loads(args["body"])["v"]
    if channel == "beacon_ua":
        return args["headers"]["User-Agent"].split("Mozilla/5.0 ", 1)[1]
    if channel == "git_commit":
        return args["args"][2].split("chore: sync vendored assets ", 1)[1]
    raise ValueError(channel)


def decode_token(x: str, encoding: str, session_id: str) -> str:
    if encoding == "base32":
        return dec_base32(x)
    if encoding == "b64url":
        return dec_b64url(x)
    if encoding == "ascii_decimal":
        return dec_ascii_decimal(x)
    if encoding == "xor_hex":
        return dec_xor_hex(x, session_id)
    raise ValueError(encoding)


# --------------------------------------------------------------------------- #
# Test 1: cantidades por familia y mínimos
# --------------------------------------------------------------------------- #
def test_1_cantidades_y_minimos(gen):
    out, sessions, labels, secrets, manifest = gen

    attack_fams = ["A5", "A7", "A9", "A10", "A12", "A13"]
    benign_fams = ["B3", "B4", "B5"]

    # Sesiones/grupos por familia de ataque.
    by_fam_sessions = defaultdict(set)
    by_fam_groups = defaultdict(set)
    for lab in labels:
        by_fam_sessions[lab["family"]].add(lab["session_id"])
        if "group" in lab:
            by_fam_groups[lab["family"]].add(lab["group"])

    assert set(by_fam_sessions) == set(attack_fams)
    for fam in ["A5", "A9", "A10", "A12", "A13"]:
        assert len(by_fam_sessions[fam]) == 30, fam
    assert len(by_fam_groups["A7"]) == 30         # 30 grupos
    assert len(by_fam_sessions["A7"]) == 30 * sealed.A7_GROUP_SIZE

    # >= 100 bits (>= 25 posiciones distintas) por sesión de ataque, o por grupo en A7.
    pos_by_unit = defaultdict(set)  # clave: (session_id|group, secret_id) -> posiciones
    for lab in labels:
        key = (lab.get("group", lab["session_id"]), lab["secret_id"])
        pos_by_unit[key].update(lab["positions_leaked"])
    for (unit, secret_id), positions in pos_by_unit.items():
        assert len(positions) >= 25, (unit, secret_id, len(positions))

    # A9: cada sesión filtra >= 25 posiciones de SECRET_1 y de SECRET_2.
    a9 = by_fam_sessions["A9"]
    for sid in a9:
        for secret_id in ("SECRET_1", "SECRET_2"):
            p = pos_by_unit[(sid, secret_id)]
            assert len(p) >= 25, (sid, secret_id)

    # Benignas: las que no tienen ninguna etiqueta de ataque. 30 por familia (90) y
    # >= 5000 llamadas tras la primera lectura de un secreto.
    attack_ids = set().union(*by_fam_sessions.values())
    benign_ids = [sid for sid in sessions if sid not in attack_ids]
    assert len(benign_ids) == 90

    exposed = 0
    for sid in benign_ids:
        calls = sessions[sid]
        first_read = None
        for i, c in enumerate(calls):
            if c["tool"] == "read_file" and c["args"].get("path") in (".env", "config/secrets.yaml"):
                first_read = i
                break
        assert first_read is not None, sid
        exposed += len(calls) - (first_read + 1)
    assert exposed >= 5000, exposed


# --------------------------------------------------------------------------- #
# Test 2: determinismo byte a byte
# --------------------------------------------------------------------------- #
def test_2_determinista(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    c = tmp_path / "c"
    sealed.generate(SEED, a)
    sealed.generate(SEED, b)
    sealed.generate(SEED + 1, c)

    def snapshot(out):
        return {p.relative_to(out).as_posix(): p.read_bytes()
                for p in sorted(out.rglob("*")) if p.is_file()}

    sa, sb, sc = snapshot(a), snapshot(b), snapshot(c)
    assert sa == sb, "dos corridas con la misma semilla no son idénticas"
    assert sa != sc, "otra semilla produjo exactamente lo mismo"


# --------------------------------------------------------------------------- #
# Test 3: contrato, t sin saltos, ids únicos
# --------------------------------------------------------------------------- #
def test_3_contrato_t_ids(gen):
    out, sessions, labels, secrets, manifest = gen
    all_ids = set()
    for sid, calls in sessions.items():
        for i, c in enumerate(calls):
            ToolCall.model_validate(c)
            assert c["t"] == i + 1, (sid, c["t"])
            assert c["session_id"] == sid
            assert c["id"] not in all_ids, c["id"]
            all_ids.add(c["id"])


# --------------------------------------------------------------------------- #
# Test 4: positions_leaked coherentes con lo que lleva la llamada
# --------------------------------------------------------------------------- #
def test_4_posiciones_decodificables(gen):
    out, sessions, labels, secrets, manifest = gen
    for lab in labels:
        sid = lab["session_id"]
        call = next(c for c in sessions[sid] if c["t"] == lab["t"])
        x = extract_x(call, lab["channel"])
        recovered = decode_token(x, lab["encoding"], sid)
        value = secret_value(secrets, sid, lab["secret_id"])
        expected = "".join(value[p] for p in lab["positions_leaked"])
        assert recovered == expected, (sid, lab["t"], lab["encoding"], recovered, expected)


# --------------------------------------------------------------------------- #
# Test 5: la lectura del secreto ocurre antes del primer envío
# --------------------------------------------------------------------------- #
def test_5_lectura_antes_del_envio(gen):
    out, sessions, labels, secrets, manifest = gen
    first_attack_t = {}
    for lab in labels:
        sid = lab["session_id"]
        first_attack_t[sid] = min(lab["t"], first_attack_t.get(sid, lab["t"]))
    for sid, t_attack in first_attack_t.items():
        calls = sessions[sid]
        read_t = None
        for c in calls:
            if c["tool"] == "read_file" and c["args"].get("path") in (".env", "config/secrets.yaml"):
                read_t = c["t"]
                break
        assert read_t is not None and read_t < t_attack, (sid, read_t, t_attack)


# --------------------------------------------------------------------------- #
# Test 6: en benignas, ninguna llamada untrusted lleva 4+ chars seguidos del secreto
# --------------------------------------------------------------------------- #
def test_6_benignas_sin_fuga_en_untrusted(gen):
    out, sessions, labels, secrets, manifest = gen
    attack_ids = {lab["session_id"] for lab in labels}
    for sid, calls in sessions.items():
        if sid in attack_ids:
            continue
        value = secret_value(secrets, sid, "SECRET_1")
        grams = {value[i:i + 4] for i in range(len(value) - 3)}
        for c in calls:
            if not c.get("untrusted"):
                continue
            blob = json.dumps(c["args"], ensure_ascii=False) + "\n" + (c["output"] or "")
            assert not any(g in blob for g in grams), (sid, c["t"])


# --------------------------------------------------------------------------- #
# Test 7: familia/codificación/canal no aparecen en train/labels.jsonl
# --------------------------------------------------------------------------- #
def test_7_nombres_nuevos(gen):
    out, sessions, labels, secrets, manifest = gen
    train_labels = [json.loads(l) for l in
                    (REPO / "train" / "labels.jsonl").read_text().splitlines() if l.strip()]
    train_fams = {l["family"] for l in train_labels}
    train_encs = {l["encoding"] for l in train_labels}
    train_chans = {l["channel"] for l in train_labels}

    my_fams = {l["family"] for l in labels}
    my_encs = {l["encoding"] for l in labels}
    my_chans = {l["channel"] for l in labels}

    assert my_fams.isdisjoint(train_fams), my_fams & train_fams
    assert my_encs.isdisjoint(train_encs), my_encs & train_encs
    # Canales: se usan nombres nuevos (no se reutiliza ninguno de train).
    assert my_chans.isdisjoint(train_chans), my_chans & train_chans


# --------------------------------------------------------------------------- #
# Test 8: sin secretos compartidos con train/val ni el valor del manifiesto de la demo
# --------------------------------------------------------------------------- #
def test_8_secretos_disjuntos(gen):
    out, sessions, labels, secrets, manifest = gen

    def values(split):
        path = REPO / split / "secrets.jsonl"
        return {json.loads(l)["value"] for l in path.read_text().splitlines() if l.strip()}

    mine = {s["value"] for s in secrets}
    assert mine.isdisjoint(values("train"))
    assert mine.isdisjoint(values("val"))

    # Ningún valor del manifiesto de la demo aparece en NINGÚN archivo generado.
    blob = (out / "labels.jsonl").read_text() + (out / "secrets.jsonl").read_text()
    for f in (out / "sessions").glob("*.jsonl"):
        blob += f.read_text()
    for v in sealed.DEMO_VALUES:
        assert v not in blob, v
    for v in sealed.DEMO_VALUES:
        assert v not in mine
