"""python -m services.scenarios goteo --out logs/goteo

Corre el goteo sin protección (<out>/sin/) y con protección (<out>/con/) e imprime los
dos resultados lado a lado.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .goteo import run_goteo

ROWS = (
    ("session_id", lambda r: r["session_id"]),
    ("rotaciones", lambda r: r["rotations"]),
    ("bloqueadas", lambda r: r["blocked"]),
    ("bits del atacante (vigente)", lambda r: f'{r["truth"]["bits"]:.0f} ({r["truth"]["fraction"]:.0%})'),
    ("máx. bits según el detector", lambda r: f'{r["max_leak_bits_detector"]:.0f}'),
    ("cobro contra la API", lambda r: r["cashout_status"]),
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m services.scenarios")
    sub = ap.add_subparsers(dest="scenario", required=True)
    g = sub.add_parser("goteo", help="goteo de fragmentos del secreto hacia attacker.test")
    g.add_argument("--out", default="logs/goteo")
    g.add_argument("--chunk", type=int, default=4)
    g.add_argument("--every", type=int, default=8)
    g.add_argument("--n-calls", type=int, default=60)
    g.add_argument("--secret-id", default="SECRET_1")
    g.add_argument("--json", action="store_true", help="imprime los resultados como JSON")
    a = ap.parse_args(argv)

    out = Path(a.out)
    kw = dict(chunk=a.chunk, every=a.every, n_calls=a.n_calls, secret_id=a.secret_id)
    sin = run_goteo(False, str(out / "sin"), **kw)
    con = run_goteo(True, str(out / "con"), **kw)

    if a.json:
        print(json.dumps({"sin": sin, "con": con}, indent=2, ensure_ascii=False))
        return 0
    w = max(len(k) for k, _ in ROWS)
    print(f'{"":{w}}  {"sin protección":>26}  {"con protección":>26}')
    for label, get in ROWS:
        print(f"{label:{w}}  {str(get(sin)):>26}  {str(get(con)):>26}")
    print(f"\nRegistros: {out / 'sin'}  y  {out / 'con'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
