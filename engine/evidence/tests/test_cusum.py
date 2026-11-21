import math

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from engine.evidence import Cusum


def test_page_recursion():
    c = Cusum()
    assert c.update(2.0) == 2.0
    assert c.update(-0.5) == 1.5
    assert c.update(-5.0) == 0.0
    assert c.update(1.0) == 1.0


@given(st.lists(st.floats(-10, 10), max_size=200))
def test_never_negative_and_reset(ls):
    c = Cusum(S0=1.0)
    for l in ls:
        assert c.update(l) >= 0.0
    c.reset()
    assert c.S == 0.0


def test_time_to_false_alarm_at_least_e_b():
    """Incrementos exactos N(-v/2, v), v=1: tiempo medio hasta S_t > b=3 es >= e^b (2.000 corridas)."""
    rng = np.random.default_rng(47)
    b, v, runs = 3.0, 1.0, 2000
    lengths = []
    for _ in range(runs):
        c, t = Cusum(), 0
        while True:
            t += 1
            if c.update(rng.normal(-v / 2, math.sqrt(v))) > b:
                break
        lengths.append(t)
    assert np.mean(lengths) >= math.exp(b)
