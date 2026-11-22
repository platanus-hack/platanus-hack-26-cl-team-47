"""Servidor del pitch: sirve la demo y corre el motor en vivo cuando el público elige el ataque.

    python demo/alternativas/03-enjambre-juanpedro/servidor.py            # puerto 8300

y después, en el navegador:

    http://127.0.0.1:8300/alternativas/03-enjambre-juanpedro/enjambre.html?pitch=1

Hace tres cosas, las tres solo en este computador (escucha en 127.0.0.1):

- sirve la carpeta `demo/` igual que `python -m http.server --directory demo`;
- responde `GET /api/correr?reparten=10&disfraz=base64&semilla=37` corriendo `hacer_corrida.py`
  con esos valores: arma la sesión, la pasa por el motor del repositorio con un monitor por
  agente y con la cuenta global, y devuelve los eventos y un resumen. Cada corrida queda
  impresa en esta terminal;
- responde `GET /api/sello` recalculando el sha256 del set de prueba tal como está ahora en el
  repositorio, con la receta de `redteam/SELLO.md` (`hacer_evaluacion.py`). La escena «Cómo lo
  probamos» lo compara con el sello publicado.

Para `terminales.html` (la escena con terminales debajo) hace una cuarta cosa, con `vivo.py`:

- `GET /api/vivo/abrir?mundo=a|b&reparten=10&disfraz=none&semilla=47` levanta como procesos el
  gestor de secretos, la API, el servidor del atacante y el GitHub simulado (cada uno en un puerto
  libre), y arma un proxy real por asistente;
- `GET /api/vivo/paso?corrida=<id>&t=<llamada>` ejecuta de verdad las llamadas de la sesión hasta
  esa, y devuelve las líneas de cada terminal. La página la llama cuando la escena llega a esa
  llamada: lo de abajo ocurre en ese momento;
- `GET /api/vivo/lineas?desde=<n>` entrega las mismas líneas a `terminal.py`, para verlas en
  terminales de verdad.

Solo escribe en una carpeta temporal (los registros de esa corrida) y no acepta más valores que
los que la página ofrece.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import importlib.util
import json
import signal
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
INFORME = HERE.parents[2] / "docs" / "informe" / "informe.pdf"
DEMO = HERE.parents[1]
PAGE = f"alternativas/{HERE.name}/enjambre.html"


def _load(name: str):
    """Importa un módulo de esta carpeta desde su archivo (el nombre de la carpeta lleva guiones)."""
    spec = importlib.util.spec_from_file_location(f"alt03_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_runner():
    return _load("hacer_corrida")


class Handler(http.server.SimpleHTTPRequestHandler):
    runner = None
    evaluacion = None
    director = None     # vivo.Director: se crea con la primera corrida en vivo
    lock = threading.Lock()
    quiet = False

    def do_GET(self):  # noqa: N802 (nombre que pide http.server)
        url = urlparse(self.path)
        if url.path == "/api/correr":
            return self._correr(parse_qs(url.query))
        if url.path == "/api/sello":
            return self._sello()
        if url.path == "/api/salud":
            return self._json(200, {"ok": True})
        if url.path.startswith("/api/vivo/"):
            return self._vivo(url.path.rsplit("/", 1)[1], parse_qs(url.query))
        if url.path.endswith(f"/{HERE.name}/informe.pdf"):
            return self._informe(con_cuerpo=True)
        return super().do_GET()

    def do_HEAD(self):  # noqa: N802
        if urlparse(self.path).path.endswith(f"/{HERE.name}/informe.pdf"):
            return self._informe(con_cuerpo=False)
        return super().do_HEAD()

    def _informe(self, con_cuerpo: bool) -> None:
        """El informe técnico, que en el sitio publicado queda junto a la página (publicar.sh)."""
        try:
            datos = INFORME.read_bytes()
        except OSError:
            return self.send_error(404, "File not found")
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        if con_cuerpo:
            self.wfile.write(datos)

    # ---- la sesión de la escena, ejecutada de verdad (vivo.py)

    @classmethod
    def _director(cls):
        with cls.lock:
            if cls.director is None:
                cls.director = _load("vivo").Director()
            return cls.director

    def _vivo(self, que: str, q: dict) -> None:
        r = self.runner
        uno = lambda k, d: q.get(k, [d])[0]  # noqa: E731
        try:
            if que == "abrir":
                mundo, disfraz = uno("mundo", "b"), uno("disfraz", "none")
                reparten, semilla = int(uno("reparten", "10")), int(uno("semilla", str(r.SEED)))
                if mundo not in ("a", "b") or reparten not in r.REPARTEN or disfraz not in r.DISFRACES \
                        or not 0 <= semilla <= 999999:
                    raise ValueError
                out = self._director().abrir(mundo, semilla, reparten, disfraz)
                if not self.quiet:
                    print(f"en vivo, mundo {mundo}: gestor, API y servidor del atacante como procesos; "
                          f"registros en {out['carpeta']}", flush=True)
                return self._json(200, out)
            if que == "paso":
                out = self._director().paso(uno("corrida", ""), int(uno("t", "0")))
                if out["cobrado"] and out["lineas"] and not self.quiet:
                    print(f"  corrida {out['corrida']}: el atacante recibe {out['cobro']}; "
                          f"{out['coinciden']} de {out['n']} decisiones iguales a las de la escena", flush=True)
                return self._json(200, out)
            if que == "lineas":
                return self._json(200, self._director().lineas(max(0, int(uno("desde", "0")))))
        except (ValueError, TypeError):
            return self._json(400, {"error": "parámetros: mundo a|b, reparten, disfraz, semilla; o corrida y t"})
        except KeyError as exc:
            return self._json(410, {"error": str(exc).strip("'")})
        except Exception as exc:  # el banco no se pudo levantar: la página sigue con la grabación
            return self._json(503, {"error": f"{type(exc).__name__}: {exc}"})
        return self._json(404, {"error": "no existe"})

    def _sello(self) -> None:
        try:
            out = self.evaluacion.sello_actual()
        except Exception as exc:  # falta el set o SELLO.md: la página muestra solo el sello publicado
            return self._json(500, {"error": f"{type(exc).__name__}: {exc}"})
        if not self.quiet:
            print(f"sello del set de prueba, recalculado: {out['sha256']} "
                  f"({'coincide con' if out['coincide'] else 'NO coincide con'} el publicado; "
                  f"{out['archivos']} archivos, {out['ms']} ms)", flush=True)
        return self._json(200, out)

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
        # args[0] es la línea de la petición, o un código de estado cuando se registra un error.
        if not self.quiet and "/api/" in str(args[0] if args else ""):
            super().log_message(fmt, *args)


def make_server(port: int = 8300, quiet: bool = False) -> http.server.ThreadingHTTPServer:
    Handler.runner = load_runner()
    Handler.evaluacion = _load("hacer_evaluacion")
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
    print(f"Con terminales en vivo debajo:   {base.replace('enjambre.html', 'terminales.html')}?pitch=1")
    print("Ctrl+C para terminar. Cada corrida en vivo queda impresa aquí abajo.\n", flush=True)

    def _terminar(signum, frame):  # cerrar la terminal o un kill: igual se cierran los procesos del banco
        raise KeyboardInterrupt

    for nombre in ("SIGTERM", "SIGHUP"):
        if hasattr(signal, nombre):
            signal.signal(getattr(signal, nombre), _terminar)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if Handler.director is not None:
            Handler.director.cerrar()


if __name__ == "__main__":
    main()
