"""Gestor de secretos sintéticos (vault.test), puerto 8101.

    uvicorn services.vault.app:app --port 8101

GET  /v1/secrets/{secret_id}          -> 200 {"secret_id", "value", "version"} | 404
POST /v1/secrets/{secret_id}/rotate   -> 200 {"secret_id", "version", "rotated_at"} | 404
POST /v1/verify  {"secret_id","value"} -> 200 {"valid": bool, "version": int}
"""

from __future__ import annotations

import hmac
import threading
import time
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.vault.manifest import infer_alphabet, load_manifest, random_value


@dataclass
class _Secret:
    value: str
    version: int
    alphabet: str
    rotated_at: float | None = None


class SecretStore:
    """Almacén en memoria. Solo el valor vigente es válido."""

    def __init__(self, initial: dict[str, str]):
        self._lock = threading.Lock()
        self._secrets = {
            sid: _Secret(value=v, version=1, alphabet=infer_alphabet(v))
            for sid, v in initial.items()
        }

    def get(self, secret_id: str) -> _Secret | None:
        with self._lock:
            return self._secrets.get(secret_id)

    def rotate(self, secret_id: str) -> _Secret | None:
        with self._lock:
            s = self._secrets.get(secret_id)
            if s is None:
                return None
            new = s.value
            while new == s.value:
                new = random_value(len(s.value), s.alphabet)
            s.value = new
            s.version += 1
            s.rotated_at = time.time()
            return s

    def verify(self, secret_id: str, value: str) -> tuple[bool, int]:
        with self._lock:
            s = self._secrets.get(secret_id)
            if s is None:
                return False, 0
            ok = hmac.compare_digest(s.value.encode(), str(value).encode())
            return ok, s.version


class VerifyRequest(BaseModel):
    secret_id: str
    value: str


def create_app(store: SecretStore | None = None) -> FastAPI:
    store = store if store is not None else SecretStore(load_manifest())
    app = FastAPI(title="vault.test")
    app.state.store = store

    @app.get("/v1/secrets/{secret_id}")
    def get_secret(secret_id: str):
        s = store.get(secret_id)
        if s is None:
            raise HTTPException(status_code=404, detail="unknown secret")
        return {"secret_id": secret_id, "value": s.value, "version": s.version}

    @app.post("/v1/secrets/{secret_id}/rotate")
    def rotate_secret(secret_id: str):
        s = store.rotate(secret_id)
        if s is None:
            raise HTTPException(status_code=404, detail="unknown secret")
        return {"secret_id": secret_id, "version": s.version, "rotated_at": s.rotated_at}

    @app.post("/v1/verify")
    def verify(req: VerifyRequest):
        valid, version = store.verify(req.secret_id, req.value)
        return {"valid": valid, "version": version}

    return app


app = create_app()
