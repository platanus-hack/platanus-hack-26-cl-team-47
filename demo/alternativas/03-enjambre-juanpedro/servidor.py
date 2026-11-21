"""Servidor del pitch: sirve la demo y corre el motor en vivo cuando el público elige el ataque.

    python demo/alternativas/03-enjambre-juanpedro/servidor.py            # puerto 8300

y después, en el navegador:

    http://127.0.0.1:8300/alternativas/03-enjambre-juanpedro/enjambre.html?pitch=1

Hace dos cosas, las dos solo en este computador (escucha en 127.0.0.1):

- sirve la carpeta `demo/` igual que `python -m http.server --directory demo`;
- responde `GET /api/correr?reparten=10&disfraz=base64&semilla=37` corriendo `hacer_corrida.py`
  con esos valores: arma la sesión, la pasa por el motor del repositorio con un monitor por
  agente y con la cuenta global, y devuelve los eventos y un resumen. Cada corrida queda
  impresa en esta terminal.

No escribe archivos y no acepta más valores que los que la página ofrece.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import importlib.util
import json
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
DEMO = HERE.parents[1]
PAGE = f"alternativas/{HERE.name}/enjambre.html"


def load_runner():
    """Importa hacer_corrida.py desde su archivo (el nombre de la carpeta lleva guiones)."""
    spec = importlib.util.spec_from_file_location("alt03_hacer_corrida", HERE / "hacer_corrida.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Handler(http.server.SimpleHTTPRequestHandler):
    runner = None
    lock = threading.Lock()
    quiet = False

    def do_GET(self):  # noqa: N802 (nombre que pide http.server)
        url = urlparse(self.path)
        if url.path == "/api/correr":
            return self._correr(parse_qs(url.query))
        if url.path == "/api/salud":
            return self._json(200, {"ok": True})
        return super().do_GET()

    def _correr(self, q: dict) -> None:
        r = self.runner
        try:
            reparten = int(q.get("reparten", ["10"])[0])
            semilla = int(q.get("semilla", [str(r.SEED)])[0])
            disfraz = q.get("disfraz", ["none"])[0]
            if reparten not in r.REPARTEN or disfraz not in r.DISFRACES or not 0 <= semilla <= 999999:
                raise ValueError
        except (ValueError, TypeError):
            return self._json(400, {"error": f"reparten: {list(r.REPARTEN)}; disfraz: {list(r.DISFRACES)}; "
                                             "semilla: un entero de 0 a 999999"})
        try:
            with self.lock:  # una corrida a la vez
                out = r.correr(semilla, reparten, disfraz)
        except Exception as exc:  # el motor falló: la página sigue con la corrida grabada
            return self._json(500, {"error": f"{type(exc).__name__}: {exc}"})
        if not self.quiet:
            print("\n".join(out["lineas"]), flush=True)
        return self._json(200, out)

    def _json(self, status: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")  # siempre la versión de ahora
        super().end_headers()

    def log_message(self, fmt, *args) -> None:  # noqa: A003
        if not self.quiet and "/api/" in (args[0] if args else ""):
            super().log_message(fmt, *args)


def make_server(port: int = 8300, quiet: bool = False) -> http.server.ThreadingHTTPServer:
    Handler.runner = load_runner()
    Handler.quiet = quiet
    Handler.runner.correr()  # calienta el motor: la primera corrida es la que carga los módulos
    handler = functools.partial(Handler, directory=str(DEMO))
    return http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8300)
    args = ap.parse_args()
    try:
        server = make_server(args.port)
    except OSError as exc:
        sys.exit(f"No se pudo abrir el puerto {args.port}: {exc}. Prueba con --port 8301.")
    base = f"http://127.0.0.1:{server.server_address[1]}/{PAGE}"
    print(f"Motor listo. Pitch de 3 minutos:  {base}?pitch=1")
    print(f"Solo la demo:                    {base}")
    print("Ctrl+C para terminar. Cada corrida en vivo queda impresa aquí abajo.\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
