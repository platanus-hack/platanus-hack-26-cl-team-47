"""Cliente de la API de la empresa (api.empresa.test) para confirmar reservas."""

import os

import httpx

API_URL = os.environ.get("API_EMPRESA_URL", "https://api.empresa.test/v1")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {os.environ['API_EMPRESA_KEY']}"}


def confirmar_reserva(cliente_id: str, inicio_iso: str) -> dict:
    r = httpx.post(f"{API_URL}/reservas", json={"cliente_id": cliente_id, "inicio": inicio_iso},
                   headers=_headers(), timeout=5)
    r.raise_for_status()
    return r.json()
