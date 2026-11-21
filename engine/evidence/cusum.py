"""CUSUM de Page (documento v4.0, sección 6.3): S_t = max(0, S_{t-1} + l_t)."""

from __future__ import annotations


class Cusum:
    def __init__(self, S0: float = 0.0):
        self.S0 = max(0.0, float(S0))
        self.S = self.S0

    def update(self, l: float) -> float:
        self.S = max(0.0, self.S + float(l))
        return self.S

    def reset(self) -> None:
        self.S = 0.0
