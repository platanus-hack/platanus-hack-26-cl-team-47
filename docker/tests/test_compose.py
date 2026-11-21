"""Validación de la red aislada sin necesitar Docker (y con Docker si está instalado)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
DOCKER = ROOT / "docker"
COMPOSE = DOCKER / "compose.yml"
SERVICES = {"vault", "api", "attacker", "proxy"}
ALIASES = {"vault": "vault.test", "api": "api.empresa.test", "attacker": "attacker.test"}


@pytest.fixture(scope="module")
def compose():
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def _networks(svc):
    nets = svc.get("networks", {})
    return nets if isinstance(nets, dict) else {n: {} for n in nets}


def test_four_services(compose):
    assert SERVICES <= set(compose["services"])


def test_internal_network(compose):
    assert compose["networks"]["banco"]["internal"] is True
    for name in SERVICES:
        assert "banco" in _networks(compose["services"][name]), name


def test_only_published_services_leave_banco(compose):
    """Solo api y attacker (por sus puertos) están en otra red; proxy y vault solo en banco."""
    for name in ("vault", "proxy"):
        assert set(_networks(compose["services"][name])) == {"banco"}, name
    for name, svc in compose["services"].items():
        extra = set(_networks(svc)) - {"banco"}
        if extra:
            assert svc.get("ports"), f"{name} sale de banco sin publicar puertos"
            for net in extra:
                assert not compose["networks"][net].get("internal"), net


def test_aliases(compose):
    for name, alias in ALIASES.items():
        banco = _networks(compose["services"][name])["banco"] or {}
        assert alias in banco.get("aliases", []), name


def test_ports_only_on_localhost(compose):
    published = {}
    for name, svc in compose["services"].items():
        for p in svc.get("ports", []):
            spec = p if isinstance(p, str) else f"{p.get('host_ip', '')}:{p.get('published')}:{p.get('target')}"
            assert spec.startswith("127.0.0.1:"), (name, spec)
            published[name] = spec
    assert published == {"api": "127.0.0.1:8102:8102", "attacker": "127.0.0.1:8103:8103"}


def test_commands_and_env(compose):
    s = compose["services"]
    assert s["vault"]["command"][:2] == ["uvicorn", "services.vault.app:app"] and "8101" in s["vault"]["command"]
    assert s["api"]["command"][:2] == ["uvicorn", "services.api.app:app"] and "8102" in s["api"]["command"]
    assert s["attacker"]["command"][:2] == ["uvicorn", "services.attacker.app:app"]
    assert s["api"]["environment"]["VAULT_URL"] == "http://vault.test:8101"
    assert s["proxy"]["command"] == ["sleep", "infinity"]
    assert s["proxy"]["environment"]["PROXY_MODE"] == "live"
    for name in SERVICES:
        env = s[name]["environment"]
        assert env["LOG_DIR"] == "/logs" and env["SECRETS_MANIFEST"] == "demo/secrets_manifest.json"
        assert "logs:/logs" in s[name]["volumes"]
        assert "./hosts.docker.json:/app/contracts/hosts.json:ro" in s[name]["volumes"]
    assert "logs" in compose["volumes"]


def test_hosts_docker_matches_contracts():
    ours = json.loads((DOCKER / "hosts.docker.json").read_text(encoding="utf-8"))
    base = json.loads((ROOT / "contracts" / "hosts.json").read_text(encoding="utf-8"))
    assert set(ours) == set(base)
    for host, url in ours.items():
        assert url == f"http://{host}:{base[host].rsplit(':', 1)[1]}"


def test_dockerignore():
    lines = {l.strip() for l in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()}
    for pat in (".env", ".git", "logs/", "demo/out/", ".venv/", ".board/", ".claude/"):
        assert pat in lines, pat
    assert any("__pycache__" in l for l in lines)


def test_dockerfile():
    text = (DOCKER / "Dockerfile").read_text(encoding="utf-8")
    assert [l for l in text.splitlines() if l.startswith("FROM ")] == ["FROM python:3.12-slim"]
    for req in ("contracts", "services", "proxy", "proxy/agent", "engine", "engine/graph"):
        assert f"-r {req}/requirements.txt" in text, req
        assert (ROOT / req / "requirements.txt").exists(), req


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker no está instalado")
def test_docker_compose_config():
    r = subprocess.run(["docker", "compose", "-f", str(COMPOSE), "config", "-q"],
                       cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
