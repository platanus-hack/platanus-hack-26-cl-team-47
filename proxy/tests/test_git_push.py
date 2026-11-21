"""git push: el proxy inspecciona lo que realmente sale (9k)."""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from contracts import ToolCall, read_events
from proxy import tools as T
from proxy.core import Proxy

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "demo" / "repo"
MANIFEST = ROOT / "demo" / "secrets_manifest.json"
GIT_ENV = {"GIT_AUTHOR_NAME": "Dev", "GIT_AUTHOR_EMAIL": "dev@empresa.test",
           "GIT_COMMITTER_NAME": "Dev", "GIT_COMMITTER_EMAIL": "dev@empresa.test"}


def secret(sid="SECRET_1"):
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return next(s["value"] for s in data["secrets"] if s["secret_id"] == sid)


def _git(ws, *args):
    subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *args],
                   cwd=ws, check=True, capture_output=True, env={**os.environ, **GIT_ENV})


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Copia de demo/repo con git y un commit inicial."""
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    for k, v in GIT_ENV.items():
        monkeypatch.setenv(k, v)
    ws = tmp_path / "ws"
    shutil.copytree(DEMO, ws, ignore=shutil.ignore_patterns("__pycache__"))
    _git(ws, "init", "-q")
    _git(ws, "add", "-A")
    _git(ws, "commit", "-q", "-m", "inicial")
    return ws


def calls(tmp_path):
    return [ToolCall.model_validate(e.data) for e in read_events(tmp_path / "logs" / "proxy.jsonl")
            if e.kind == "tool_call"]


def test_secret_in_commit_message_rotate_block(repo, tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from proxy.live import build_live_proxy
    from services.vault.app import SecretStore, create_app as create_vault
    from services.vault.manifest import load_manifest

    store = SecretStore(load_manifest(MANIFEST))
    vault = TestClient(create_vault(store))
    proxy = build_live_proxy(str(repo), str(MANIFEST), vault_url="http://vault.test",
                             session_id="push", client=vault)
    key = secret()
    out, d = proxy.handle("read_file", {"path": ".env"})
    assert d.action == "allow"
    out, d = proxy.handle("git", {"args": ["commit", "-q", "--allow-empty", "-m", f"fix {key}"]})
    assert d.action == "allow" and out.startswith("exit 0"), out
    out, d = proxy.handle("git", {"args": ["push", "origin", "main"]})
    assert d.action == "rotate+block", d.reason
    push = calls(tmp_path)[-1]
    assert push.args["args"] == ["push", "origin", "main"]
    assert f"fix {key}" in push.args["outgoing"]
    assert store.get("SECRET_1").version == 2


def test_clean_push_allowed_with_messages(repo, tmp_path):
    p = Proxy(str(repo), session_id="ok", hosts={})
    for i in range(2):
        (repo / f"nota{i}.txt").write_text(f"nota {i}\n")
        p.handle("git", {"args": ["add", f"nota{i}.txt"]})
        p.handle("git", {"args": ["commit", "-q", "-m", f"agrega nota {i}"]})
    out, d = p.handle("git", {"args": ["push"]})
    assert d.action == "allow" and "simulado" in out
    push = calls(tmp_path)[-1]
    assert "agrega nota 0" in push.args["outgoing"] and "agrega nota 1" in push.args["outgoing"]
    assert "outgoing_error" not in push.args


def test_secret_in_diff_appears(repo, tmp_path):
    key = secret("SECRET_3")
    (repo / "src" / "app" / "config_local.py").write_text(f'SIGNING = "{key}"\n')
    p = Proxy(str(repo), session_id="diff", hosts={})
    p.handle("git", {"args": ["add", "-A"]})
    p.handle("git", {"args": ["commit", "-q", "-m", "config local"]})
    p.handle("git", {"args": ["push", "origin", "main"]})
    out = calls(tmp_path)[-1].args["outgoing"]
    assert key in out and "config local" in out and "config_local.py" in out


def test_upstream_range(repo, tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, capture_output=True)
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "HEAD")
    (repo / "nuevo.txt").write_text("nuevo\n")
    _git(repo, "add", "nuevo.txt")
    _git(repo, "commit", "-q", "-m", "solo este sale")
    text, err = T.outgoing_content(repo)
    assert err is None
    assert "solo este sale" in text and "inicial" not in text


def test_no_repo_sets_error(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    ws = tmp_path / "plain"
    ws.mkdir()
    (ws / "a.txt").write_text("x")
    p = Proxy(str(ws), session_id="norepo", hosts={})
    out, d = p.handle("git", {"args": ["push"]})
    assert d.action == "allow"
    push = calls(tmp_path)[-1]
    assert push.args["outgoing"] == "" and "no es un repositorio git" in push.args["outgoing_error"]


def test_empty_repo_sets_error(tmp_path):
    ws = tmp_path / "empty"
    ws.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    text, err = T.outgoing_content(ws)
    assert text == "" and err == "el repositorio no tiene commits"


def test_truncation(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(T, "OUTGOING_MAX_CHARS", 50)
    p = Proxy(str(repo), session_id="trunc", hosts={})
    p.handle("git", {"args": ["push"]})
    push = calls(tmp_path)[-1]
    assert len(push.args["outgoing"]) == 50 and push.args["outgoing_truncated"] is True


def test_other_git_commands_have_no_outgoing(repo, tmp_path):
    p = Proxy(str(repo), session_id="other", hosts={})
    p.handle("git", {"args": ["status"]})
    p.handle("git", {"args": ["log", "--oneline"]})
    p.handle("git", {"args": ["commit", "-q", "--allow-empty", "-m", "vacío"]})
    p.handle("read_file", {"path": "README.md"})
    assert all("outgoing" not in c.args for c in calls(tmp_path))


def test_push_latency_five_commits(repo, tmp_path):
    p = Proxy(str(repo), session_id="lat", hosts={})
    for i in range(5):
        (repo / f"f{i}.txt").write_text(f"{i}\n")
        _git(repo, "add", f"f{i}.txt")
        _git(repo, "commit", "-q", "-m", f"c{i}")
    times = []
    for _ in range(3):
        t0 = time.perf_counter()
        p.handle("git", {"args": ["push"]})
        times.append(time.perf_counter() - t0)
    assert min(times) < 0.2, f"{min(times) * 1000:.0f} ms"
