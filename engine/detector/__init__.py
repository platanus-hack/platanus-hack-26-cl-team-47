"""Detector del nivel 0: decide(ToolCall) -> Decision."""

import json
from pathlib import Path

from .detector import Detector, make_decide, make_decide_shared, make_measure_only
from .features import extract
from .ledger import SharedLedger
from .params import Params


def make_decide_with_model(path: str = "models/model.json"):
    """Fábrica cuyo detector carga el modelo de evidencia guardado por `python -m eval.fit`."""
    from engine.evidence import FeatureModel

    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"no existe el modelo {path}: genéralo con python -m eval.fit ... --out {path}")
    data = json.loads(p.read_text(encoding="utf-8"))

    def factory():
        return Detector(model=FeatureModel.from_dict(data)).decide

    return factory


__all__ = ["Detector", "Params", "SharedLedger", "extract", "make_decide", "make_decide_shared",
           "make_decide_with_model", "make_measure_only"]
