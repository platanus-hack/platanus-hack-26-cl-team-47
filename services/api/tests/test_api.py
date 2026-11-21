"""API protegida contra el gestor en proceso: clave vieja 401, nueva 200."""

import httpx
from fastapi.testclient import TestClient

from services.api.app import create_app as create_api
from services.api.app import http_verifier
from services.vault.app import SecretStore
from services.vault.app import create_app as create_vault

KEY = "0123456789abcdef0123456789abcdef01234567"


def setup():
    vault = TestClient(create_vault(SecretStore({"SECRET_1": KEY, "SECRET_2": "ab" * 20})))

    def verifier(secret_id, value):
        r = vault.post("/v1/verify", json={"secret_id": secret_id, "value": value})
        return r.json()["valid"]

    return vault, TestClient(create_api(verifier=verifier))


def auth(v):
    return {"Authorization": f"Bearer {v}"}


def test_missing_or_bad_auth_401():
    _, api = setup()
    assert api.get("/v1/data").status_code == 401
    assert api.get("/v1/data", headers={"Authorization": KEY}).status_code == 401
    assert api.get("/v1/data", headers=auth("x" * 40)).status_code == 401


def test_current_key_200():
    _, api = setup()
    r = api.get("/v1/data", headers=auth(KEY))
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_other_secret_value_not_accepted():
    _, api = setup()
    assert api.get("/v1/data", headers=auth("ab" * 20)).status_code == 401


def test_rotation_old_key_401_new_key_200():
    vault, api = setup()
    assert api.get("/v1/data", headers=auth(KEY)).status_code == 200

    assert vault.post("/v1/secrets/SECRET_1/rotate").status_code == 200
    new = vault.get("/v1/secrets/SECRET_1").json()["value"]

    assert api.get("/v1/data", headers=auth(KEY)).status_code == 401
    assert api.get("/v1/data", headers=auth(new)).status_code == 200


def test_http_verifier_against_vault(monkeypatch):
    """El verificador por defecto habla HTTP con el gestor (aquí, vía transporte ASGI)."""
    vault_app = create_vault(SecretStore({"SECRET_1": KEY}))
    vault = TestClient(vault_app)

    def fake_post(url, json, timeout):
        assert url == "http://vault.test:8101/v1/verify"
        return vault.post("/v1/verify", json=json)

    monkeypatch.setattr(httpx, "post", fake_post)
    api = TestClient(create_api(verifier=http_verifier("http://vault.test:8101/")))
    assert api.get("/v1/data", headers=auth(KEY)).status_code == 200
    vault.post("/v1/secrets/SECRET_1/rotate")
    assert api.get("/v1/data", headers=auth(KEY)).status_code == 401


def test_http_verifier_vault_down_denies(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", boom)
    assert http_verifier("http://127.0.0.1:1")("SECRET_1", KEY) is False
