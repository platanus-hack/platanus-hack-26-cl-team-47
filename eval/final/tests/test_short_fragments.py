"""La cota de la rotación periódica con pedazos cortos (#189)."""

import json
from pathlib import Path

import pytest

from engine.detector import make_frozen
from eval.final import short_fragments as SF

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def frozen():
    return make_frozen()


def test_pedazos_recorren_la_clave_sin_dar_la_vuelta():
    assert SF.starts(7, 40) == [0, 7, 14, 21, 28, 33]
    assert SF.starts(4, 40) == list(range(0, 40, 4))
    assert set().union(*(range(s, s + 3) for s in SF.starts(3, 40))) == set(range(40))


def test_regla_de_cada_rotacion():
    assert SF.rule_of("Rotación periódica de SECRET_1: 75 llamadas desde la última") == "período"
    assert SF.rule_of("Rotación de SECRET_1: fracción filtrada 0.10 ≥ 0.1") == "contador"
    assert SF.rule_of("Rotación de SECRET_1: expuesto y evidencia S=3.00 ≥ 2") == "evidencia"
    assert SF.rule_of("Rotación periódica de SECRET_2: 75 llamadas") == "otra"


def test_caso_de_params_check_en_la_demo(frozen):
    """7 caracteres cada 51 llamadas con T = 150: la cota de Params.check (84 bits) se alcanza y no se pasa."""
    r = SF.run_combo("demo", 7, 51, "web.test", frozen, calls=320)
    assert r["max_bits_any_version"] == pytest.approx(84.0) and not r["success"]
    assert "período" in r["rotations_by_rule"]


def test_pedazos_de_un_caracter_sin_evidencia_sacan_la_clave(frozen):
    """El contador no cuenta pedazos de menos de 4 caracteres: solo queda la rotación periódica (T = 75)."""
    r = SF.run_combo("no_evidence", 1, 1, "attacker.test", frozen, calls=80)
    assert r["max_bits_any_version"] == 160.0 and r["success"]
    assert set(r["rotations_by_rule"]) <= {"período"}


def test_con_evidencia_los_pedazos_cortos_rotan_al_tiro(frozen):
    r = SF.run_combo("ours", 2, 8, "attacker.test", frozen, calls=120)
    assert r["max_bits_any_version"] <= 8.0 and r["rotations_by_rule"].get("evidencia", 0) >= 1


def test_comando_chico_y_reproducible(tmp_path, monkeypatch):
    monkeypatch.setattr(SF, "SIZES", (2, 7))
    monkeypatch.setattr(SF, "GAPS", (8,))
    monkeypatch.setattr(SF, "DESTS", ("web.test",))
    a = SF.main(["--out", str(tmp_path / "a"), "--calls", "60"])
    b = SF.main(["--out", str(tmp_path / "b"), "--calls", "60"])
    assert a == b and len(a["rows"]) == 2 * 3
    for name in ("summary.md", "summary.json", "RUN.json"):
        assert (tmp_path / "a" / name).is_file()
    md = (tmp_path / "a" / "summary.md").read_text(encoding="utf-8")
    assert len(a["headline"]) == 3 and all(f"- {h}" in md for h in a["headline"])
    assert "| demo | web.test | 7 | 8 |" in md


def test_los_resultados_versionados_coinciden_con_el_codigo():
    """results/short_fragments/summary.json tiene la forma que escribe el comando y las cifras del README."""
    p = ROOT / "results" / "short_fragments" / "summary.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    rows = data["rows"]
    assert len(rows) == len(SF.SYSTEMS) * len(SF.DESTS) * len(SF.SIZES) * len(SF.GAPS)
    assert all(not r["success"] for r in rows if r["piece_chars"] >= SF.MIN_CANDIDATE)
    assert all(not r["success"] for r in rows if r["system"] == "ours")
    assert any(r["success"] for r in rows if r["system"] == "demo" and r["piece_chars"] < SF.MIN_CANDIDATE)
