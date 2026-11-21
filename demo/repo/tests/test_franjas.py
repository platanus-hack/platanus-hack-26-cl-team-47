from datetime import datetime

from app.franjas import franjas_del_dia


def test_incluye_ultima_franja():
    dia = datetime(2026, 11, 23)
    franjas = franjas_del_dia(dia, "08:00", "18:00", 30)
    assert franjas[0] == dia.replace(hour=8)
    assert franjas[-1] == dia.replace(hour=17, minute=30)
    assert len(franjas) == 20


def test_excluye_ocupadas():
    dia = datetime(2026, 11, 23)
    ocupada = dia.replace(hour=9)
    franjas = franjas_del_dia(dia, "08:00", "10:00", 30, {ocupada})
    assert ocupada not in franjas
    assert len(franjas) == 3
