"""python -m eval.search --benign data/benign/sessions --attack <carpeta>... [--labels ...] [--secrets ...]
    --model models/model.json --out models/search [--workers 0] [--limit-combos N]

--attack, --labels y --secrets aceptan varios valores: se cargan y concatenan. Con --labels, una
sesión de --attack sin ninguna línea de etiquetas es benigna (B1, B2); su parte sale del prefijo
del session_id (train-, val-, test-) o, si no lo tiene, del reparto al azar de las benignas."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from engine.detector import Detector, Params
from engine.evidence import FeatureModel
from eval.metrics import aggregate, session_summary
from eval.fit.fit import load_secrets
from eval.replay.core import load_sessions, replay

from .search import GRID, choose, combos, freeze, pareto, search_combos
from .split import PARTS, split_sessions


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def split_from_id(sid: str) -> str | None:
    """Parte que indica el prefijo del session_id (train-, val-, test-), o None."""
    head, sep, _ = sid.partition("-")
    return head if sep and head in PARTS else None


def assign_families(benign, attack, labels):
    """(families, given) para split_sessions.

    families[sid]: familia de ataque o None (benigna). given[sid]: parte ya decidida.
    Con etiquetas, una sesión de ataque sin líneas en labels es benigna y su parte sale del
    prefijo del id si lo tiene. Sin etiquetas, toda sesión de ataque usa el prefijo de su id
    como familia (comportamiento anterior).
    """
    fam = {l["session_id"]: l.get("family") or "sin_familia" for l in labels}
    given = {l["session_id"]: l["split"] for l in labels if l.get("split")}
    families: dict[str, str | None] = {s[0].session_id: None for s in benign if s}
    for s in attack:
        if not s:
            continue
        sid = s[0].session_id
        if not labels:
            families[sid] = sid.rsplit("-", 1)[0]
        elif sid in fam:
            families[sid] = fam[sid]
        else:
            families[sid] = None
            part = split_from_id(sid)
            if part:
                given[sid] = part
    return families, given


def family_detail(params, model, sessions, labels, secrets, seed=0) -> dict:
    """aggregate(...)["by_family"] de una combinación (para informar la elegida)."""
    events = []
    for s in sessions:
        if s:
            sec = secrets.get(s[0].session_id)
            events += replay([s], lambda sec=sec: Detector(params=params, model=model, secrets=sec, seed=seed).decide)
    return aggregate(session_summary(events, labels), n_boot=50, seed=seed)["by_family"]


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(prog="python -m eval.search")
    ap.add_argument("--benign", required=True)
    ap.add_argument("--attack", required=True, nargs="+")
    ap.add_argument("--labels", nargs="+", default=[])
    ap.add_argument("--secrets", nargs="+", default=[])
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--limit-combos", type=int)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-false-alarm", type=float, default=1e-3)
    ap.add_argument("--max-benign-rot", type=float, default=5.0)
    args = ap.parse_args(argv)

    t0 = time.perf_counter()
    labels = [l for path in args.labels for l in _read_jsonl(path)]
    secrets: dict[str, dict[str, str]] = {}
    for path in args.secrets:
        for sid, d in load_secrets(path).items():
            secrets.setdefault(sid, {}).update(d)
    benign = load_sessions(args.benign)
    attack = [s for d in args.attack for s in load_sessions(d)]

    families, given = assign_families(benign, attack, labels)
    parts = split_sessions(list(families), families, seed=args.seed, given=given)
    val = [s for s in benign + attack if s and parts[s[0].session_id] == "val"]

    model = FeatureModel.from_dict(json.loads(Path(args.model).read_text(encoding="utf-8")))
    cs = combos(GRID)
    if args.limit_combos:
        cs = cs[: args.limit_combos]
    rows = search_combos(model, val, labels, secrets, cs, workers=args.workers, seed=args.seed)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    front = pareto(rows)
    (out / "pareto.json").write_text(json.dumps(front, indent=2), encoding="utf-8")
    best = choose(rows, args.max_false_alarm, args.max_benign_rot)
    ok = [r for r in rows if (r.get("false_alarm_rate") or 0) <= args.max_false_alarm
          and (r.get("benign_rotations_per_1000") or 0) <= args.max_benign_rot]
    frozen = None
    by_family = None
    if best is not None:
        params = {k: best[k] for k in ("b", "b_rot", "lambda_rot", "T")}
        frozen = freeze(params, args.model, [args.benign, *args.attack], str(out / "frozen.json"))
        by_family = family_detail(Params(**params), model, val, labels, secrets, args.seed)
    secs = time.perf_counter() - t0
    n_val_b = sum(1 for s in val if families[s[0].session_id] is None)
    print(f"validación: {n_val_b} benignas, {len(val) - n_val_b} de ataque; {len(rows)} combinaciones en {secs:.1f} s")
    print(f"{len(ok)} combinaciones cumplen las metas; Pareto: {len(front)}; elegida: {best}")
    if by_family is not None:
        print("elegida por familia: " + json.dumps(by_family))
    return {"rows": rows, "pareto": front, "chosen": best, "frozen": frozen, "seconds": secs,
            "families": families, "parts": parts, "by_family": by_family}


if __name__ == "__main__":
    main()
