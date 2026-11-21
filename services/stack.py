"""Levanta los tres servicios del banco de pruebas: gestor, API protegida y atacante.

    python -m services.stack            # los deja corriendo hasta Ctrl+C

    with Stack(log_dir="logs") as stack:
        ...                             # vault.test :8101, api.empresa.test :8102, attacker.test :8103

Cada servicio corre como subproceso de uvicorn con LOG_DIR, SECRETS_MANIFEST, VAULT_URL y
API_URL en el entorno. Al salir del bloque se detienen siempre, también si hubo un error.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from contracts import load_hosts

REPO_ROOT = Path(__file__).resolve().parents[1]
READY_TIMEOUT_S = 10.0

# nombre, host .test, módulo ASGI, ruta para comprobar que responde
SERVICES = (
    ("vault", "vault.test", "services.vault.app:app", "/v1/secrets/_ping"),
    ("api", "api.empresa.test", "services.api.app:app", "/v1/data"),
    ("attacker", "attacker.test", "services.attacker.app:app", "/_truth/_ping"),
)


class PortInUseError(RuntimeError):
    pass


def exclusive_bind_option() -> int:
    """Opción de socket para un bind que falle si otro ya escucha en el puerto.

    En Windows, SO_REUSEADDR deja bindear un puerto que otro socket ya escucha, así
    que no sirve para detectarlo: se usa SO_EXCLUSIVEADDRUSE. En Linux y macOS,
    SO_REUSEADDR solo permite reutilizar puertos en TIME_WAIT, que es lo que queremos.
    """
    return socket.SO_EXCLUSIVEADDRUSE if sys.platform == "win32" else socket.SO_REUSEADDR


def port_free(host: str, port: int) -> bool:
    """False si otro socket ya escucha en (host, port), en cualquier sistema operativo."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, exclusive_bind_option(), 1)
        try:
            s.bind((host, port))
        except OSError:
            return False
    return True


class Stack:
    def __init__(self, log_dir: str = "logs", manifest: str = "demo/secrets_manifest.json"):
        self.log_dir = Path(log_dir).resolve()
        self.manifest = str(Path(manifest).resolve())
        self.hosts = load_hosts()
        self.urls = {host: self.hosts[host] for _, host, _, _ in SERVICES}
        self._procs: list[tuple[str, subprocess.Popen, object]] = []

    @property
    def vault_url(self) -> str:
        return self.urls["vault.test"]

    @property
    def api_url(self) -> str:
        return self.urls["api.empresa.test"]

    @property
    def attacker_url(self) -> str:
        return self.urls["attacker.test"]

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update(
            LOG_DIR=str(self.log_dir),
            SECRETS_MANIFEST=self.manifest,
            VAULT_URL=self.vault_url,
            API_URL=self.api_url,
            PYTHONPATH=os.pathsep.join(filter(None, [str(REPO_ROOT), env.get("PYTHONPATH")])),
        )
        return env

    def __enter__(self) -> "Stack":
        self.log_dir.mkdir(parents=True, exist_ok=True)
        busy = []
        for name, host, _, _ in SERVICES:
            u = urlsplit(self.urls[host])
            if not port_free(u.hostname, u.port):
                busy.append(f"{host} ({u.hostname}:{u.port})")
        if busy:
            raise PortInUseError("Puerto ocupado: " + ", ".join(busy) + ". Detén lo que lo usa y reintenta.")
        try:
            env = self._env()
            for name, host, app, _ in SERVICES:
                u = urlsplit(self.urls[host])
                err = tempfile.TemporaryFile()
                proc = subprocess.Popen(
                    [sys.executable, "-m", "uvicorn", app, "--host", u.hostname, "--port", str(u.port),
                     "--log-level", "warning"],
                    cwd=REPO_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=err,
                )
                self._procs.append((name, proc, err))
            for name, host, _, probe in SERVICES:
                self._wait_ready(name, self.urls[host] + probe)
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def _wait_ready(self, name: str, url: str) -> None:
        proc, err = next((p, e) for n, p, e in self._procs if n == name)
        deadline = time.monotonic() + READY_TIMEOUT_S
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            try:
                httpx.get(url, timeout=0.5)
                return  # cualquier respuesta HTTP sirve: está escuchando
            except httpx.HTTPError:
                time.sleep(0.1)
        err.seek(0)
        tail = err.read().decode("utf-8", "replace")[-800:]
        raise RuntimeError(f"{name} no respondió en {READY_TIMEOUT_S:.0f} s en {url}.\n{tail}")

    def __exit__(self, *exc) -> None:
        for _, proc, _ in self._procs:
            if proc.poll() is None:
                proc.terminate()
        for _, proc, err in self._procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
            err.close()
        self._procs.clear()


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Levanta gestor, API protegida y atacante hasta Ctrl+C.")
    ap.add_argument("--log-dir", default="logs")
    ap.add_argument("--manifest", default="demo/secrets_manifest.json")
    a = ap.parse_args()
    with Stack(a.log_dir, a.manifest) as s:
        for _, host, _, _ in SERVICES:
            print(f"{host:18} {s.urls[host]}")
        print(f"Registros en {s.log_dir}. Ctrl+C para detener.")
        try:
            signal.pause() if hasattr(signal, "pause") else time.sleep(10**9)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
