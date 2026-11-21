"""Vector de features de una llamada para el modelo de evidencia (paso 8)."""

from __future__ import annotations

from typing import Any

from engine.evidence import content_features


def extract(call: Any, touch: dict, dag_info: dict, bits: dict, prev_kind: str | None) -> dict[str, float]:
    """m, m_sd, jump (grafo); U, n_S, is_sink, prev_source_now_sink (DAG); arg_entropy, short_match (contenido)."""
    kind = dag_info.get("kind")
    f = {
        "m": float(touch.get("m", 0.0)),
        "m_sd": float(touch.get("m_sd", 0.0)),
        "jump": float(touch.get("jump", 0.0)),
        "U": 1.0 if dag_info.get("U") else 0.0,
        "n_S": float(len(dag_info.get("S") or [])),
        "is_sink": 1.0 if getattr(call, "is_sink", False) else 0.0,
        "prev_source_now_sink": 1.0 if (prev_kind == "source" and kind == "sink") else 0.0,
    }
    f.update(content_features(call, bits))
    return f
