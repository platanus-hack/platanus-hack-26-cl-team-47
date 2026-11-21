"""Proxy en vivo: detector real y rotación en el gestor de secretos (tarea 9c).

    PROXY_MODE=live python -m proxy.server

El valor nuevo de un secreto rotado solo viaja al detector: no se escribe en el
workspace ni en el registro. En el registro queda {secret_id, version}.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Callable

from contracts import Decision, Event, ToolCall, load_hosts, write_event

from .core import Proxy, default_workspace

DEFAULT_MANIFEST = "demo/secrets_manifest.json"
DEFAULT_VAULT_TIMEOUT_S = 2.0
RETRY_AFTER_S = 5.0  # tras una falla, no se vuelve a llamar al gestor por ese secreto durante este tiempo


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


def build_live_proxy(workspace: str | None = None, manifest_path: str = DEFAULT_MANIFEST,
                     vault_url: str | None = None, session_id: str | None = None,
                     client=None) -> Proxy:
    from engine.detector import Detector  # import tardío: el modo por defecto no carga el motor

    workspace = workspace or default_workspace()
    vault_url = vault_url or load_hosts()["vault.test"]
    pending: list[dict] = []

    def on_rotate(secret_id: str, version: int) -> None:
        pending.append({"secret_id": secret_id, "version": version})

    def on_rotation_error(secret_id: str, reason: str) -> None:
        pending.append({"secret_id": secret_id, "version": None, "error": reason})

    detector = Detector(workspace, manifest_path,
                        rotate=vault_rotator(vault_url, on_rotate=on_rotate, client=client))
    proxy = Proxy(workspace, decide=fail_safe(detector.decide, on_rotation_error), session_id=session_id,
                  on_output=detector.set_output)

    def on_decision(call: ToolCall, decision: Decision) -> None:
        # La rotación ocurre dentro de decide(); se registra justo después de la decisión.
        while pending:
            write_event(Event(ts=time.time(), session_id=proxy.session_id, source="proxy",
                              kind="rotation", call_id=call.id, data=pending.pop(0)))

    proxy.on_decision = on_decision
    proxy.detector = detector
    return proxy
