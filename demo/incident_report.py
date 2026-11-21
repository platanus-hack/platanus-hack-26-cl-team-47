"""Informe de incidente por secreto, generado desde un registro de eventos (tarea 15i).

    python demo/incident_report.py --events demo/out/right.jsonl --out demo/out/report.json

Por cada secreto con fuga medida o con rotación: cuándo quedó expuesto, qué llamadas
sacaron bits y hacia dónde, cuándo se rotó y qué recibió el atacante al final. Ningún
campo lleva valores de secretos ni fragmentos: de los argumentos solo se toma el host.
La medición es una cota inferior, así que el texto siempre dice «al menos».
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts import Event, read_events  # noqa: E402


def _destination(call: dict) -> str | None:
    url = (call.get("args") or {}).get("url")
    if isinstance(url, str) and url:
        host = urlsplit(url).hostname
        if host:
            return host
    res = call.get("resources") or []
    return str(res[0]) if res else None


def _call_ref(call: dict) -> dict:
    return {"call_id": call["id"], "t": call["t"], "tool": call["tool"]}


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def _statement(sid: str, bits: float, H: float | None, dests: list[str], n_calls: int,
               rotations: list[dict], final_status: int | None) -> str:
    total = f" de {H:.0f}" if H else ""
    where = f" hacia {', '.join(dests)}" if dests else ""
    s = (f"Salieron al menos {bits:.0f} bits{total} de {sid}{where} "
         f"en {n_calls} {_plural(n_calls, 'llamada', 'llamadas')}.")
    if rotations:
        s += f" La clave se rotó en la llamada {rotations[0]['t']}."
        if final_status != 200:
            s += " La versión filtrada ya no es válida."
    else:
        s += " La clave no se rotó."
        if final_status == 200:
            s += " El atacante la usó con éxito."
    return s


def build_report(events: list[Event], generated_from: str | None = None) -> dict:
    calls: dict[str, dict] = {}
    decisions: list[tuple[dict, dict]] = []  # (llamada, decisión) en orden
    rotation_events: list[Event] = []
    final_status = None
    session_id = events[0].session_id if events else ""

    for e in events:
        if e.kind == "tool_call":
            calls[e.call_id] = e.data
        elif e.kind == "decision" and e.call_id in calls:
            decisions.append((calls[e.call_id], e.data))
        elif e.kind == "rotation":
            rotation_events.append(e)
        elif e.source == "attacker" and e.kind == "received" and isinstance(e.data, dict) \
                and e.data.get("status") is not None:
            final_status = int(e.data["status"])

    decision_of = {c["id"]: d for c, d in decisions}
    secret_ids: list[str] = []
    for _, d in decisions:
        for sid in (d.get("leak") or {}):
            if sid not in secret_ids:
                secret_ids.append(sid)
    for r in rotation_events:
        sid = (r.data or {}).get("secret_id")
        if sid and sid not in secret_ids:
            secret_ids.append(sid)

    out = []
    for sid in secret_ids:
        leak_calls, blocked, prev = [], [], 0.0
        max_bits = max_fraction = 0.0
        H = None
        for call, d in decisions:
            leak = (d.get("leak") or {}).get(sid) or {}
            bits, frac = float(leak.get("bits", 0.0)), float(leak.get("fraction", 0.0))
            if frac > 0:
                H = bits / frac
            max_bits, max_fraction = max(max_bits, bits), max(max_fraction, frac)
            action = d.get("action", "")
            if bits > prev:
                leak_calls.append({**_call_ref(call), "destination": _destination(call),
                                   "bits_after": bits, "action": action})
            if not action.endswith("allow") and (bits > 0 or sid in (d.get("reason") or "")):
                blocked.append({**_call_ref(call), "destination": _destination(call),
                                "action": action, "reason": d.get("reason", "")})
            prev = bits

        rotations = []
        for r in rotation_events:
            if (r.data or {}).get("secret_id") != sid:
                continue
            call = calls.get(r.call_id, {})
            rotations.append({"t": call.get("t"), "version": (r.data or {}).get("version"),
                              "reason": decision_of.get(r.call_id, {}).get("reason", "")})

        if not leak_calls and not rotations:
            continue

        first_rot_t = rotations[0]["t"] if rotations else None
        before = [c for c in leak_calls if first_rot_t is None or c["t"] <= first_rot_t]
        bits_before = max((c["bits_after"] for c in before), default=0.0)
        exposed_at, path = None, []
        if rotations:
            rot_call_id = next(r.call_id for r in rotation_events if (r.data or {}).get("secret_id") == sid)
            path = list(decision_of.get(rot_call_id, {}).get("path") or [])
            first = calls.get(path[0]) if path else None
            if first:
                res = first.get("resources") or []
                exposed_at = {**_call_ref(first), "resource": res[0] if res else None}
        destinations = sorted({c["destination"] for c in leak_calls if c["destination"]})

        out.append({
            "secret_id": sid,
            "exposed_at": exposed_at,
            "leak_calls": leak_calls,
            "max_bits_before_rotation": bits_before if rotations else max_bits,
            "max_fraction": max_fraction,
            "rotations": rotations,
            "blocked_calls": blocked,
            "destinations": destinations,
            "path": path,
            "final_status": final_status,
            "statement": _statement(sid, bits_before if rotations else max_bits, H,
                                    sorted({c["destination"] for c in before if c["destination"]}),
                                    len(before), rotations, final_status),
        })

    return {"session_id": session_id, "generated_from": generated_from or "", "secrets": out}


def write_report(events_path: str | Path, out_path: str | Path) -> Path:
    events_path, out_path = Path(events_path), Path(out_path)
    report = build_report(read_events(events_path), generated_from=events_path.name)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python demo/incident_report.py")
    ap.add_argument("--events", required=True, help="registro JSONL de Event (p. ej. demo/out/right.jsonl)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    path = write_report(a.events, a.out)
    for s in json.loads(path.read_text(encoding="utf-8"))["secrets"]:
        print(s["statement"])
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
