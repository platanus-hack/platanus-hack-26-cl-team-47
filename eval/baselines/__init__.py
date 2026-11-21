"""Líneas de base (paso 10): defensas simples con la interfaz make_decide() -> decide(ToolCall).

    python -m eval.replay --sessions <carpeta> --decide eval.baselines.allowlist:make_decide --out x.jsonl

- allowlist: egress solo a dominios aprobados.
- detect_secrets_baseline: regex + entropía sobre los argumentos de cada sumidero.
- combined: bloquea si cualquiera de las dos bloquea.
- budget: presupuesto acumulado de bits (réplica de Nimbus), sin CUSUM ni rotación.
"""
