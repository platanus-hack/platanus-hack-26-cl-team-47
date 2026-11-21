"""Proxy en vivo: detector real y rotación en el gestor de secretos (tarea 9c).

    PROXY_MODE=live python -m proxy.server

El valor nuevo de un secreto rotado solo viaja al detector: no se escribe en el
workspace ni en el registro. En el registro queda {secret_id, version}.
"""

from __future__ import annotations

import time
from typing import Callable

from contracts import Decision, Event, ToolCall, load_hosts, write_event

from .core import Proxy, default_workspace

DEFAULT_MANIFEST = "demo/secrets_manifest.json"


def vault_rotator(vault_url: str, on_rotate: Callable[[str, int], None] | None = None,
                  client=None) -> Callable[[str], str]:
    """rotate(secret_id): POST /rotate, GET del valor nuevo, aviso on_rotate(secret_id, version)."""
    if client is None:
        import httpx

        client = httpx.Client(base_url=vault_url.rstrip("/"), timeout=5.0)

    def rotate(secret_id: str) -> str:
        r = client.post(f"/v1/secrets/{secret_id}/rotate")
        r.raise_for_status()
        g = client.get(f"/v1/secrets/{secret_id}")
        g.raise_for_status()
        body = g.json()
        version = int(body.get("version", r.json().get("version", 0)))
        if on_rotate is not None:
            on_rotate(secret_id, version)
        return body["value"]

    return rotate


def build_live_proxy(workspace: str | None = None, manifest_path: str = DEFAULT_MANIFEST,
                     vault_url: str | None = None, session_id: str | None = None,
                     client=None) -> Proxy:
    from engine.detector import Detector  # import tardío: el modo por defecto no carga el motor

    workspace = workspace or default_workspace()
    vault_url = vault_url or load_hosts()["vault.test"]
    pending: list[tuple[str, int]] = []

    def on_rotate(secret_id: str, version: int) -> None:
        pending.append((secret_id, version))

    detector = Detector(workspace, manifest_path,
                        rotate=vault_rotator(vault_url, on_rotate=on_rotate, client=client))
    proxy = Proxy(workspace, decide=detector.decide, session_id=session_id,
                  on_output=detector.set_output)

    def on_decision(call: ToolCall, decision: Decision) -> None:
        # La rotación ocurre dentro de decide(); se registra justo después de la decisión.
        while pending:
            sid, version = pending.pop(0)
            write_event(Event(ts=time.time(), session_id=proxy.session_id, source="proxy",
                              kind="rotation", call_id=call.id,
                              data={"secret_id": sid, "version": version}))

    proxy.on_decision = on_decision
    proxy.detector = detector
    return proxy
