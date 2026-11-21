"""Features de contenido de una llamada (paso 8)."""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import Any, Mapping


def shannon_entropy(s: str) -> float:
    """Entropía de Shannon por carácter, en bits. Cadena vacía = 0."""
    if not s:
        return 0.0
    n = len(s)
    return max(0.0, -sum(c / n * math.log2(c / n) for c in Counter(s).values()))


def _args(call: Any) -> Any:
    if isinstance(call, Mapping):
        return call.get("args", {})
    return getattr(call, "args", {})


def content_features(call: Any, bits: dict[str, dict]) -> dict[str, float]:
    """arg_entropy: entropía de json.dumps(args, sort_keys=True).
    short_match: suma de candidate_bits sobre todos los secretos (salida de BitsEngine.observe)."""
    text = json.dumps(_args(call) or {}, sort_keys=True, default=str)
    short = sum(float(v.get("candidate_bits", 0.0)) for v in (bits or {}).values())
    return {"arg_entropy": shannon_entropy(text), "short_match": short}
