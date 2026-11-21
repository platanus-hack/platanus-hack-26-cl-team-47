"""Evaluación final: pruebas T1–T6, Holm y tabla de resultados (paso 14a)."""

from .report import build_report, to_markdown
from .tests_h import holm, prevented_reread, t1_false_alarms, t2_detection, t3_vs_baseline, t4_rotation, t5_theorem_slope, t6_gff

__all__ = ["build_report", "holm", "prevented_reread", "t1_false_alarms", "t2_detection", "t3_vs_baseline", "t4_rotation",
           "t5_theorem_slope", "t6_gff", "to_markdown"]
