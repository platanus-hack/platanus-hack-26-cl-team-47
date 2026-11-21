"""Cálculo de franjas horarias disponibles."""

from datetime import datetime, timedelta


def _hm(texto: str) -> tuple[int, int]:
    h, m = texto.split(":")
    return int(h), int(m)


def franjas_del_dia(fecha: datetime, apertura: str, cierre: str, duracion_min: int,
                    ocupadas: set[datetime] | None = None) -> list[datetime]:
    """Devuelve los inicios de franja libres entre apertura y cierre.

    Una franja es válida si termina a más tardar a la hora de cierre.
    """
    ocupadas = ocupadas or set()
    h, m = _hm(apertura)
    inicio = fecha.replace(hour=h, minute=m, second=0, microsecond=0)
    h, m = _hm(cierre)
    fin = fecha.replace(hour=h, minute=m, second=0, microsecond=0)
    paso = timedelta(minutes=duracion_min)

    franjas = []
    t = inicio
    while t + paso < fin:
        if t not in ocupadas:
            franjas.append(t)
        t += paso
    return franjas
