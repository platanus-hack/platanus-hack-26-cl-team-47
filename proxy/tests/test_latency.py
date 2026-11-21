"""Latencia del proxy en vivo (documento v4.0, sección 6.3): p95 de Decision.latency_ms < 15 ms."""

import random
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from proxy.live import build_live_proxy  # noqa: E402
from services.vault.app import SecretStore, create_app as create_vault  # noqa: E402
from services.vault.manifest import load_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "demo" / "repo"
MANIFEST = ROOT / "demo" / "secrets_manifest.json"
P95_MS = 15.0


def test_live_p95_latency(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    vault = TestClient(create_vault(SecretStore(load_manifest(MANIFEST))))
    proxy = build_live_proxy(str(WORKSPACE), str(MANIFEST), vault_url="http://vault.test",
                             session_id="lat", client=vault)
    files = sorted(p.relative_to(WORKSPACE).as_posix() for p in WORKSPACE.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts)
    dirs = [".", "docs", "src/app", "config", "tests"]
    rng = random.Random(0)
    steps = []
    for _ in range(300):
        steps.append(("read_file", {"path": rng.choice(files)}) if rng.random() < 0.8
                     else ("list_dir", {"path": rng.choice(dirs)}))
    for i in range(20):
        url = rng.choice(["http://api.empresa.test/v1/data", f"http://attacker.test/ping?n={i}",
                          f"http://web.test/page/{i}"])
        steps.insert(rng.randint(0, len(steps)), ("http_request", {"method": "GET", "url": url}))

    lat = [proxy.handle(tool, args)[1].latency_ms for tool, args in steps]
    p95 = float(np.percentile(lat, 95))
    print(f"\nlatencia en vivo: n={len(lat)} p50={np.percentile(lat, 50):.2f} ms p95={p95:.2f} ms max={max(lat):.2f} ms")
    assert len(lat) == 320
    assert p95 < P95_MS, f"p95 = {p95:.2f} ms"
