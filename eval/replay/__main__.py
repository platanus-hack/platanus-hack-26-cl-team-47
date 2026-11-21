"""python -m eval.replay --sessions <carpeta con *.jsonl> --decide <modulo>:<fabrica> --out <archivo.jsonl>"""

from __future__ import annotations

import argparse
import time
from collections import Counter

from .core import load_factory, load_sessions, replay, write_events


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m eval.replay")
    ap.add_argument("--sessions", required=True, help="carpeta con una sesión *.jsonl por archivo")
    ap.add_argument("--decide", required=True, help="fábrica make_decide, como modulo:fabrica")
    ap.add_argument("--out", required=True, help="archivo .jsonl de eventos de salida")
    args = ap.parse_args()

    t0 = time.perf_counter()
    sessions = load_sessions(args.sessions)
    events = replay(sessions, load_factory(args.decide))
    write_events(events, args.out)
    secs = time.perf_counter() - t0

    calls = sum(len(s) for s in sessions)
    actions = Counter(e.data["action"] for e in events if e.kind == "decision")
    print(f"{len(sessions)} sesiones, {calls} llamadas, {len(events)} eventos -> {args.out}")
    print(f"{secs:.2f} s ({calls / secs * 60:,.0f} llamadas/min)  acciones: {dict(actions)}")


if __name__ == "__main__":
    main()
