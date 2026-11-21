"""Pipeline de estimación del modelo de evidencia (paso 8b; documento v4.0, secciones 4.2, 6.1 y 6.2).

Sesiones (benignas y de ataque) -> features por llamada con el detector en solo medición ->
FeatureModel.fit -> informe con la deriva d0 y la varianza v de l en las benignas.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy

from contracts import ToolCall
from engine.detector import Detector
from engine.evidence import FeatureModel
from eval.replay.core import load_sessions


def session_features(session: list[ToolCall], secrets: dict[str, str] | None = None) -> list[dict[str, float]]:
    """Features de cada llamada de la sesión, en orden, con Detector(enforce=False, model=None)."""
    det = Detector(enforce=False, model=None, secrets=secrets)
    out = []
    for call in sorted(session, key=lambda c: c.t):
        det.decide(call)
        out.append(dict(det.last_features))
    return out


def _read_jsonl(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_secrets(path: str | None) -> dict[str, dict[str, str]]:
    """secrets.jsonl -> {session_id: {secret_id: value}}."""
    out: dict[str, dict[str, str]] = {}
    if path:
        for row in _read_jsonl(path):
            out.setdefault(row["session_id"], {})[row["secret_id"]] = row["value"]
    return out


def fit_model(benign_dir: str, attack_dir: str, labels_path: str | None = None,
              secrets_path: str | None = None, n_bins: int = 10, B: float = 3.0) -> tuple[FeatureModel, dict]:
    secrets = load_secrets(secrets_path)

    benign: list[dict[str, float]] = []
    for session in load_sessions(benign_dir):
        benign += session_features(session)

    labeled: set[tuple[str, int]] | None = None
    if labels_path:
        labeled = {(r["session_id"], int(r["t"])) for r in _read_jsonl(labels_path)
                   if r.get("label", "attack") == "attack"}

    attack: list[dict[str, float]] = []
    for session in load_sessions(attack_dir):
        calls = sorted(session, key=lambda c: c.t)
        if not calls:
            continue
        feats = session_features(calls, secrets.get(calls[0].session_id))
        for call, f in zip(calls, feats):
            is_attack = ((call.session_id, call.t) in labeled) if labeled is not None else call.label == "attack"
            if is_attack:
                attack.append(f)

    if not benign or not attack:
        raise ValueError(f"muestras vacías: {len(benign)} benignas, {len(attack)} de ataque")

    model = FeatureModel(n_bins=n_bins, B=B).fit(benign, attack)
    l_b = numpy.array([model.llr(f) for f in benign])
    l_a = numpy.array([model.llr(f) for f in attack])
    report = {
        "n_benign_calls": len(benign),
        "n_attack_calls": len(attack),
        "d0": float(-l_b.mean()),
        "v": float(l_b.var()),
        "clip_fraction": float(numpy.mean(numpy.isclose(numpy.abs(l_b), model.B))),
        "mean_llr_attack": float(l_a.mean()),
    }
    return model, report
