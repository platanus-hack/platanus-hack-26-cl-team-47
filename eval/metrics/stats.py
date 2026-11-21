"""Intervalos para las métricas de evaluación (documento v4.0, sección 6.4)."""

from __future__ import annotations

from typing import Callable, Sequence

import numpy
from scipy.stats import beta as _beta


def clopper_pearson(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """Intervalo exacto (Clopper–Pearson) para una proporción binomial k/n."""
    if n <= 0:
        return 0.0, 1.0
    if not 0 <= k <= n:
        raise ValueError("se requiere 0 <= k <= n")
    a = 1.0 - conf
    lo = 0.0 if k == 0 else float(_beta.ppf(a / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(_beta.ppf(1 - a / 2, k + 1, n - k))
    return lo, hi


def bootstrap_ci(values: Sequence[float], stat: Callable = numpy.median, n_boot: int = 2000,
                 conf: float = 0.95, seed: int = 0) -> tuple[float, float]:
    """Intervalo bootstrap por percentiles. Determinista para una misma semilla."""
    x = numpy.asarray(list(values), dtype=float)
    if x.size == 0:
        return float("nan"), float("nan")
    rng = numpy.random.default_rng(seed)
    idx = rng.integers(0, x.size, size=(n_boot, x.size))
    stats = numpy.array([stat(x[row]) for row in idx], dtype=float)
    a = (1.0 - conf) / 2
    lo, hi = numpy.quantile(stats, [a, 1 - a])
    return float(lo), float(hi)
