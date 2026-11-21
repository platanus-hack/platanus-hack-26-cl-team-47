"""`python -m services.stack` cierra sus servicios con cualquier señal de término (tarea 9q, #190).

En macOS y Linux la señal (SIGTERM o SIGHUP) llega solo al proceso padre: sin manejador, los tres
uvicorn quedaban escuchando. En Windows no hay SIGTERM real; se usa CTRL_BREAK_EVENT (SIGBREAK,
lo mismo que llega al cerrar la consola) con un grupo de procesos propio. Ese evento llega también a
los hijos, así que ahí lo que prueba la salida ordenada es el código 128 + SIGBREAK y el mensaje final.
"""

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from contracts import load_hosts
from services import stack as stack_mod
from services.stack import PortInUseError, Stack, how_to_free, port_free

ROOT = Path(__file__).resolve().parents[3]
HOSTS = ("vault.test", "api.empresa.test", "attacker.test")


def _ports():
    hosts = load_hosts()
    return [(urlsplit(hosts[h]).hostname, urlsplit(hosts[h]).port) for h in HOSTS]


def _all_free():
    return all(port_free(h, p) for h, p in _ports())


def _wait(cond, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(0.2)
    return cond()


def _señales():
    if sys.platform == "win32":
        return [pytest.param("SIGBREAK", id="ctrl-break")]
    return [pytest.param("SIGTERM", id="sigterm"), pytest.param("SIGHUP", id="sighup")]


@pytest.mark.parametrize("nombre", _señales())
def test_señal_de_termino_libera_los_tres_puertos(tmp_path, nombre):
    if not _all_free():
        pytest.skip("los puertos 8101 a 8103 ya están ocupados por otro proceso")
    win = sys.platform == "win32"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "services.stack", "--log-dir", str(tmp_path / "logs")],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if win else 0,
    )
    try:
        lines = []
        for raw in proc.stdout:  # los tres servicios ya respondieron cuando sale esta línea
            lines.append(raw.decode("utf-8", "replace"))
            if "Ctrl+C para detener" in lines[-1]:
                break
        assert any("Ctrl+C para detener" in x for x in lines), "".join(lines)
        assert not any(port_free(h, p) for h, p in _ports()), "los servicios no quedaron escuchando"

        proc.send_signal(signal.CTRL_BREAK_EVENT if win else getattr(signal, nombre))
        rest, _ = proc.communicate(timeout=15)
        out = "".join(lines) + rest.decode("utf-8", "replace")
        assert proc.returncode == 128 + getattr(signal, nombre), (proc.returncode, out)
        assert "Servicios detenidos." in out, out
        assert _wait(_all_free, 10), f"puertos ocupados después de {nombre}: {_ports()}"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)


def test_manejadores_de_las_señales_que_existen():
    previas = {n: signal.getsignal(getattr(signal, n)) for n in stack_mod.TERM_SIGNALS if hasattr(signal, n)}
    try:
        instaladas = stack_mod.install_term_handlers()
        esperadas = [getattr(signal, n) for n in stack_mod.TERM_SIGNALS if hasattr(signal, n)]
        assert instaladas == esperadas and signal.SIGTERM in instaladas
        manejador = signal.getsignal(signal.SIGTERM)
        with pytest.raises(stack_mod.Terminated) as e:
            manejador(signal.SIGTERM, None)
        assert e.value.code == 128 + signal.SIGTERM
        assert isinstance(e.value, SystemExit)              # pasa por Stack.__exit__ como cualquier salida
        assert signal.getsignal(signal.SIGTERM) == signal.SIG_IGN   # una segunda señal no corta la limpieza
    finally:
        for n, h in previas.items():
            signal.signal(getattr(signal, n), h)


def test_puerto_ocupado_dice_cual_y_como_liberarlo(tmp_path, capsys):
    host, port = _ports()[0]
    if not port_free(host, port):
        pytest.skip(f"{port} ya está ocupado por otro proceso")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, stack_mod.exclusive_bind_option(), 1)
        s.bind((host, port))
        s.listen(1)
        with pytest.raises(PortInUseError) as e:
            Stack(log_dir=str(tmp_path)).__enter__()
        assert f"vault.test ({host}:{port})" in str(e.value) and how_to_free(port) in str(e.value)
        assert stack_mod.main(["--log-dir", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: Puerto ocupado: vault.test") and str(port) in err


def test_como_liberar_un_puerto_segun_el_sistema(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert how_to_free(8101) == ("Para ver quién lo usa: netstat -ano | findstr :8101 (la última columna es el "
                                 "PID); para cerrarlo: taskkill /PID <PID> /F.")
    monkeypatch.setattr(sys, "platform", "darwin")
    assert how_to_free(8102) == "Para ver quién lo usa: lsof -i :8102; para cerrarlo: kill <PID>."
