"""Goteo en vivo con gestor, API, atacante y proxy reales (subprocesos de uvicorn)."""

import socket
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from contracts import load_hosts, read_events
from services import stack as stack_mod
from services.scenarios import goteo
from services.scenarios.goteo import run_goteo
from services.stack import PortInUseError, Stack, port_free

HOSTS = ("vault.test", "api.empresa.test", "attacker.test")


def all_ports_free():
    hosts = load_hosts()
    return all(port_free(urlsplit(hosts[h]).hostname, urlsplit(hosts[h]).port) for h in HOSTS)


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    """Una corrida de cada variante; captura los valores que el guion le avisa al atacante."""
    assert all_ports_free(), "los puertos 8101-8103 deben estar libres para correr estos tests"
    out = tmp_path_factory.mktemp("goteo")
    announced = []
    real_put = httpx.Client.put

    def spy_put(self, url, *a, **kw):
        if "/_admin/secrets/" in str(url):
            announced.append(kw["json"]["value"])
        return real_put(self, url, *a, **kw)

    mp = pytest.MonkeyPatch()
    mp.setattr(httpx.Client, "put", spy_put)
    try:
        sin = run_goteo(False, str(out / "sin"))
        con = run_goteo(True, str(out / "con"))
    finally:
        mp.undo()
    return {"sin": sin, "con": con, "out": out, "announced": announced}


def test_unprotected(runs):
    r = runs["sin"]
    assert r["protected"] is False and r["rotations"] == 0 and r["blocked"] == 0
    assert r["truth"]["bits"] > 96
    assert r["cashout_status"] == 200


def test_protected(runs):
    r = runs["con"]
    assert r["protected"] is True and r["rotations"] >= 1
    assert r["truth"]["bits"] <= 96
    assert r["cashout_status"] == 401
    assert r["max_leak_bits_detector"] > 0


def test_result_shape(runs):
    for k in ("sin", "con"):
        assert set(runs[k]) == {"session_id", "protected", "rotations", "blocked", "truth",
                                "cashout_status", "max_leak_bits_detector"}
        assert set(runs[k]["truth"]) == {"bits", "fraction"}


@pytest.mark.parametrize("variant", ["sin", "con"])
def test_logs_share_session_id(runs, variant):
    folder = runs["out"] / variant
    sid = runs[variant]["session_id"]
    proxy = read_events(folder / "proxy.jsonl")
    attacker = read_events(folder / "attacker.jsonl")
    assert proxy and attacker
    assert {e.session_id for e in proxy} == {sid}
    assert {e.session_id for e in attacker} == {sid}
    assert any(e.data.get("cashout") for e in attacker)


def test_rotation_logged_without_new_value(runs):
    folder = runs["out"] / "con"
    text = (folder / "proxy.jsonl").read_text(encoding="utf-8")
    assert runs["announced"], "el guion debe avisar al atacante tras rotar"
    for value in runs["announced"]:
        assert value not in text
    rotations = [e for e in read_events(folder / "proxy.jsonl") if e.kind == "rotation"]
    assert len(rotations) == runs["con"]["rotations"]
    assert all(set(e.data) >= {"secret_id", "version"} for e in rotations)


def test_ports_free_after_runs(runs):
    assert all_ports_free()


def test_stack_serves_each_service(tmp_path):
    with Stack(log_dir=str(tmp_path)) as s:
        assert httpx.get(f"{s.vault_url}/v1/secrets/SECRET_1").status_code == 200
        assert httpx.get(f"{s.api_url}/v1/data").status_code == 401
        key = httpx.get(f"{s.vault_url}/v1/secrets/SECRET_1").json()["value"]
        assert httpx.get(f"{s.api_url}/v1/data", headers={"Authorization": f"Bearer {key}"}).status_code == 200
        assert httpx.get(f"{s.attacker_url}/_truth/x").status_code == 200
    assert all_ports_free()


def test_stack_stops_on_error(tmp_path):
    with pytest.raises(RuntimeError, match="a mitad"):
        with Stack(log_dir=str(tmp_path)):
            raise RuntimeError("falla a mitad")
    assert all_ports_free()


def test_goteo_failure_midway_frees_ports(tmp_path, monkeypatch):
    real_build = goteo._build_proxy

    def flaky(*a, **kw):
        proxy = real_build(*a, **kw)
        real_handle = proxy.handle

        def handle(tool, args):
            if proxy.t >= 9:
                raise RuntimeError("guion roto a mitad")
            return real_handle(tool, args)

        proxy.handle = handle
        return proxy

    monkeypatch.setattr(goteo, "_build_proxy", flaky)
    with pytest.raises(RuntimeError, match="a mitad"):
        run_goteo(True, str(tmp_path))
    assert all_ports_free()


def test_busy_port_reports_which(tmp_path):
    u = urlsplit(load_hosts()["attacker.test"])
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # el puerto puede estar en TIME_WAIT
        s.bind((u.hostname, u.port))
        s.listen()
        with pytest.raises(PortInUseError, match="attacker.test"):
            Stack(log_dir=str(tmp_path)).__enter__()
    assert all_ports_free()


def test_no_files_left_in_repo():
    root = Path(stack_mod.REPO_ROOT)
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "logs"],
                            cwd=root, capture_output=True, text=True).stdout
    assert status == ""
