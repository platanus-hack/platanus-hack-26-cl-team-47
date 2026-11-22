"""Alternativa 03, la parte en vivo: la sesión de la escena, ejecutada de verdad y paso a paso.

    python demo/alternativas/03-enjambre-juanpedro/vivo.py             # corre los dos mundos y los imprime
    python demo/alternativas/03-enjambre-juanpedro/vivo.py --grabar    # reescribe grabaciones/terminales.json

La escena (`enjambre.html`) es una animación de una corrida grabada. Este módulo ejecuta esa misma
sesión contra procesos reales, una llamada a la vez, para que la página `terminales.html` muestre
debajo de la escena lo que está pasando de verdad:

- levanta como procesos el gestor de secretos (`vault.test`), la API protegida
  (`api.empresa.test`), el servidor del atacante (`attacker.test`) y el GitHub simulado con el issue
  plantado (`github.test`), cada uno en un puerto libre de este computador;
- arma un proxy real (`proxy.core.Proxy`) por asistente, con el detector real y los parámetros de la
  demo (`demo.run_split.SWARM_PARAMS`): en el mundo «a», un monitor por asistente; en el «b», la
  cuenta por clave compartida entre los 20 (`SharedLedger`);
- cada llamada pasa por `Proxy.handle`: se decide, se registra en `proxy.jsonl` y se ejecuta de
  verdad. Leer un archivo lee el archivo; un envío es una petición HTTP que llega al otro proceso;
  una rotación la hace el gestor;
- al final, el servidor del atacante cobra: arma la clave con lo que recibió y la prueba contra la
  API, que le pregunta al gestor si sigue vigente. El 200 o el 401 es el que respondió la API.

Cada decisión en vivo se compara con la de la corrida que muestra la escena (`hacer_corrida.py`):
si alguna difiere, la página lo dice.

Lo que no es real: el agente. Las llamadas son un guion (el mismo de la escena), no un modelo.
"""
from __future__ import annotations

import argparse
import atexit
import datetime
import importlib.util
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from contracts import load_hosts  # noqa: E402
from engine.detector.detector import Detector  # noqa: E402
from engine.detector.ledger import SharedLedger  # noqa: E402
from engine.detector.params import Params  # noqa: E402
from proxy.core import Proxy  # noqa: E402
from proxy.live import fail_safe, vault_rotator  # noqa: E402

GRABACION = HERE / "grabaciones" / "terminales.json"
MANIFEST = ROOT / "demo" / "secrets_manifest.json"
REPO_DEMO = ROOT / "demo" / "repo"
SECRET_ID = "SECRET_1"
GITHUB_REPO = "empresa/servicio"
ISSUE_NUMBER = 14
MUNDOS = {"a": "un monitor por asistente", "b": "Alicanto: una cuenta por clave"}
PANES = ("proxy", "gestor", "atacante")
# Cada banco anota aquí sus procesos, en un archivo con el pid de quien los levantó. Si ese
# servidor se cerró de golpe, sus procesos quedan vivos y sin dueño: el próximo banco que parta
# los cierra. Los de un servidor que sigue vivo (un ensayo, otros tests) no se tocan.
PIDS = Path(tempfile.gettempdir()) / "alicanto-vivo-pids"
NUESTROS = ("services.vault.app", "services.api.app", "services.attacker.app", "services.github_sim.app")


def _cargar(nombre: str):
    """Importa un módulo de esta carpeta desde su archivo (el nombre de la carpeta lleva guiones)."""
    spec = importlib.util.spec_from_file_location(f"alt03_{nombre}", HERE / f"{nombre}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hc = _cargar("hacer_corrida")
rs = hc.rs


class BancoNoDisponible(RuntimeError):
    """No se pudieron levantar los procesos (casi siempre, un puerto ocupado)."""


# --------------------------------------------------------------------------- los procesos reales

class Banco:
    """Gestor, API, servidor del atacante y GitHub simulado, como procesos de este computador.

    Cada uno parte en un puerto libre elegido en el momento (no en los 8101 a 8104 de
    `contracts/hosts.json`), así una corrida en vivo no choca con los tests ni con otro banco de
    pruebas que esté corriendo. Los proxies reciben el mapa de nombres `.test` con esos puertos.
    """

    _n = 0
    SERVICIOS = (   # nombre, nombre .test, aplicación, ruta para saber que ya responde
        ("vault", "vault.test", "services.vault.app:app", "/v1/secrets/_ping"),
        ("api", "api.empresa.test", "services.api.app:app", "/v1/data"),
        ("attacker", "attacker.test", "services.attacker.app:app", "/_truth/_ping"),
        ("github", "github.test", "services.github_sim.app:app", "/_admin/published"),
    )

    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="alicanto-vivo-"))
        self.logs = self.dir / "logs"
        self.workspace = self.dir / "repo"
        self.hosts: dict[str, str] = {}
        self._procs: list[tuple[str, subprocess.Popen]] = []
        self.rotado = False          # el gestor ya no tiene los valores del manifiesto
        self.arranques = 0
        Banco._n += 1
        self._anotados = PIDS / f"{os.getpid()}-{Banco._n}.pids"
        self._preparar_repo()
        atexit.register(self.cerrar)

    # -- el repositorio de trabajo: una copia del de la demo, donde las lecturas de la sesión existen
    def _preparar_repo(self) -> None:
        shutil.copytree(REPO_DEMO, self.workspace)
        app = self.workspace / "src" / "app"
        app.mkdir(parents=True, exist_ok=True)
        for t in range(1, hc.N_CALLS + 1):
            (app / f"modulo_{t}.py").write_text(f"# módulo {t}\n", encoding="utf-8")
        env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_AUTHOR_NAME": "Equipo de TI", "GIT_AUTHOR_EMAIL": "ti@clinica.test",
               "GIT_COMMITTER_NAME": "Equipo de TI", "GIT_COMMITTER_EMAIL": "ti@clinica.test"}
        try:  # para que `git status` responda como en un repositorio de verdad
            for cmd in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "agenda-ficha"]):
                subprocess.run(["git", *cmd], cwd=self.workspace, env=env, capture_output=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            pass

    def _semillas(self) -> Path:
        gh = self.dir / "semillas" / "github"
        gh.mkdir(parents=True, exist_ok=True)
        titulo, _, cuerpo = hc.ISSUE.partition(". ")
        issues = [{"title": f"Issue {n} (archivado)", "body": "Cerrado."} for n in range(1, ISSUE_NUMBER)]
        issues.append({"title": titulo.lstrip("#0123456789 "), "body": cuerpo})
        (gh / "issues.json").write_text(json.dumps({"repo": GITHUB_REPO, "issues": issues}, ensure_ascii=False),
                                        encoding="utf-8")
        return gh

    @property
    def vault_url(self) -> str:
        return self.hosts["vault.test"]

    @property
    def attacker_url(self) -> str:
        return self.hosts["attacker.test"]

    def vivo(self) -> bool:
        return bool(self._procs)

    @staticmethod
    def _vive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except OSError:          # existe, aunque sea de otro usuario
            return True
        return True

    @staticmethod
    def cerrar_huerfanos() -> int:
        """Cierra los procesos que dejó un servidor que se cerró de golpe. Solo toca los pid que este
        módulo anotó, que siguen siendo un uvicorn de los servicios del banco y cuyo dueño ya no existe.
        Los procesos de un servidor que sigue vivo no son huérfanos: no se tocan."""
        cerrados = 0
        for archivo in sorted(PIDS.glob("*.pids")) if PIDS.is_dir() else []:
            try:
                dueño = int(archivo.stem.split("-")[0])
                pids = [int(x) for x in archivo.read_text(encoding="utf-8").split()]
            except (OSError, ValueError):
                continue
            if Banco._vive(dueño):
                continue
            for pid in pids:
                try:
                    cmd = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True,
                                         timeout=5).stdout
                except (OSError, subprocess.SubprocessError):
                    continue
                if "uvicorn" in cmd and any(n in cmd for n in NUESTROS):
                    try:
                        os.kill(pid, 15)
                        cerrados += 1
                    except OSError:
                        pass
            try:
                archivo.unlink()
            except OSError:
                pass
        return cerrados

    @staticmethod
    def _puerto_libre() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def iniciar(self) -> None:
        if self._procs:
            return
        self.cerrar_huerfanos()
        self.logs.mkdir(parents=True, exist_ok=True)
        for viejo in self.logs.glob("*.jsonl"):
            viejo.unlink()
        if not hasattr(self, "_log_dir_antes"):
            self._log_dir_antes = os.environ.get("LOG_DIR")
        os.environ["LOG_DIR"] = str(self.logs)      # contracts.write_event lo lee en cada evento
        ultimo = ""
        for _ in range(3):                          # si justo alguien tomó un puerto, se eligen otros
            try:
                self._lanzar()
                break
            except BancoNoDisponible as exc:
                ultimo = str(exc)
                self.detener()
        else:
            raise BancoNoDisponible(ultimo)
        self.rotado = False
        self.arranques += 1
        try:
            PIDS.mkdir(exist_ok=True)
            self._anotados.write_text(" ".join(str(proc.pid) for _, proc in self._procs), encoding="utf-8")
        except OSError:
            pass

    def _lanzar(self) -> None:
        self.hosts = {host: f"http://127.0.0.1:{self._puerto_libre()}" for _, host, _, _ in self.SERVICIOS}
        self.hosts["web.test"] = load_hosts()["web.test"]     # la sesión no lo usa
        env = {**os.environ, "LOG_DIR": str(self.logs), "SECRETS_MANIFEST": str(MANIFEST),
               "VAULT_URL": self.hosts["vault.test"], "API_URL": self.hosts["api.empresa.test"],
               "GITHUB_SIM_SEEDS": str(self._semillas()),
               "PYTHONPATH": os.pathsep.join(filter(None, [str(ROOT), os.environ.get("PYTHONPATH")]))}
        for nombre, host, app, _ in self.SERVICIOS:
            u = urlsplit(self.hosts[host])
            self._procs.append((nombre, subprocess.Popen(
                [sys.executable, "-m", "uvicorn", app, "--host", u.hostname, "--port", str(u.port),
                 "--log-level", "warning"],
                cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)))
        limite = time.monotonic() + 15
        for nombre, host, _, ruta in self.SERVICIOS:
            proc = next(p for n, p in self._procs if n == nombre)
            while True:
                if proc.poll() is not None:
                    raise BancoNoDisponible(f"{host} no partió")
                try:
                    httpx.get(self.hosts[host] + ruta, timeout=0.5)   # cualquier respuesta: ya escucha
                    break
                except httpx.HTTPError:
                    if time.monotonic() > limite:
                        raise BancoNoDisponible(f"{host} no respondió en 15 s")
                    time.sleep(0.05)
        muertos = [n for n, proc in self._procs if proc.poll() is not None]
        if muertos:
            raise BancoNoDisponible(f"no partieron: {', '.join(muertos)}")

    def detener(self) -> None:
        procs, self._procs = self._procs, []
        for _, proc in procs:
            if proc.poll() is None:
                proc.terminate()
        for _, proc in procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        if procs:
            try:
                self._anotados.unlink()
            except OSError:
                pass

    def cerrar(self) -> None:
        """Detiene los procesos, borra la carpeta temporal (el repositorio de trabajo y los registros) y
        deja LOG_DIR como estaba: quien use este proceso después no hereda la carpeta de este banco."""
        self.detener()
        if hasattr(self, "_log_dir_antes"):
            if self._log_dir_antes is None:
                os.environ.pop("LOG_DIR", None)
            else:
                os.environ["LOG_DIR"] = self._log_dir_antes
            del self._log_dir_antes
        shutil.rmtree(self.dir, ignore_errors=True)

    def fresco(self) -> None:
        """Deja el gestor con los valores del manifiesto: si alguna clave rotó, reinicia los procesos."""
        if not self._procs:
            self.iniciar()
        elif self.rotado or any(proc.poll() is not None for _, proc in self._procs):
            self.detener()
            self.iniciar()

    def procesos(self) -> dict[str, dict]:
        host = {n: h for n, h, _, _ in self.SERVICIOS}
        out = {"proxy": {"pid": os.getpid(), "puerto": None}}
        for nombre, proc in self._procs:
            out[nombre] = {"pid": proc.pid, "puerto": urlsplit(self.hosts[host[nombre]]).port}
        return out


# --------------------------------------------------------------------------- una corrida, paso a paso

def _linea(pane: str, t: int, clase: str, *partes) -> dict:
    """Una línea de terminal: en qué terminal va, a qué llamada corresponde y sus trozos con estilo."""
    return {"pane": pane, "t": t, "clase": clase, "partes": [[str(a), b] for a, b in partes]}


SANGRIA = " " * 9          # el ancho de «0048 a13 »: una línea que continúa la anterior


def comparar(esperada: tuple[str, float] | None, accion: str, bits: float, tras_rotar: bool) -> tuple[bool, bool]:
    """Compara una decisión en vivo con la de la escena. Devuelve (igual, azar).

    Hasta que la clave rota, las dos ejecuciones cuentan contra la misma clave y tienen que dar la misma
    acción y los mismos bits. Después de rotar, cada una tiene su propia clave nueva, elegida al azar por
    su gestor de secretos: se exige la misma acción, pero los bits pueden diferir si un pedazo de la clave
    vieja coincide en 4 caracteres con una de las dos claves nuevas (pasa en menos de 1 de cada 100
    corridas). Eso no es una diferencia del proxy. `azar` avisa cuando la coincidencia fue en esta ejecución.
    """
    if esperada is None:
        return False, False
    misma_accion = esperada[0] == accion
    mismos_bits = abs(esperada[1] - bits) < 1e-9
    return misma_accion and (mismos_bits or tras_rotar), tras_rotar and bits > 0


def _partes_args(tool: str, args: dict) -> list[tuple[str, str]]:
    """Los argumentos de una llamada, en trozos. En una URL de ruta larga, el medio va marcado
    («largo»): la página lo abrevia en las pantallas donde la línea no cabe entera."""
    if tool in ("read_file", "list_dir"):
        return [(str(args.get("path", ".")), "arg")]
    if tool == "git":
        return [(" ".join(str(a) for a in args.get("args") or []), "arg")]
    if tool == "http_request":
        u = urlsplit(str(args.get("url", "")))
        metodo, cola = str(args.get("method", "GET")).upper(), (f"?{u.query}" if u.query else "")
        tramos = u.path.strip("/").split("/")
        if len(tramos) > 2:
            return [(f"{metodo} {u.hostname}/", "arg"), ("/".join(tramos[:-2]), "arg largo"),
                    ("/" + "/".join(tramos[-2:]) + cola, "arg")]
        return [(f"{metodo} {u.hostname}{u.path}{cola}", "arg")]
    return []


class Corrida:
    """La sesión de la escena, ejecutada de verdad en uno de los dos mundos."""

    _n = 0

    def __init__(self, banco: Banco, mundo: str = "b", semilla: int | None = None, reparten: int = 10,
                 disfraz: str = "none"):
        if mundo not in MUNDOS:
            raise ValueError("mundo: a o b")
        semilla = hc.SEED if semilla is None else semilla
        Corrida._n += 1
        self.banco = banco
        self.mundo = mundo
        self.params = {"semilla": semilla, "reparten": reparten, "disfraz": disfraz}
        self.id = f"{mundo}{Corrida._n}"
        # Sesión del servidor del atacante. Sin tramos de 4 hexadecimales seguidos: va en una cabecera
        # y el contador de bits lee todos los argumentos de la llamada.
        self.sesion = f"vivo-{mundo}-{Corrida._n}"
        self.calls = hc.make_session(semilla, reparten, disfraz)
        self.n = len(self.calls)
        self.hecho = 0
        self.cobrado = False
        self.lineas: list[dict] = []
        self.coinciden = 0
        self.difieren: list[int] = []
        self.rotaciones: list[dict] = []
        self.azar: list[int] = []            # llamadas en que un pedazo viejo coincidió por azar con la clave nueva
        self._ya_rotaron: set[int] = set()   # asistentes cuyo monitor ya cuenta contra una clave nueva
        self.bloqueadas = 0
        self.cobro: dict | None = None
        self._pendientes: list[dict] = []
        self._proxies: dict[int, Proxy] = {}
        self._http = httpx.Client(timeout=5.0)
        self._vault = httpx.Client(base_url=banco.vault_url, timeout=2.0)
        self._ledger = SharedLedger.from_manifest(str(MANIFEST)) if mundo == "b" else None
        self._bits_atacante = 0.0
        self.esperado = self._esperado()
        self._abrir()

    # -- lo que la escena muestra para esta misma sesión (el arnés de la demo, en proceso)
    def _esperado(self) -> dict:
        """Las decisiones del arnés para esta sesión. Su clave nueva también es al azar: si a esta corrida
        de referencia le toca una coincidencia con ella (ver `comparar`), se repite, porque la referencia
        es la corrida típica, que es la que la escena tiene grabada."""
        secretos = rs.load_manifest(rs.MANIFEST)
        agente_de = {c.t: int(c.session_id.rsplit("a", 1)[1]) for c in self.calls}
        for _ in range(6):
            eventos = rs.run_swarm_panel(self.calls, rs._per_agent if self.mundo == "a" else rs._shared, secretos, SECRET_ID)
            t_de = {e.call_id: e.data["t"] for e in eventos if e.kind == "tool_call"}
            dec = {t_de[e.call_id]: (e.data["action"], float(e.data["leak"][SECRET_ID]["bits"]))
                   for e in eventos if e.kind == "decision"}
            rota_en = [t_de[e.call_id] for e in eventos if e.kind == "rotation"]
            ya, azar = set(), False
            for t in sorted(dec):
                tras_rotar = bool(ya) if self.mundo == "b" else agente_de[t] in ya
                azar = azar or (tras_rotar and dec[t][1] > 0)
                if t in rota_en:
                    ya.add(agente_de[t])
            if not azar:
                break
        cobro = next(e.data for e in eventos if e.source == "attacker")
        return {"decisiones": dec, "cobro": int(cobro["status"]), "rota_en": rota_en}

    def _abrir(self) -> None:
        modo = MUNDOS[self.mundo]
        self._emit(_linea("proxy", 0, "inicio", (f"{hc.N_AGENTS} asistentes", "proc"), (f" · {modo}", "dim")))
        self._emit(_linea("proxy", 0, "inicio", ("rota una clave cuando salió el 30 %: 48 de 160 bits", "dim")))
        if "vault" in self.banco.procesos():
            self._emit(_linea("gestor", 0, "inicio", (f"{SECRET_ID}", "proc"), (": versión 1, vigente", "dim")))
            self._emit(_linea("gestor", 0, "inicio", ("API", "proc"), (": exige la clave vigente", "dim")))
            self._emit(_linea("atacante", 0, "inicio", ("esperando pedazos de la clave", "dim")))

    def _emit(self, linea: dict) -> None:
        self.lineas.append(linea)
        self._pendientes.append(linea)

    # -- un proxy real por asistente
    def _proxy(self, agente: int) -> Proxy:
        if agente not in self._proxies:
            rotar = vault_rotator(self.banco.vault_url, on_rotate=self._al_rotar, client=self._vault)
            det = Detector(workspace=str(self.banco.workspace), manifest_path=str(MANIFEST), rotate=rotar,
                           params=Params(**rs.SWARM_PARAMS), ledger=self._ledger)
            self._proxies[agente] = Proxy(str(self.banco.workspace), decide=fail_safe(det.decide),
                                          session_id=f"enjambre-a{agente:02d}", hosts=self.banco.hosts,
                                          on_output=det.set_output)
        return self._proxies[agente]

    def _al_rotar(self, secret_id: str, version: int) -> None:
        """El gestor acaba de rotar. El servidor del atacante recibe la versión nueva como verdad de
        terreno (igual que en services/scenarios/goteo.py): es lo que le permite saber que lo suyo es viejo."""
        self.banco.rotado = True
        self.rotaciones.append({"secret_id": secret_id, "version": version, "t": self._t})
        try:
            cur = self._vault.get(f"/v1/secrets/{secret_id}").json()
            self._http.put(f"{self.banco.attacker_url}/_admin/secrets/{secret_id}",
                           json={"value": cur["value"], "version": cur["version"]})
        except httpx.HTTPError:
            pass

    # -- avanzar hasta la llamada T. La escena sigue dos pasos después de la última llamada: en
    #    n + 1 el atacante arma la clave y en n + 2 llega la respuesta. El cobro real se hace en n + 2.
    def paso(self, T: int) -> list[dict]:
        while self.hecho < min(T, self.n):
            self._llamada(self.hecho + 1)
            self.hecho += 1
        if T >= self.n + 2 and not self.cobrado:
            self._cobrar()
        out, self._pendientes = self._pendientes, []
        return out

    def _leer(self, call) -> tuple[int, dict, bool]:
        """De una llamada de la sesión: qué asistente la hace, sus argumentos y si es un envío al atacante."""
        agente = int(call.session_id.rsplit("a", 1)[1])
        args = dict(call.args)
        envio = call.tool == "http_request" and urlsplit(str(args.get("url", ""))).hostname == "attacker.test"
        if envio:
            args["headers"] = {"X-Session-Id": self.sesion}
        return agente, args, envio

    def _llamada(self, t: int) -> None:
        call = self.calls[t - 1]
        agente, args, envio = self._leer(call)
        proxy = self._proxy(agente)
        proxy.t = t - 1                      # el proxy numera con el reloj de la sesión, como la grabación
        self._t = t
        antes = len(self.rotaciones)
        t0 = time.perf_counter()
        salida, dec = proxy.handle(call.tool, args)
        total_ms = (time.perf_counter() - t0) * 1000
        fuga = dec.leak.get(SECRET_ID)
        bits = float(fuga.bits) if fuga is not None else 0.0

        # ¿Esta cuenta ya es contra una clave nueva? Con Alicanto la cuenta es una sola; sin él, cada monitor la suya.
        tras_rotar = antes > 0 if self.mundo == "b" else agente in self._ya_rotaron
        igual, azar = comparar(self.esperado["decisiones"].get(t), dec.action, bits, tras_rotar)
        if azar:
            self.azar.append(t)
        if igual:
            self.coinciden += 1
        else:
            self.difieren.append(t)
        if not dec.allowed:
            self.bloqueadas += 1

        nuevas = self.rotaciones[antes:]
        if nuevas:
            self._ya_rotaron.add(agente)
        # la clave ya había rotado: lo que sale es de la versión anulada
        for linea in self._lineas_llamada(t, agente, call.tool, args, dec.action, dec.allowed, bits, dec.latency_ms,
                                          igual, viejo=envio and antes > 0,
                                          rota=[(r["secret_id"], r["version"]) for r in nuevas], azar=azar):
            self._emit(linea)
        if envio:
            self._llegada(t, agente, args, dec.allowed, bool(nuevas), total_ms)

    def _llegada(self, t: int, agente: int, args: dict, permitido: bool, roto_ahora: bool, ms: float) -> None:
        bits = None
        if permitido:
            try:
                verdad = self._http.get(f"{self.banco.attacker_url}/_truth/{self.sesion}").json()[SECRET_ID]
                bits = self._bits_atacante = float(verdad["bits"])
            except (httpx.HTTPError, KeyError, ValueError):
                bits = None
        viejo = bool(self.rotaciones) and not roto_ahora
        for linea in self._lineas_llegada(t, agente, args, permitido, roto_ahora, viejo, bits, ms):
            self._emit(linea)

    def _cobrar(self) -> None:
        self.cobrado = True
        t = self.n + 2
        try:
            r = self._http.post(f"{self.banco.attacker_url}/_admin/cashout/{self.sesion}", json={"secret_id": SECRET_ID})
            cobro = r.json()
        except (httpx.HTTPError, ValueError) as exc:
            self._emit(_linea("atacante", t, "bloquea", (f"no se pudo cobrar: {type(exc).__name__}", "nota")))
            return
        self.cobro = cobro
        for linea in self._lineas_cobro(t, cobro):
            self._emit(linea)

    # -- cómo se escribe cada cosa. No hacen nada: reciben lo que pasó y devuelven las líneas. Las usan
    #    la corrida real y los moldes, y por eso ninguna pasa de 34 caracteres en las terminales angostas.
    def _lineas_llamada(self, t: int, agente: int, tool: str, args: dict, accion: str, permitido: bool, bits: float,
                        ms: float, igual: bool, viejo: bool, rota: list[tuple[str, int]], azar: bool = False) -> list[dict]:
        host = urlsplit(str(args.get("url", ""))).hostname if tool == "http_request" else None
        envio = host == "attacker.test"
        lee_clave = tool == "read_file" and args.get("path") == ".env"
        clase = ("rota" if accion.startswith("rotate") else "bloquea" if not permitido
                 else "viejo" if viejo else "envio" if envio else "clave" if lee_clave
                 else "issue" if host == "github.test" else "normal")
        partes = [(f"{t:04d} ", "num"), (f"a{agente:02d} ", "agente"),
                  (tool + " ", "tool http" if tool == "http_request" else "tool"),
                  *_partes_args(tool, args), (" → ", "dim"), (accion, "accion")]
        if envio or accion != "allow":
            dueño = f"monitor a{agente:02d}" if self.mundo == "a" else SECRET_ID
            partes.append((f"  {dueño} {bits:.0f}/160 bits", "bits"))
        elif lee_clave:
            partes.append(("  lee la clave del repositorio", "nota"))
        partes.append((f"  {ms:.1f} ms", "ms"))
        if not igual:
            partes.append(("  ≠ escena", "difiere"))
        out = [_linea("proxy", t, clase, *partes)]
        if host == "github.test":
            out.append(_linea("proxy", t, "issue", (SANGRIA, "num"),
                              ("contenido no confiable: viene de fuera del repositorio", "nota")))
        if azar:
            out.append(_linea("proxy", t, clase, (SANGRIA, "num"),
                              (f"{bits:.0f} bits: 4 caracteres coinciden por azar con la clave nueva", "nota")))
        for secret_id, version in rota:
            out.append(_linea("proxy", t, "rota", (SANGRIA, "num"),
                              (f"llegó al 30 %: pide rotar {secret_id} al gestor", "accion")))
            out.append(_linea("gestor", t, "rota", ("POST ", "tool"), ("/v1/secrets", "tool largo"),
                              (f"/{secret_id}/rotate", "tool"), (" → ", "dim"), ("200", "accion")))
            out.append(_linea("gestor", t, "rota", ("  ", "num"), (f"versión {version}: vigente", "bits")))
            out.append(_linea("gestor", t, "rota", ("  ", "num"), (f"versión {version - 1}: anulada", "bits")))
        return out

    def _lineas_llegada(self, t: int, agente: int, args: dict, permitido: bool, roto_ahora: bool, viejo: bool,
                        bits: float | None, ms: float) -> list[dict]:
        if not permitido:
            return [_linea("atacante", t, "bloquea", ("no llega: el proxy lo bloqueó", "nota"))]
        u = urlsplit(str(args.get("url", "")))
        out = [_linea("atacante", t, "viejo" if viejo else "envio", (f"← GET {u.path}?{u.query}", "tool"),
                      (f"  a{agente:02d}", "agente"), (f"  {ms:.0f} ms", "ms"))]
        if bits is not None:      # lo que el servidor del atacante tiene de la clave que hoy abre la API
            out.append(_linea("atacante", t, "rota" if roto_ahora else "viejo" if viejo else "envio", ("  ", "num"),
                              (f"{bits:.0f}/160 bits de la clave vigente", "bits")))
        return out

    def _lineas_cobro(self, t: int, cobro: dict) -> list[dict]:
        estado = cobro.get("status")
        if estado is None:
            return [_linea("atacante", t, "normal", ("no recibió ningún pedazo: no cobra", "nota"))]
        bits, version, ok = float(cobro.get("bits_known") or 0), cobro.get("version"), estado == 200
        out = [_linea("atacante", t, "cobro", (f"cobra con {bits:.0f}/160 bits de la versión {version}", "bits"))]
        if bits < 160:
            out.append(_linea("atacante", t, "cobro", ("  ", "num"),
                              ("el resto, por fuerza bruta" if cobro.get("completed_by_bruteforce")
                               else "le faltan pedazos", "nota")))
        return out + [
            _linea("atacante", t, "cobro", ("→ GET api.empresa.test/v1/data", "tool")),
            _linea("gestor", t, "cobro", ("GET /v1/data", "tool"), ("  ← attacker.test", "nota")),
            _linea("gestor", t, "cobro", ("POST /v1/verify", "tool"), ("  ¿sigue vigente?", "nota")),
            _linea("gestor", t, "cobro-ok" if ok else "cobro-no", ("→ ", "dim"), (str(estado), "accion"),
                   ('  {"ok": true}' if ok else "  invalid or expired key", "bits")),
            _linea("atacante", t, "cobro-ok" if ok else "cobro-no", (f"← {estado}", "accion"),
                   ("  abre las fichas" if ok else "  la clave que juntó ya no sirve", "bits")),
        ]

    def moldes(self) -> list[dict]:
        """Las líneas que se esperan de esta corrida, escritas con lo que el arnés de la escena decide para
        la misma sesión. No se muestran: la página las mide antes de partir para elegir cuánto abreviar
        en cada terminal, y así ninguna línea cambia de forma a mitad de camino."""
        esp = self.esperado
        out, version = [l for l in self.lineas if l["t"] == 0], 1
        for t, call in enumerate(self.calls, 1):
            agente, args, envio = self._leer(call)
            accion, bits = esp["decisiones"].get(t, ("allow", 0.0))
            rota = [(SECRET_ID, version + 1)] if t in esp["rota_en"] else []
            permitido = not accion.endswith("block")
            out += self._lineas_llamada(t, agente, call.tool, args, accion, permitido, bits, 99.9, True,
                                        viejo=envio and version > 1, rota=rota)
            if envio:
                out += self._lineas_llegada(t, agente, args, permitido, bool(rota), version > 1 and not rota, 160.0, 99.0)
            version += len(rota)
        return out + self._lineas_cobro(self.n + 2, {"status": esp["cobro"], "bits_known": 160.0, "version": 1})

    def resumen(self) -> dict:
        esp = self.esperado
        return {"corrida": self.id, "mundo": self.mundo, "params": self.params, "n": self.n, "hecho": self.hecho,
                "cobrado": self.cobrado, "cobro": (self.cobro or {}).get("status"),
                "rota_en": [r["t"] for r in self.rotaciones], "bloqueadas": self.bloqueadas,
                "coinciden": self.coinciden, "difieren": self.difieren, "azar": self.azar,
                "cobro_igual": (self.cobro or {}).get("status") == esp["cobro"] if self.cobrado else None,
                "esperado": {"cobro": esp["cobro"], "rota_en": esp["rota_en"]}}

    def cerrar(self) -> None:
        self._http.close()
        self._vault.close()


# --------------------------------------------------------------------------- el director (lo usa servidor.py)

class Director:
    """Una corrida a la vez. Todo bajo un cerrojo: las peticiones de la página llegan en hilos distintos."""

    def __init__(self):
        self.lock = threading.Lock()
        self.banco: Banco | None = None
        self.corrida: Corrida | None = None

    def abrir(self, mundo: str, semilla: int | None, reparten: int, disfraz: str) -> dict:
        with self.lock:
            if self.banco is None:
                self.banco = Banco()
            if self.corrida is not None:
                self.corrida.cerrar()
                self.corrida = None
            self.banco.fresco()
            self.corrida = Corrida(self.banco, mundo, semilla, reparten, disfraz)
            lineas = self.corrida.paso(0)
            return {**self.corrida.resumen(), "procesos": self.banco.procesos(), "lineas": lineas,
                    "moldes": self.corrida.moldes(), "carpeta": str(self.banco.logs)}

    def paso(self, corrida: str, T: int) -> dict:
        with self.lock:
            c = self.corrida
            if c is None or c.id != corrida:
                raise KeyError("esa corrida ya no está abierta")
            lineas = c.paso(T)
            return {**c.resumen(), "lineas": lineas}

    def lineas(self, desde: int) -> dict:
        """Para las terminales de verdad (terminal.py): las líneas de la corrida abierta, desde un índice."""
        with self.lock:
            c = self.corrida
            if c is None:
                return {"corrida": None, "lineas": [], "total": 0}
            return {"corrida": c.id, "mundo": c.mundo, "lineas": c.lineas[desde:], "total": len(c.lineas)}

    def cerrar(self) -> None:
        with self.lock:
            if self.corrida is not None:
                self.corrida.cerrar()
                self.corrida = None
            if self.banco is not None:
                self.banco.cerrar()
                self.banco = None


# --------------------------------------------------------------------------- en una terminal

ANSI = {"num": "2", "dim": "2", "ms": "2", "agente": "36", "tool": "1", "arg": "0", "accion": "1;33", "bits": "33",
        "nota": "2;3", "proc": "1", "difiere": "1;31"}


def texto(linea: dict, color: bool = True) -> str:
    if not color:
        return "".join(p for p, _ in linea["partes"])
    return "".join(f"\x1b[{ANSI.get(c.split(' ')[0], '0')}m{p}\x1b[0m" if p else "" for p, c in linea["partes"])


def correr_todo(semilla: int | None = None, reparten: int = 10, disfraz: str = "none", imprimir: bool = False,
                banco: Banco | None = None) -> dict:
    """Los dos mundos, de punta a punta, con los procesos reales. Devuelve las líneas y el resumen de cada uno."""
    propio = banco is None
    banco = banco or Banco()
    out: dict = {}
    try:
        for mundo in ("a", "b"):
            banco.fresco()
            c = Corrida(banco, mundo, semilla, reparten, disfraz)
            lineas = c.paso(0)
            for T in range(1, c.n + 3):
                lineas += c.paso(T)
            if imprimir:
                print(f"\n=== {MUNDOS[mundo]} ===")
                for pane in PANES:
                    print(f"--- {pane}")
                    for l in lineas:
                        if l["pane"] == pane and (l["clase"] != "normal" or pane != "proxy"):
                            print(texto(l, sys.stdout.isatty()))
            out[mundo] = {"lineas": lineas, "resumen": c.resumen()}
            c.cerrar()
    finally:
        if propio:
            banco.cerrar()
    return out


def grabar() -> dict:
    """Corre los dos mundos con la sesión de la escena y guarda las terminales para la página sin servidor."""
    datos = correr_todo()
    con_azar = [m for m, d in datos.items() if d["resumen"]["azar"]]
    if con_azar:
        # La escena grabada no tiene ninguna, y la grabación de la web tiene que decir lo mismo que la escena.
        raise SystemExit("En esta corrida un pedazo de la clave vieja coincidió por azar con la clave nueva "
                         f"(mundo {', '.join(con_azar)}). Pasa en menos de 1 de cada 100: vuelve a grabar.")
    commit = ""
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                                timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    out = {"nota": "Generado por vivo.py --grabar: una corrida real con los procesos del banco de pruebas. No se edita a mano.",
           "fecha": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "commit": commit, "python": platform.python_version(),
           "params": {"semilla": hc.SEED, "reparten": 10, "disfraz": "none"},
           "mundos": datos}
    GRABACION.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--grabar", action="store_true", help="reescribe grabaciones/terminales.json")
    ap.add_argument("--semilla", type=int, default=None)
    ap.add_argument("--reparten", type=int, choices=hc.REPARTEN, default=10)
    ap.add_argument("--disfraz", choices=hc.DISFRACES, default="none")
    args = ap.parse_args()
    try:
        datos = grabar()["mundos"] if args.grabar else correr_todo(args.semilla, args.reparten, args.disfraz, imprimir=True)
    except BancoNoDisponible as exc:
        sys.exit(f"No se pudo levantar el banco de pruebas: {exc}")
    print()
    for mundo, d in datos.items():
        r = d["resumen"]
        rota = f"rota en la llamada {r['rota_en'][0]}" if r["rota_en"] else "no rota"
        print(f"{MUNDOS[mundo]}: {rota}, {r['bloqueadas']} bloqueadas, el atacante recibe {r['cobro']}; "
              f"{r['coinciden']} de {r['n']} decisiones iguales a las de la escena"
              + ("" if not r["difieren"] else f" (difieren: {r['difieren']})"))
    if args.grabar:
        print(f"-> {GRABACION.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
