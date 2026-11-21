"""python -m eval.final --ours <resumen.json> [--baseline <resumen.json>] [--no-rotation <resumen.json>]
    [--t5 <json con llr y bits>] [--t6 <json con auc_with y auc_without>] --out results/final

Los resúmenes son los que escribe `python -m eval.metrics` (llevan la lista "sessions").
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .report import build_report, to_markdown
from .tests_h import (prevented_reread, t1_false_alarms, t2_detection, t3_vs_baseline, t4_rotation,
                      t5_theorem_slope, t6_gff)


def _sessions(path: str | None) -> list[dict] | None:
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["sessions"] if isinstance(data, dict) else data


def _json(path: str | None) -> dict | None:
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(prog="python -m eval.final")
    ap.add_argument("--ours", required=True)
    ap.add_argument("--baseline")
    ap.add_argument("--no-rotation")
    ap.add_argument("--t5")
    ap.add_argument("--t6")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    from .run import safe_console
    safe_console()

    ours = _sessions(args.ours)
    benign = [s for s in ours if not s["is_attack"]]
    attacks = [s for s in ours if s["is_attack"]]
    results: dict = {"T1": t1_false_alarms(benign), "T2": t2_detection(attacks)}
    if attacks:
        results["T2_reread"] = prevented_reread(attacks)   # fila informativa (#127)

    base = _sessions(args.baseline)
    if base is not None:
        base_att = [s for s in base if s["is_attack"]]
        results["T3"] = t3_vs_baseline(attacks, base_att)
    norot = _sessions(args.no_rotation)
    if norot is not None:
        results["T4"] = t4_rotation(attacks, [s for s in norot if s["is_attack"]])
    t5 = _json(args.t5)
    if t5 is not None:
        results["T5"] = t5_theorem_slope(t5["llr"], t5["bits"], seed=args.seed)
    t6 = _json(args.t6)
    if t6 is not None:
        results["T6"] = t6_gff(t6["auc_with"], t6["auc_without"], seed=args.seed)

    report = build_report(results)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md = to_markdown(report)
    (out / "report.md").write_text(md, encoding="utf-8")
    print(md)
    return report


if __name__ == "__main__":
    main()
