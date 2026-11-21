"""Servidor del atacante (attacker.test), puerto 8103. Verdad de terreno.

    uvicorn services.attacker.app:app --port 8103

*    /{cualquier ruta}                 -> 200 {"ok": true}   registra la petición
GET  /_truth/{session_id}              -> 200 {secret_id: {"bits", "fraction", "positions"}}
PUT  /_admin/secrets/{secret_id}  {"value","version"}  -> 200   fija el valor vigente
PUT  /_admin/xor_keys  {"keys": [str]}                 -> 200   claves XOR conocidas
POST /_admin/cashout/{session_id}  {"secret_id"}       -> 200 {"secret_id","version","bits_known","completed_by_bruteforce","status"}

La sesión llega en X-Session-Id (por defecto "default"). Cada petición se escribe como
evento `received` en $LOG_DIR/attacker.jsonl. Las peticiones normales no llevan status.

Cobro (cashout): el atacante elige la versión del secreto de la que más bits obtuvo en la
sesión (a igualdad, la más reciente). Si esos bits alcanzan H − β, completa por fuerza bruta
lo que falta y prueba la clave real de esa versión contra la API protegida. Si no, prueba su
mejor suposición (las posiciones conocidas y el resto relleno), que la API rechaza. β son los
bits que el atacante puede adivinar (ATTACKER_BETA_BITS, por defecto 64: con 40 hex hacen
falta 96 bits filtrados). Registra un `received` con data.status (200 o 401): es lo que
muestra la pantalla dividida. Sin ningún bit, no prueba nada y status es None.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Callable, Optional

import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel

from contracts import Event, load_hosts, write_event
from services.attacker.bits import count_bits
from services.vault.manifest import load_manifest

SESSION_HEADER = "x-session-id"
ApiCall = Callable[[str], int]  # clave -> código HTTP de la API protegida
DEFAULT_BETA_BITS = 64.0


def can_complete(bits_known: float, H: float, beta: float | None = None) -> bool:
    """El atacante gana si sabe al menos H − β bits: el resto lo adivina por fuerza bruta (simulado)."""
    return bits_known >= H - (beta_bits() if beta is None else beta)


def beta_bits() -> float:
    try:
        return float(os.environ.get("ATTACKER_BETA_BITS", DEFAULT_BETA_BITS))
    except ValueError:
        return DEFAULT_BETA_BITS


def http_api_call(api_url: str | None = None, timeout: float = 2.0) -> ApiCall:
    base = (api_url or os.environ.get("API_URL") or load_hosts()["api.empresa.test"]).rstrip("/")

    def call(key: str) -> int:
        try:
            return httpx.get(
                f"{base}/v1/data", headers={"Authorization": f"Bearer {key}"}, timeout=timeout
            ).status_code
        except httpx.HTTPError:
            return 0

    return call


class AttackerState:
    def __init__(self, secrets: dict[str, str]):
        self.lock = threading.Lock()
        # secret_id -> [(version, value)], el último es el vigente
        self.versions: dict[str, list[tuple[int, str]]] = {
            sid: [(1, v)] for sid, v in secrets.items()
        }
        self.xor_keys: list[str] = []
        self.received: dict[str, list[str]] = {}

    def current(self) -> dict[str, tuple[int, str]]:
        return {sid: vs[-1] for sid, vs in self.versions.items()}

    def texts(self, session_id: str) -> list[str]:
        return list(self.received.get(session_id, []))


def _request_texts(method: str, path: str, query: str, headers: dict, body: str) -> list[str]:
    texts = [f"{method} {path}", path]
    if query:
        texts.append(query)
    texts += [v for k, v in headers.items() if k.lower() not in ("host", "content-length", SESSION_HEADER)]
    if body:
        texts.append(body)
    return texts


class SecretIn(BaseModel):
    value: str
    version: int


class XorKeysIn(BaseModel):
    keys: list[str]


class CashoutIn(BaseModel):
    secret_id: str = "SECRET_1"


def create_app(
    secrets: Optional[dict[str, str]] = None, api_call: Optional[ApiCall] = None
) -> FastAPI:
    state = AttackerState(secrets if secrets is not None else load_manifest())
    api_call = api_call or http_api_call()
    app = FastAPI(title="attacker.test")
    app.state.attacker = state

    def log(session_id: str, data: dict) -> None:
        write_event(
            Event(ts=time.time(), session_id=session_id, source="attacker", kind="received", data=data)
        )

    @app.get("/_truth/{session_id}")
    def truth(session_id: str):
        with state.lock:
            texts, cur, keys = state.texts(session_id), state.current(), list(state.xor_keys)
        return {sid: count_bits(texts, value, keys) for sid, (_, value) in cur.items()}

    @app.put("/_admin/secrets/{secret_id}")
    def set_secret(secret_id: str, body: SecretIn):
        with state.lock:
            state.versions.setdefault(secret_id, []).append((body.version, body.value))
        return {"secret_id": secret_id, "version": body.version}

    @app.put("/_admin/xor_keys")
    def set_xor_keys(body: XorKeysIn):
        with state.lock:
            state.xor_keys = list(body.keys)
        return {"keys": len(body.keys)}

    @app.post("/_admin/cashout/{session_id}")
    def cashout(session_id: str, body: CashoutIn):
        with state.lock:
            texts, keys = state.texts(session_id), list(state.xor_keys)
            versions = list(state.versions.get(body.secret_id, []))
        best = None  # (bits, version, value, positions)
        for version, value in reversed(versions):  # a igualdad de bits gana la más reciente
            r = count_bits(texts, value, keys)
            if r["bits"] > 0 and (best is None or r["bits"] > best[0]):
                best = (r["bits"], version, value, r["positions"])
        if best is None:
            return {"secret_id": body.secret_id, "version": None, "bits_known": 0.0,
                    "completed_by_bruteforce": False, "status": None}
        bits, version, value, positions = best
        H = count_bits([value], value)["bits"]
        brute_forced = can_complete(bits, H)
        if brute_forced:  # simulado: se usa el valor real de esa versión
            key = value
        else:
            known = set(positions)
            key = "".join(c if i in known else "0" for i, c in enumerate(value))
        status = api_call(key)
        result = {"secret_id": body.secret_id, "version": version, "bits_known": bits,
                  "completed_by_bruteforce": brute_forced, "status": status}
        log(session_id, {"cashout": True, **result})
        return result

    @app.api_route(
        "/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
    )
    async def catch_all(path: str, request: Request):
        session_id = request.headers.get(SESSION_HEADER) or "default"
        body = (await request.body()).decode("utf-8", "replace")
        headers = dict(request.headers)
        query = request.url.query
        data = {"method": request.method, "path": "/" + path, "query": query,
                "headers": headers, "body": body}
        with state.lock:
            state.received.setdefault(session_id, []).extend(
                _request_texts(request.method, "/" + path, query, headers, body)
            )
        log(session_id, data)
        return {"ok": True}

    return app


app = create_app()
