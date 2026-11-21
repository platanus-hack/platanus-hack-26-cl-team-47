"""python -m eval.search --benign data/benign/sessions --attack <carpeta> [--labels ...] [--secrets ...]
    --model models/model.json --out models/search [--workers 0] [--limit-combos N]"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from engine.evidence import FeatureModel
from eval.fit.fit import load_secrets
from eval.replay.core import load_sessions

from .search import GRID, choose, combos, freeze, pareto, search_combos
from .split import split_sessions


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(prog="python -m eval.search")
    ap.add_argument("--benign", required=True)
    ap.add_argument("--attack", required=True)
    ap.add_argument("--labels")
    ap.add_argument("--secrets")
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--limit-combos", type=int)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-false-alarm", type=float, default=1e-3)
    ap.add_argument("--max-benign-rot", type=float, default=5.0)
    args = ap.parse_args(argv)

    t0 = time.perf_counter()
    labels = _read_jsonl(args.labels) if args.labels else []
    secrets = load_secrets(args.secrets)
    benign = load_sessions(args.benign)
    attack = load_sessions(args.attack)

    fam = {l["session_id"]: l.get("family") or "sin_familia" for l in labels}
    given = {l["session_id"]: l["split"] for l in labels if l.get("split")}
    families: dict[str, str | None] = {s[0].session_id: None for s in benign if s}
    for s in attack:
        if s:
            sid = s[0].session_id
            families[sid] = fam.get(sid) or sid.rsplit("-", 1)[0]
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
    if best is not None:
        params = {k: best[k] for k in ("b", "b_rot", "lambda_rot", "T")}
        frozen = freeze(params, args.model, [args.benign, args.attack], str(out / "frozen.json"))
    secs = time.perf_counter() - t0
    n_val_b = sum(1 for s in val if families[s[0].session_id] is None)
    print(f"validación: {n_val_b} benignas, {len(val) - n_val_b} de ataque; {len(rows)} combinaciones en {secs:.1f} s")
    print(f"{len(ok)} combinaciones cumplen las metas; Pareto: {len(front)}; elegida: {best}")
    return {"rows": rows, "pareto": front, "chosen": best, "frozen": frozen, "seconds": secs}


if __name__ == "__main__":
    main()
