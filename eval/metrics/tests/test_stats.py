import numpy

from eval.metrics import bootstrap_ci, clopper_pearson


def test_clopper_pearson_bounds():
    lo, hi = clopper_pearson(0, 1000)
    assert lo == 0.0 and 0.0029 <= hi <= 0.0037
    lo, hi = clopper_pearson(50, 50)
    assert lo > 0.92 and hi == 1.0
    lo, hi = clopper_pearson(5, 10)
    assert lo < 0.5 < hi


def test_clopper_pearson_empty():
    assert clopper_pearson(0, 0) == (0.0, 1.0)


def test_bootstrap_deterministic():
    vals = list(numpy.random.default_rng(3).normal(10, 2, 50))
    assert bootstrap_ci(vals, seed=7) == bootstrap_ci(vals, seed=7)
    lo, hi = bootstrap_ci(vals, seed=7)
    assert lo <= float(numpy.median(vals)) <= hi


def test_bootstrap_constant():
    assert bootstrap_ci([32.0] * 5) == (32.0, 32.0)
