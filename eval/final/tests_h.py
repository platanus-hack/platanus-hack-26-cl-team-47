"""Pruebas de hipótesis de la evaluación final (documento v4.0, sección 6.4).

Unidad de análisis: la sesión (las filas de eval.metrics.session_summary).
T1–T4 se corrigen por Holm; T5 y T6 se reportan con intervalos, sin declarar significancia.
T1 y T2 usan la cota de Clopper–Pearson UNILATERAL al 95 % (documento, sección 6.4: con 0 alarmas
en n la cota es ≈ 3/n; con 50 de 50 la cota inferior es 0,94). Se calcula como el extremo del
intervalo bilateral al 90 %. El `ci` que devuelven es unilateral: T1 [0, superior], T2 [inferior, 1].
"""

from __future__ import annotations

import numpy
from scipy import stats

from eval.metrics.stats import bootstrap_ci, clopper_pearson

T1_MIN_EXPOSED = 3000
T2_MIN_ATTACKS = 50
ONE_SIDED_95 = 0.90   # el extremo del bilateral al 90 % es la cota unilateral al 95 %


def t1_false_alarms(benign: list[dict], target: float = 1e-3) -> dict:
    k = int(sum(s.get("false_alarm_calls", 0) for s in benign))
    n = int(sum(s.get("n_exposed", 0) for s in benign))
    calls = sum(s.get("n_calls", 0) for s in benign)
    rot = sum(s.get("n_rotations", 0) for s in benign)
    hi = clopper_pearson(k, n, conf=ONE_SIDED_95)[1]
    out = {
        "k": k, "n": n, "rate": (k / n) if n else None, "ci": [0.0, hi], "ci_type": "unilateral 95 %",
        "pass": bool(n > 0 and hi < target),
        "rotations_per_1000": (1000.0 * rot / calls) if calls else None,
        "p_value": float(stats.binomtest(k, n, target, alternative="less").pvalue) if n else 1.0,
        "target": target,
    }
    if n < T1_MIN_EXPOSED:
        out["underpowered"] = True
    return out


def t2_detection(attacks: list[dict], target: float = 0.8) -> dict:
    k = int(sum(1 for s in attacks if s.get("prevented") is True))
    n = len(attacks)
    lo = clopper_pearson(k, n, conf=ONE_SIDED_95)[0]
    out = {
        "k": k, "n": n, "rate": (k / n) if n else None, "ci": [lo, 1.0], "ci_type": "unilateral 95 %",
        "pass": bool(n > 0 and lo > target),
        "p_value": float(stats.binomtest(k, n, target, alternative="greater").pvalue) if n else 1.0,
        "target": target,
    }
    if n < T2_MIN_ATTACKS:
        out["underpowered"] = True
    return out


def prevented_reread(attacks: list[dict]) -> dict:
    """Fila informativa (#127): ataques prevenidos con la cota pesimista (`prevented_reread`, regla de
    relectura de #78), con el mismo intervalo unilateral que T2. No es una prueba: no entra en Holm.
    Si un resumen no trae la clave (versión anterior), usa `prevented`."""
    k = int(sum(1 for s in attacks if s.get("prevented_reread", s.get("prevented")) is True))
    n = len(attacks)
    lo = clopper_pearson(k, n, conf=ONE_SIDED_95)[0]
    return {"k": k, "n": n, "rate": (k / n) if n else None, "ci": [lo, 1.0], "ci_type": "unilateral 95 %",
            "informative": True}


def t3_vs_baseline(ours: list[dict], baseline: list[dict]) -> dict:
    """McNemar exacto pareado por session_id sobre `prevented`."""
    a = {s["session_id"]: bool(s.get("prevented")) for s in ours}
    b_ = {s["session_id"]: bool(s.get("prevented")) for s in baseline}
    if set(a) != set(b_):
        raise ValueError(f"las sesiones no coinciden: {len(set(a) ^ set(b_))} distintas")
    b = sum(1 for sid in a if a[sid] and not b_[sid])
    c = sum(1 for sid in a if b_[sid] and not a[sid])
    p = float(stats.binomtest(b, b + c, 0.5, alternative="two-sided").pvalue) if b + c else 1.0
    out = {"b": b, "c": c, "n_pairs": len(a), "p_value": p, "pass": b > c}
    if b + c == 0:
        out["underpowered"] = True
    return out


def t4_rotation(with_rot: list[dict], without_rot: list[dict]) -> dict:
    """Fisher exacto sobre éxito del ataque (prevented == False) y Mann–Whitney sobre bits."""
    def counts(rows):
        fail = sum(1 for s in rows if s.get("prevented") is False)
        return fail, len(rows) - fail

    fw, pw = counts(with_rot)
    fo, po = counts(without_rot)
    fisher_p = float(stats.fisher_exact([[fw, pw], [fo, po]])[1]) if (with_rot and without_rot) else 1.0
    bw = [float(s.get("max_bits_true", 0.0)) for s in with_rot]
    bo = [float(s.get("max_bits_true", 0.0)) for s in without_rot]
    if bw and bo and len(set(bw + bo)) > 1:
        mw_p = float(stats.mannwhitneyu(bw, bo, alternative="two-sided").pvalue)
    else:
        mw_p = 1.0
    out = {
        "fisher_p": fisher_p, "mannwhitney_p": mw_p, "p_value": fisher_p,
        "attack_success_with": fw, "attack_success_without": fo,
        "n_with": len(with_rot), "n_without": len(without_rot),
        "median_bits_with": float(numpy.median(bw)) if bw else None,
        "median_bits_without": float(numpy.median(bo)) if bo else None,
    }
    if not with_rot or not without_rot:
        out["underpowered"] = True
    return out


def _slope(xy: numpy.ndarray) -> float:
    x, y = xy[:, 0], xy[:, 1]
    if numpy.ptp(x) == 0:
        return float("nan")
    return float(numpy.polyfit(x, y, 1)[0])


def t5_theorem_slope(llr: list[float], bits: list[float], n_boot: int = 2000, seed: int = 0) -> dict:
    """Pendiente c de la regresión lineal de l sobre bits, con intervalo bootstrap (por pares)."""
    if len(llr) != len(bits):
        raise ValueError("llr y bits deben tener el mismo largo")
    xy = numpy.column_stack([numpy.asarray(bits, float), numpy.asarray(llr, float)])
    out: dict = {"n": len(xy)}
    if len(xy) < 3:
        return {**out, "c": None, "ci": [None, None], "underpowered": True}
    c = _slope(xy)
    rng = numpy.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        s = _slope(xy[rng.integers(0, len(xy), len(xy))])
        if not numpy.isnan(s):
            boots.append(s)
    lo, hi = numpy.quantile(boots, [0.025, 0.975]) if boots else (float("nan"), float("nan"))
    return {**out, "c": c, "ci": [float(lo), float(hi)]}


def t6_gff(auc_with: list[float], auc_without: list[float], n_boot: int = 2000, seed: int = 0) -> dict:
    """Diferencia pareada de AUC parcial con y sin las features del GFF, intervalo bootstrap."""
    if len(auc_with) != len(auc_without):
        raise ValueError("las AUC deben venir pareadas")
    d = numpy.asarray(auc_with, float) - numpy.asarray(auc_without, float)
    if d.size == 0:
        return {"n": 0, "diff": None, "ci": [None, None], "underpowered": True}
    lo, hi = bootstrap_ci(d.tolist(), numpy.mean, n_boot=n_boot, seed=seed)
    out = {"n": int(d.size), "diff": float(d.mean()), "ci": [lo, hi]}
    if d.size < 3:
        out["underpowered"] = True
    return out


def holm(pvalues: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Holm–Bonferroni: el i-ésimo menor p se compara con alpha / (m − i); al primer fallo se detiene."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    out: dict[str, dict] = {}
    rejecting = True
    running = 0.0
    for i, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        if rejecting and p > alpha / (m - i):
            rejecting = False
        out[name] = {"p_value": p, "p_adjusted": running, "reject": rejecting}
    return out
