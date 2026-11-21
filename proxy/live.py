"""Proxy en vivo: detector real y rotación en el gestor de secretos (tarea 9c).

    PROXY_MODE=live python -m proxy.server
    PROXY_MODE=live LEDGER_PATH=/ruta/compartida/ledger.json python -m proxy.server   # enjambre (#138)

El valor nuevo de un secreto rotado solo viaja al detector: no se escribe en el
workspace ni en el registro. En el registro queda {secret_id, version}.

Cuenta compartida entre procesos (#138): con LEDGER_PATH (o ledger_path), el detector usa un
SharedLedger que se guarda en ese archivo. En cada llamada, bajo un cerrojo de archivo
(<ledger_path>.lock), el proceso carga la cuenta, sincroniza las rotaciones que pidieron otros
procesos (pide al gestor el valor vigente), decide y guarda. Así varios agentes, cada uno con su
proceso del proxy, comparten una cuenta por clave que además sobrevive entre sesiones. Si no se
puede tomar el cerrojo, falla segura. El archivo no contiene valores de secretos.
"""

from __future__ import annotations

import json
import os
import sys
import time
from contextlib import contextmanager
from typing import Callable, Iterator

from contracts import Decision, Event, ToolCall, load_hosts, write_event

from .core import Proxy, default_workspace

DEFAULT_MANIFEST = "demo/secrets_manifest.json"
DEFAULT_VAULT_TIMEOUT_S = 2.0
RETRY_AFTER_S = 5.0  # tras una falla, no se vuelve a llamar al gestor por ese secreto durante este tiempo
LOCK_TIMEOUT_S = 2.0   # cuánto se espera el cerrojo de la cuenta compartida
LOCK_POLL_S = 0.01
LOCK_STALE_S = 10.0    # un cerrojo más viejo que esto se considera abandonado


class LedgerLockError(Exception):
    """No se pudo tomar el cerrojo de la cuenta compartida a tiempo."""


@contextmanager
def ledger_lock(path: str, timeout_s: float = LOCK_TIMEOUT_S, stale_s: float = LOCK_STALE_S,
                poll_s: float = LOCK_POLL_S) -> Iterator[None]:
    """Cerrojo de archivo `<path>.lock` (O_CREAT | O_EXCL). Reintenta cada poll_s hasta timeout_s; un
    cerrojo con más de stale_s segundos de antigüedad se quita. Se suelta siempre al salir."""
    lock = f"{path}.lock"
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) > stale_s:
                    os.remove(lock)       # abandonado: se quita y se reintenta en seguida
                    continue
            except FileNotFoundError:
                continue                  # lo soltó otro proceso entre medio
            if time.monotonic() >= deadline:
                raise LedgerLockError(f"cerrojo {lock} ocupado por más de {timeout_s:g} s")
            time.sleep(poll_s)
            continue
        else:
            try:
                os.write(fd, str(os.getpid()).encode())
            finally:
                os.close(fd)
            break
    try:
        yield
    finally:
        try:
            os.remove(lock)
        except FileNotFoundError:
            pass


class RotationError(Exception):
    """El gestor no pudo rotar el secreto (conexión, tiempo agotado o respuesta distinta de 200)."""

    def __init__(self, secret_id: str, reason: str):
        super().__init__(f"{secret_id}: {reason}")
        self.secret_id = secret_id
        self.reason = reason


def vault_timeout() -> float:
    try:
        return float(os.environ.get("VAULT_TIMEOUT", DEFAULT_VAULT_TIMEOUT_S))
    except ValueError:
        return DEFAULT_VAULT_TIMEOUT_S


def vault_rotator(vault_url: str, on_rotate: Callable[[str, int], None] | None = None,
                  client=None, retry_after_s: float = RETRY_AFTER_S) -> Callable[[str], str]:
    """rotate(secret_id): POST /rotate, GET del valor nuevo, aviso on_rotate(secret_id, version).
    Cualquier falla del gestor levanta RotationError. Tras una falla, durante retry_after_s
    se levanta RotationError sin volver a llamar al gestor (no se paga el tiempo de espera
    en cada llamada mientras está caído)."""
    failed_at: dict[str, tuple[float, str]] = {}
    if client is None:
        import httpx

        client = httpx.Client(base_url=vault_url.rstrip("/"), timeout=vault_timeout())

    def _call(secret_id: str, method: str, path: str):
        try:
            resp = getattr(client, method)(path)
        except Exception as e:  # conexión rechazada, tiempo agotado, transporte
            raise RotationError(secret_id, f"{method.upper()} {path} falló ({type(e).__name__})") from e
        if resp.status_code != 200:
            raise RotationError(secret_id, f"{method.upper()} {path} respondió {resp.status_code}")
        try:
            return resp.json()
        except ValueError as e:
            raise RotationError(secret_id, f"{method.upper()} {path} devolvió JSON inválido") from e

    def rotate(secret_id: str) -> str:
        last = failed_at.get(secret_id)
        if last is not None and time.monotonic() - last[0] < retry_after_s:
            raise RotationError(secret_id, f"gestor no disponible ({last[1]}); se reintenta en unos segundos")
        try:
            rotated = _call(secret_id, "post", f"/v1/secrets/{secret_id}/rotate")
            body = _call(secret_id, "get", f"/v1/secrets/{secret_id}")
            if not isinstance(body, dict) or not body.get("value"):
                raise RotationError(secret_id, "el gestor no devolvió el valor nuevo")
        except RotationError as e:
            failed_at[secret_id] = (time.monotonic(), e.reason)
            raise
        failed_at.pop(secret_id, None)
        version = int(body.get("version", rotated.get("version", 0) if isinstance(rotated, dict) else 0))
        if on_rotate is not None:
            on_rotate(secret_id, version)
        return body["value"]

    return rotate


def fail_safe(decide: Callable[[ToolCall], Decision],
              on_rotation_error: Callable[[str, str], None] | None = None) -> Callable[[ToolCall], Decision]:
    """Envuelve decide para fallar cerrado.

    - RotationError en un sumidero -> block: nada sale mientras la clave vieja sigue viva.
    - RotationError en una llamada que no es sumidero (lectura) -> allow con el motivo: no saca
      datos, y bloquearla dejaría el proxy inservible mientras el gestor esté caído, porque el
      detector vuelve a pedir la rotación en cada llamada. Los sumideros siguen bloqueados.
    - Cualquier otra excepción del detector -> block.
    """

    def safe_decide(call: ToolCall) -> Decision:
        try:
            return decide(call)
        except LedgerLockError as e:
            if not call.is_sink:
                return Decision(action="allow",
                                reason=f"No se pudo tomar la cuenta compartida ({e}). La llamada no envía datos; "
                                       "los sumideros se bloquean hasta poder decidir con la cuenta.")
            return Decision(action="block",
                            reason=f"No se pudo tomar la cuenta compartida ({e}). Se bloquea por seguridad: "
                                   "no se decide sin la cuenta compartida.")
        except RotationError as e:
            if on_rotation_error is not None:
                on_rotation_error(e.secret_id, e.reason)
            if not call.is_sink:
                return Decision(action="allow",
                                reason=f"No se pudo rotar {e.secret_id}: {e.reason}. Rotación pendiente: "
                                       "la llamada no envía datos; los sumideros se bloquean hasta rotar.")
            return Decision(action="block",
                            reason=f"No se pudo rotar {e.secret_id}: {e.reason}. Se bloquea por seguridad.")
        except Exception as e:  # noqa: BLE001 - fallar cerrado es el objetivo
            print(f"[proxy] error interno del detector en {call.id}: {type(e).__name__}: {e}", file=sys.stderr)
            return Decision(action="block",
                            reason=f"Error interno del detector: {type(e).__name__}. Se bloquea por seguridad.")

    return safe_decide


def _vault_value(client, secret_id: str) -> str:
    """Valor vigente de un secreto en el gestor (GET /v1/secrets/{id}); RotationError si falla."""
    try:
        resp = client.get(f"/v1/secrets/{secret_id}")
    except Exception as e:  # conexión, tiempo agotado
        raise RotationError(secret_id, f"GET /v1/secrets/{secret_id} falló ({type(e).__name__})") from e
    if resp.status_code != 200:
        raise RotationError(secret_id, f"GET /v1/secrets/{secret_id} respondió {resp.status_code}")
    value = (resp.json() or {}).get("value")
    if not value:
        raise RotationError(secret_id, "el gestor no devolvió el valor vigente")
    return value


def _sync_from_file(ledger, path: str, value_of: Callable[[str], str]) -> None:
    """Carga la cuenta guardada. Si otro proceso rotó un secreto (versión mayor en el archivo), pide el
    valor vigente al gestor y lo pone en el ledger antes de cargar las posiciones (que son de ese valor)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        saved = {k: int(v) for k, v in (json.load(f).get("version") or {}).items()}
    for sid, v in saved.items():
        if sid in ledger.version and v > ledger.version[sid]:
            new = value_of(sid)
            ledger.values[sid] = new
            ledger.bits.rotate(sid, new)   # el motor pasa a medir contra el valor vigente
    ledger.load_state(path, versions=saved)


def shared_ledger_decide(detector, ledger, path: str, value_of: Callable[[str], str],
                         lock_timeout_s: float = LOCK_TIMEOUT_S, lock_stale_s: float = LOCK_STALE_S):
    """decide(call) con la cuenta compartida por archivo: cerrojo, cargar y sincronizar, decidir, guardar."""
    def decide(call: ToolCall) -> Decision:
        with ledger_lock(path, lock_timeout_s, lock_stale_s):
            _sync_from_file(ledger, path, value_of)
            decision = detector.decide(call)
            ledger.save(path)
            return decision
    return decide


def shared_ledger_output(detector, ledger, path: str, value_of: Callable[[str], str],
                         lock_timeout_s: float = LOCK_TIMEOUT_S, lock_stale_s: float = LOCK_STALE_S):
    """on_output con la cuenta compartida: una salida con el valor del secreto lo expone para todos."""
    def on_output(call_id: str, output: str) -> None:
        try:
            with ledger_lock(path, lock_timeout_s, lock_stale_s):
                _sync_from_file(ledger, path, value_of)
                detector.set_output(call_id, output)
                ledger.save(path)
        except (LedgerLockError, RotationError):
            detector.set_output(call_id, output)   # al menos el DAG local; la próxima decisión sincroniza
    return on_output


def build_live_proxy(workspace: str | None = None, manifest_path: str = DEFAULT_MANIFEST,
                     vault_url: str | None = None, session_id: str | None = None,
                     client=None, ledger_path: str | None = None) -> Proxy:
    """ledger_path (o la variable LEDGER_PATH): cuenta compartida por archivo entre procesos (#138).
    Sin ninguno de los dos, el comportamiento de siempre: un detector con su cuenta propia."""
    from engine.detector import Detector  # import tardío: el modo por defecto no carga el motor

    workspace = workspace or default_workspace()
    vault_url = vault_url or load_hosts()["vault.test"]
    ledger_path = ledger_path or os.environ.get("LEDGER_PATH") or None
    pending: list[dict] = []

    def on_rotate(secret_id: str, version: int) -> None:
        pending.append({"secret_id": secret_id, "version": version})

    def on_rotation_error(secret_id: str, reason: str) -> None:
        pending.append({"secret_id": secret_id, "version": None, "error": reason})

    if ledger_path is None:
        detector = Detector(workspace, manifest_path,
                            rotate=vault_rotator(vault_url, on_rotate=on_rotate, client=client))
        proxy = Proxy(workspace, decide=fail_safe(detector.decide, on_rotation_error), session_id=session_id,
                      on_output=detector.set_output)
    else:
        from engine.detector import SharedLedger

        if client is None:
            import httpx

            client = httpx.Client(base_url=vault_url.rstrip("/"), timeout=vault_timeout())
        ledger = SharedLedger.from_manifest(manifest_path)
        detector = Detector(workspace, manifest_path, ledger=ledger,
                            rotate=vault_rotator(vault_url, on_rotate=on_rotate, client=client))
        value_of = lambda sid: _vault_value(client, sid)  # noqa: E731
        decide = shared_ledger_decide(detector, ledger, ledger_path, value_of)
        proxy = Proxy(workspace, decide=fail_safe(decide, on_rotation_error), session_id=session_id,
                      on_output=shared_ledger_output(detector, ledger, ledger_path, value_of))
        proxy.ledger = ledger
        proxy.ledger_path = ledger_path

    def on_decision(call: ToolCall, decision: Decision) -> None:
        # La rotación ocurre dentro de decide(); se registra justo después de la decisión.
        while pending:
            write_event(Event(ts=time.time(), session_id=proxy.session_id, source="proxy",
                              kind="rotation", call_id=call.id, data=pending.pop(0)))

    proxy.on_decision = on_decision
    proxy.detector = detector
    return proxy
