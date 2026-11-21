"""Parámetros del detector del nivel 0 (documento v4.0, sección 6). Se congelan en H20."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Params:
    b: float = 9.2            # umbral de bloqueo por evidencia
    b_rot: float = 4.0        # umbral de rotación por evidencia
    lambda_rot: float = 0.3   # fracción filtrada (confirmada + candidata) que dispara rotación
    alpha: float = 0.2        # umbral de R_plus
    T: int = 150              # llamadas entre rotaciones periódicas de un secreto expuesto (#79: era 200)
    beta_bits: float = 64.0   # seguridad residual exigida
    max_rotations: int = 3    # rotaciones de un mismo secreto permitidas dentro de rotation_window (#79)
    rotation_window: int = 200  # llamadas

    def leak_between_rotations(self, bits_per_char: float = 4.0, k: int = 8, W: int = 50) -> float:
        """Bits que puede sacar un envío de k − 1 caracteres cada W + 1 llamadas (nunca acumula
        candidatas, que caducan tras W llamadas) entre dos rotaciones periódicas."""
        return math.ceil(self.T / (W + 1)) * (k - 1) * bits_per_char

    def check(self, H: float = 160.0, bits_per_char: float = 4.0, k: int = 8, W: int = 50) -> None:
        """Invariante: ceil(T / (W + 1)) · (k − 1) · log2|A| ≤ H − beta_bits. Lanza ValueError si no se cumple."""
        leak = self.leak_between_rotations(bits_per_char, k, W)
        limit = H - self.beta_bits
        if leak > limit:
            t_max = (math.floor(limit / ((k - 1) * bits_per_char))) * (W + 1)
            raise ValueError(
                f"Params inválidos: con T={self.T}, W={W} y k={k}, un envío de {k - 1} caracteres cada "
                f"{W + 1} llamadas saca {leak:g} bits entre rotaciones periódicas, más que "
                f"H − beta_bits = {limit:g}. Baja T a {t_max} o menos."
            )
