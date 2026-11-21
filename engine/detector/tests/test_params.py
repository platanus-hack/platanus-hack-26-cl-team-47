import pytest

from engine.detector import Detector, Params


def test_check_rejects_T200_accepts_T150():
    with pytest.raises(ValueError, match="T=200"):
        Params(T=200).check()
    Params(T=150).check()
    Params(T=153).check()
    with pytest.raises(ValueError):
        Params(T=154).check()


def test_default_T_is_150_and_valid():
    p = Params()
    assert p.T == 150 and p.max_rotations == 3 and p.rotation_window == 200
    p.check()


def test_leak_between_rotations_formula():
    assert Params(T=150).leak_between_rotations() == 3 * 7 * 4
    assert Params(T=200).leak_between_rotations() == 4 * 7 * 4


def test_detector_checks_params():
    with pytest.raises(ValueError):
        Detector(params=Params(T=200))
    Detector(params=Params(T=200), check_params=False)   # solo para el test que documenta la invariante
