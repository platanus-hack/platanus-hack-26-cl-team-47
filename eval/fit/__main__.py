"""python -m eval.fit --benign data/benign/sessions --attack <carpeta> [--labels labels.jsonl]
[--secrets secrets.jsonl] --out models/model.json"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .fit import fit_model


def report_path(out: str | Path) -> Path:
    out = Path(out)
    return out.with_name(out.stem + ".report.json")


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(prog="python -m eval.fit")
    ap.add_argument("--benign", required=True, help="carpeta con sesiones benignas *.jsonl")
    ap.add_argument("--attack", required=True, help="carpeta con sesiones de ataque *.jsonl")
    ap.add_argument("--labels", help="labels.jsonl del equipo rojo (si no, se usa label de la traza)")
    ap.add_argument("--secrets", help="secrets.jsonl con el secreto propio de cada sesión")
    ap.add_argument("--out", required=True, help="archivo .json del modelo")
    ap.add_argument("--n-bins", type=int, default=10)
    ap.add_argument("--B", type=float, default=3.0)
    args = ap.parse_args(argv)

    model, report = fit_model(args.benign, args.attack, args.labels, args.secrets, args.n_bins, args.B)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(model.to_dict(), indent=2), encoding="utf-8")
    report_path(out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    main()
