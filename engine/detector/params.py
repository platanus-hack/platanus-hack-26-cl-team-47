"""Parámetros del detector del nivel 0 (documento v4.0, sección 6). Se congelan en H20."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Params:
    b: float = 9.2            # umbral de bloqueo por evidencia
    b_rot: float = 4.0        # umbral de rotación por evidencia
    lambda_rot: float = 0.3   # fracción filtrada (confirmada + candidata) que dispara rotación
    alpha: float = 0.2        # umbral de R_plus
    T: int = 200              # llamadas entre rotaciones periódicas de un secreto expuesto
    beta_bits: float = 64.0   # seguridad residual exigida
