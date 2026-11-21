"""API protegida (api.empresa.test), puerto 8102.

    uvicorn services.api.app:app --port 8102

GET /v1/data  con  Authorization: Bearer <valor>  -> 200 {"ok": true} | 401

La clave es la vigente del secreto API_SECRET_ID (por defecto SECRET_1). Se valida
contra el gestor (VAULT_URL, por defecto http://127.0.0.1:8101) en cada petición.
"""

from __future__ import annotations

import os
from typing import Callable

import httpx
from fastapi import FastAPI, Header, HTTPException

Verifier = Callable[[str, str], bool]


def http_verifier(vault_url: str | None = None, timeout: float = 2.0) -> Verifier:
    base = (vault_url or os.environ.get("VAULT_URL", "http://127.0.0.1:8101")).rstrip("/")

    def verify(secret_id: str, value: str) -> bool:
        try:
            r = httpx.post(
                f"{base}/v1/verify",
                json={"secret_id": secret_id, "value": value},
                timeout=timeout,
            )
            return r.status_code == 200 and bool(r.json().get("valid"))
        except httpx.HTTPError:
            return False  # sin gestor no se autoriza nada

    return verify


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def create_app(verifier: Verifier | None = None, secret_id: str | None = None) -> FastAPI:
    verifier = verifier or http_verifier()
    secret_id = secret_id or os.environ.get("API_SECRET_ID", "SECRET_1")
    app = FastAPI(title="api.empresa.test")

    @app.get("/v1/data")
    def data(authorization: str | None = Header(default=None)):
        token = _bearer(authorization)
        if token is None or not verifier(secret_id, token):
            raise HTTPException(
                status_code=401,
                detail="invalid or expired key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"ok": True}

    return app


app = create_app()
