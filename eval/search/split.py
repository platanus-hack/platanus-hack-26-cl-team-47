"""División en entrenamiento, validación y prueba (documento v4.0, sección 6.1).

Benignas: 50/25/25 por sesión, al azar con semilla. Ataques: por familia (una familia nunca
queda en dos partes), salvo que labels.jsonl ya traiga `split` para la sesión.
"""

from __future__ import annotations

import random

PARTS = ("train", "val", "test")


def _cut(items: list, rng: random.Random) -> dict:
    items = list(items)
    rng.shuffle(items)
    n = len(items)
    n_train = round(n * 0.5)
    n_val = round(n * 0.25)
    out = {}
    for i, x in enumerate(items):
        out[x] = "train" if i < n_train else ("val" if i < n_train + n_val else "test")
    return out


def split_sessions(session_ids: list[str], families: dict[str, str | None], seed: int = 0,
                   given: dict[str, str] | None = None) -> dict[str, str]:
    """{session_id: "train" | "val" | "test"}.

    families[sid] = familia de ataque, o None si la sesión es benigna.
    given[sid] = split que trae labels.jsonl; si está, se respeta.
    """
    given = {k: v for k, v in (given or {}).items() if v in PARTS}
    ids = sorted(set(session_ids))
    benign = [s for s in ids if families.get(s) is None and s not in given]
    attack = [s for s in ids if families.get(s) is not None and s not in given]

    out: dict[str, str] = {s: given[s] for s in ids if s in given}
    out.update(_cut(benign, random.Random(f"benign-{seed}")))
    fam_part = _cut(sorted({families[s] for s in attack}), random.Random(f"attack-{seed}"))
    for s in attack:
        out[s] = fam_part[families[s]]
    return out
