"""Las terminales de `terminales.html`, en terminales de verdad.

    python demo/alternativas/03-enjambre-juanpedro/terminal.py proxy
    python demo/alternativas/03-enjambre-juanpedro/terminal.py gestor
    python demo/alternativas/03-enjambre-juanpedro/terminal.py atacante
    python demo/alternativas/03-enjambre-juanpedro/terminal.py todo

Se conecta a `servidor.py` (por defecto en el puerto 8300; `--puerto` lo cambia) y va imprimiendo
las líneas de la corrida en vivo a medida que la escena avanza: son las mismas que muestra la
página, pedidas al mismo servidor. Sirve para poner ventanas de terminal debajo del navegador.

No importa el motor ni arranca nada: solo lee. Ctrl+C para salir.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

ORO, GRIS, OSCURO, FIN = "\x1b[38;5;178m", "\x1b[38;5;245m", "\x1b[38;5;240m", "\x1b[0m"
NEGRITA = "\x1b[1m"
LINEA = {"envio": ORO, "viejo": OSCURO, "rota": NEGRITA, "bloquea": NEGRITA, "cobro-ok": ORO + NEGRITA,
         "cobro-no": NEGRITA, "normal": GRIS, "inicio": GRIS, "clave": "", "issue": "", "cobro": ""}
PARTE = {"num": OSCURO, "dim": OSCURO, "ms": OSCURO, "accion": NEGRITA}
TITULO = {"proxy": "proxy", "gestor": "gestor de secretos y API", "atacante": "servidor del atacante"}


def pintar(linea: dict, color: bool, prefijo: str = "") -> str:
    if not color:
        return prefijo + "".join(p for p, _ in linea["partes"])
    base = LINEA.get(linea.get("clase", "normal"), "")
    out = [prefijo]
    for texto, clase in linea["partes"]:
        if texto:
            out.append(f"{base}{PARTE.get(clase.split(' ')[0], '')}{texto}{FIN}")
    return "".join(out)


def seguir(pane: str, puerto: int, color: bool, salida=sys.stdout, vueltas: int | None = None) -> None:
    url = f"http://127.0.0.1:{puerto}/api/vivo/lineas?desde="
    corrida, desde, avisado = None, 0, False
    while vueltas is None or vueltas > 0:
        if vueltas is not None:
            vueltas -= 1
        try:
            with urllib.request.urlopen(url + str(desde), timeout=3) as r:
                d = json.load(r)
            avisado = False
        except (urllib.error.URLError, OSError, ValueError):
            if not avisado:
                print(f"esperando a servidor.py en el puerto {puerto}…", file=salida, flush=True)
                avisado = True
            time.sleep(0.6)
            continue
        if d.get("corrida") != corrida:           # otra corrida: se parte de cero
            corrida, desde = d.get("corrida"), 0
            if corrida is not None:
                mundo = "un monitor por asistente" if d.get("mundo") == "a" else "Alicanto, una cuenta por clave"
                print(f"\n{'─' * 8} {TITULO.get(pane, 'todas las terminales')} · {mundo} {'─' * 8}", file=salida, flush=True)
            continue
        for l in d.get("lineas", []):
            if pane == "todo":
                print(pintar(l, color, f"{l['pane']:<9}"), file=salida)
            elif l["pane"] == pane:
                print(pintar(l, color), file=salida)
        desde = d.get("total", desde)
        salida.flush()
        time.sleep(0.12)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("terminal", choices=["proxy", "gestor", "atacante", "todo"])
    ap.add_argument("--puerto", type=int, default=8300)
    ap.add_argument("--sin-color", action="store_true")
    args = ap.parse_args()
    try:
        seguir(args.terminal, args.puerto, sys.stdout.isatty() and not args.sin_color)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
