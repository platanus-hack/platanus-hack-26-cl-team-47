"""demo/make_workspace.py: copia de demo/repo como repo git real (todo sobre tmp_path)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "demo"))
import make_workspace as mw  # noqa: E402


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


def team_status():
    return git(ROOT, "status", "--short", "--untracked-files=all", "demo")


@pytest.fixture(scope="module")
def ws(tmp_path_factory):
    before = team_status()
    out = mw.make_workspace(str(tmp_path_factory.mktemp("w") / "workspace"))
    yield out
    assert team_status() == before


def test_between_5_and_8_commits_and_clean_tree(ws):
    commits = git(ws, "log", "--oneline").splitlines()
    assert 5 <= len(commits) <= 8
    assert git(ws, "status", "--short") == ""
    assert git(ws, "rev-parse", "--abbrev-ref", "HEAD").strip() == "main"
    people = set(git(ws, "log", "--format=%an <%ae>%n%cn <%ce>").splitlines())
    assert people == {"Banco de Pruebas <banco@empresa.test>"}


def test_same_seed_same_head(tmp_path, ws):
    a = mw.make_workspace(str(tmp_path / "a"), seed=0)
    b = mw.make_workspace(str(tmp_path / "b"), seed=0)
    c = mw.make_workspace(str(tmp_path / "c"), seed=1)
    head = lambda r: git(r, "rev-parse", "HEAD").strip()  # noqa: E731
    assert head(a) == head(b) == head(ws)
    assert head(c) != head(a)


def test_secrets_on_disk_but_not_tracked(ws):
    tracked = git(ws, "ls-files").splitlines()
    assert ".env" not in tracked and "config/secrets.yaml" not in tracked
    assert (ws / ".env").is_file() and (ws / "config" / "secrets.yaml").is_file()


def test_no_secret_value_in_history(ws):
    manifest = json.loads((ROOT / "demo" / "secrets_manifest.json").read_text(encoding="utf-8"))
    history = git(ws, "log", "-p", "--all")
    for s in manifest["secrets"]:
        assert s["value"] not in history


def test_refuses_demo_repo_and_ancestors(tmp_path):
    before = team_status()
    for bad in (ROOT / "demo" / "repo", ROOT / "demo", ROOT, ROOT / "demo" / "repo" / "sub"):
        with pytest.raises(mw.WorkspaceError):
            mw.make_workspace(str(bad))
    assert (ROOT / "demo" / "repo" / "README.md").exists()
    assert not (ROOT / "demo" / "repo" / ".git").exists()
    assert team_status() == before


def test_rerun_replaces_only_out_dir(tmp_path):
    out = tmp_path / "w"
    mw.make_workspace(str(out))
    (out / "basura.txt").write_text("x")
    sibling = tmp_path / "vecino.txt"
    sibling.write_text("se queda")
    mw.make_workspace(str(out))
    assert not (out / "basura.txt").exists() and sibling.read_text() == "se queda"


def test_proxy_git_log_works_on_copy(ws, tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    from proxy.core import Proxy

    output, decision = Proxy(workspace=str(ws)).handle("git", {"args": ["log", "--oneline"]})
    assert decision.allowed
    assert "Estructura inicial del proyecto" in output
    assert "128" not in output.splitlines()[0]


def test_rerun_with_read_only_files(tmp_path):
    """Como en Windows: archivos de solo lectura (los objetos de git) no impiden rehacer la copia."""
    import os
    import stat
    out = tmp_path / "w"
    mw.make_workspace(str(out))
    for p in (out / ".git" / "objects").rglob("*"):
        if p.is_file():
            os.chmod(p, stat.S_IREAD)
    (out / "solo_lectura.txt").write_text("x")
    os.chmod(out / "solo_lectura.txt", stat.S_IREAD)
    mw.make_workspace(str(out))
    assert not (out / "solo_lectura.txt").exists()
    assert 5 <= len(git(out, "log", "--oneline").splitlines()) <= 8
