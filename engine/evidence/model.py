"""Modelo de features -> incremento l_t (documento v4.0, secciones 4.2 y 6.2).

Por feature j: bordes = cuantiles de benignos y ataques juntos (n_bins cajas);
p0^j y p1^j = histogramas con suavizado de Laplace alpha por caja.
l_t = clip(sum_j log(p1^j(f_tj) / p0^j(f_tj)), -B, B).
Una feature ausente aporta 0; un valor fuera de rango cae en la caja del extremo.
"""

from __future__ import annotations

import math
from bisect import bisect_right

import numpy as np


class FeatureModel:
    def __init__(self, n_bins: int = 10, B: float = 3.0, alpha: float = 1.0):
        if n_bins < 1:
            raise ValueError("n_bins >= 1")
        self.n_bins = n_bins
        self.B = float(B)
        self.alpha = float(alpha)
        # feature -> {"edges": bordes interiores ordenados, "logratio": log(p1/p0) por caja}
        self.features: dict[str, dict[str, list[float]]] = {}

    def fit(self, benign: list[dict[str, float]], attack: list[dict[str, float]]) -> "FeatureModel":
        names = sorted({k for r in benign for k in r} | {k for r in attack for k in r})
        self.features = {}
        qs = np.linspace(0, 1, self.n_bins + 1)[1:-1]
        for name in names:
            b = np.array([r[name] for r in benign if name in r], dtype=float)
            a = np.array([r[name] for r in attack if name in r], dtype=float)
            both = np.concatenate([b, a])
            if both.size == 0:
                continue
            # Bordes repetidos (datos con pocos valores) se funden: menos cajas, nunca vacías por diseño.
            edges = sorted(set(np.quantile(both, qs).tolist())) if qs.size else []
            k = len(edges) + 1
            cb = np.bincount([bisect_right(edges, x) for x in b], minlength=k)
            ca = np.bincount([bisect_right(edges, x) for x in a], minlength=k)
            p0 = (cb + self.alpha) / (len(b) + self.alpha * k)
            p1 = (ca + self.alpha) / (len(a) + self.alpha * k)
            self.features[name] = {"edges": edges, "logratio": np.log(p1 / p0).tolist()}
        return self

    def llr(self, features: dict[str, float]) -> float:
        total = 0.0
        for name, value in features.items():
            f = self.features.get(name)
            if f is None or value is None:
                continue
            value = float(value)
            if math.isnan(value):
                continue
            total += f["logratio"][bisect_right(f["edges"], value)]
        return min(self.B, max(-self.B, total))

    def to_dict(self) -> dict:
        return {
            "n_bins": self.n_bins,
            "B": self.B,
            "alpha": self.alpha,
            "features": {k: {"edges": list(v["edges"]), "logratio": list(v["logratio"])}
                         for k, v in self.features.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FeatureModel":
        m = cls(n_bins=d["n_bins"], B=d["B"], alpha=d["alpha"])
        m.features = {k: {"edges": list(v["edges"]), "logratio": list(v["logratio"])}
                      for k, v in d["features"].items()}
        return m
