from collections import Counter

from eval.search import split_sessions


def _ids():
    benign = [f"benign-{i:04d}" for i in range(120)]
    attack = [f"atk-{fam}-{i}" for fam in ("A1", "A2", "A3", "A4", "B1", "B2", "A5p", "B3") for i in range(5)]
    fams = {s: None for s in benign}
    fams.update({s: s.split("-")[1] for s in attack})
    return benign, attack, fams


def test_deterministic():
    benign, attack, fams = _ids()
    a = split_sessions(benign + attack, fams, seed=3)
    b = split_sessions(list(reversed(benign + attack)), fams, seed=3)
    assert a == b
    assert a != split_sessions(benign + attack, fams, seed=4)


def test_benign_proportions():
    benign, attack, fams = _ids()
    parts = split_sessions(benign + attack, fams, seed=0)
    c = Counter(parts[s] for s in benign)
    assert abs(c["train"] / 120 - 0.50) <= 0.05
    assert abs(c["val"] / 120 - 0.25) <= 0.05
    assert abs(c["test"] / 120 - 0.25) <= 0.05


def test_family_never_in_two_parts():
    benign, attack, fams = _ids()
    for seed in range(5):
        parts = split_sessions(benign + attack, fams, seed=seed)
        by_family = {}
        for s in attack:
            by_family.setdefault(fams[s], set()).add(parts[s])
        assert all(len(v) == 1 for v in by_family.values())
        assert {p for v in by_family.values() for p in v} == {"train", "val", "test"}


def test_given_split_respected():
    benign, attack, fams = _ids()
    given = {attack[0]: "test", attack[1]: "val"}
    parts = split_sessions(benign + attack, fams, seed=0, given=given)
    assert parts[attack[0]] == "test" and parts[attack[1]] == "val"
