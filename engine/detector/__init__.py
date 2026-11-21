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


def make_frozen(frozen_path: str = "models/search/frozen.json", model_path: str = "models/model.json"):
    """Fábrica del detector CONGELADO (#133): Params de frozen.json y el modelo cuyo sha256 coincide
    con `model_sha256` de frozen.json (si no, ValueError con los dos hashes).

    Devuelve make(**kw) -> Detector(params=<congelados>, model=<modelo>, **kw); kw acepta lo de Detector
    (secrets, ledger, rotate, seed, check_params…) y puede reemplazar params o model para una ablación.
    La función devuelta lleva .params, .model y .frozen. No cambia los valores por defecto de Params."""
    import hashlib

    from engine.evidence import FeatureModel

    frozen = json.loads(Path(frozen_path).read_text(encoding="utf-8"))
    model_bytes = Path(model_path).read_bytes()
    want = frozen.get("model_sha256")
    got = hashlib.sha256(model_bytes).hexdigest()
    # Con core.autocrlf=true (Windows) la copia de trabajo trae CRLF; el hash congelado es el del archivo
    # versionado, con LF. Se acepta el contenido tal como lo guarda git.
    got_lf = hashlib.sha256(model_bytes.replace(b"\r\n", b"\n")).hexdigest()
    if want not in (got, got_lf):
        raise ValueError(f"el modelo {model_path} no es el congelado: sha256 {got}, frozen.json espera {want}")
    params = Params(**frozen["params"])
    model = FeatureModel.from_dict(json.loads(model_bytes.decode("utf-8")))

    def make(**kw):
        kw.setdefault("params", params)
        kw.setdefault("model", model)
        return Detector(**kw)

    make.params, make.model, make.frozen = params, model, frozen
    return make


__all__ = ["Detector", "Params", "SharedLedger", "extract", "make_decide", "make_decide_shared",
           "make_decide_with_model", "make_frozen", "make_measure_only"]
