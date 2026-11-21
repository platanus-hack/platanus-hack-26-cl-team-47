"""Tabla de resultados de la evaluación final. Ninguna fila se oculta, aunque el resultado sea negativo."""

from __future__ import annotations

from .tests_h import holm

TESTS = [
    ("T1", "Falsas alarmas por llamada expuesta"),
    ("T2", "Detección: ataques prevenidos"),
    ("T3", "Mejor que la línea de base (McNemar)"),
    ("T4", "La rotación frena el goteo (Fisher)"),
    ("T5", "Supuesto del teorema: pendiente de ℓ sobre bits"),
    ("T6", "Aporte del GFF: diferencia de AUC parcial"),
]
HOLM_TESTS = ("T1", "T2", "T3", "T4")


def build_report(results: dict) -> dict:
    """results = {"T1": dict | None, ..., "T6": dict | None}. Agrega Holm sobre los p de T1–T4."""
    tests = {name: results.get(name) for name, _ in TESTS}
    pv = {n: tests[n]["p_value"] for n in HOLM_TESTS if tests.get(n) and tests[n].get("p_value") is not None}
    return {"tests": tests, "holm": holm(pv)}


def _fmt(x, nd=4):
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "sí" if x else "no"
    if isinstance(x, float):
        return f"{x:.{nd}g}"
    return str(x)


def _estimate(name: str, r: dict) -> str:
    if name in ("T1", "T2"):
        return f"{r['k']}/{r['n']} = {_fmt(r['rate'])}"
    if name == "T3":
        return f"b={r['b']}, c={r['c']}"
    if name == "T4":
        return (f"éxito del ataque {r['attack_success_with']}/{r['n_with']} con rotación "
                f"vs {r['attack_success_without']}/{r['n_without']} sin; "
                f"mediana de bits {_fmt(r['median_bits_with'])} vs {_fmt(r['median_bits_without'])}")
    if name == "T5":
        return f"c = {_fmt(r['c'])}"
    return f"ΔAUC = {_fmt(r['diff'])}"


def to_markdown(report: dict) -> str:
    lines = [
        "| Prueba | Qué mide | Estimación | IC 95 % | p ajustado (Holm) | ¿Pasa? | Nota |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, what in TESTS:
        r = report["tests"].get(name)
        if r is None:
            lines.append(f"| {name} | {what} | — | — | — | — | no corrida (faltan datos de entrada) |")
            continue
        ci = r.get("ci")
        ci_s = f"[{_fmt(ci[0])}, {_fmt(ci[1])}]" if ci else "—"
        if name == "T1":
            ci_s = f"≤ {_fmt(ci[1])} (unilateral)"
        elif name == "T2":
            ci_s = f"≥ {_fmt(ci[0])} (unilateral)"
        if name == "T4":
            ci_s = f"Fisher p={_fmt(r['fisher_p'])}; Mann–Whitney p={_fmt(r['mannwhitney_p'])}"
        h = report["holm"].get(name)
        p_adj = _fmt(h["p_adjusted"]) + (" (rechaza H₀)" if h["reject"] else "") if h else "—"
        passed = _fmt(r["pass"]) if "pass" in r else "solo intervalo"
        note = "datos insuficientes" if r.get("underpowered") else ""
        lines.append(f"| {name} | {what} | {_estimate(name, r)} | {ci_s} | {p_adj} | {passed} | {note} |")
    return "\n".join(lines) + "\n"
