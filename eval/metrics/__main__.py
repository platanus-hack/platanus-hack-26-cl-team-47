"""python -m eval.metrics --events <archivo.jsonl> --labels <labels.jsonl> --out <resumen.json>"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .metrics import aggregate, load_events, load_labels, session_summary


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(prog="python -m eval.metrics")
    ap.add_argument("--events", required=True, help="eventos .jsonl escritos por eval.replay")
    ap.add_argument("--labels", required=True, help="labels.jsonl del equipo rojo")
    ap.add_argument("--out", required=True, help="resumen .json de salida")
    ap.add_argument("--H", type=float, default=160.0)
    ap.add_argument("--beta", type=float, default=64.0)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    summaries = session_summary(load_events(args.events), load_labels(args.labels), H=args.H, beta=args.beta)
    agg = aggregate(summaries, n_boot=args.n_boot, seed=args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({**agg, "sessions": summaries}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{agg['n_benign_sessions']} benignas, {agg['n_attack_sessions']} de ataque -> {out}")
    print(f"falsas alarmas {agg['false_alarm_rate']} IC {agg['false_alarm_ci']}; "
          f"prevenidos {agg['prevented_rate']} IC {agg['prevented_ci']}")
    return agg


if __name__ == "__main__":
    main()
