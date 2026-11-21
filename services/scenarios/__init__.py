"""Escenarios en vivo con todos los servicios (paso 9).

    python -m services.scenarios goteo --out logs/goteo
"""

from .goteo import run_goteo

__all__ = ["run_goteo"]
