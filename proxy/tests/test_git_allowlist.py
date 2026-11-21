"""Herramienta git del proxy: lista de subcomandos permitidos (#137)."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from proxy import tools as T
from proxy.core import Proxy

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "demo" / "repo"
GIT_ENV = {"GIT_AUTHOR_NAME": "Dev", "GIT_AUTHOR_EMAIL": "dev@empresa.test",
           "GIT_COMMITTER_NAME": "Dev", "GIT_COMMITTER_EMAIL": "dev@empresa.test"}


def _git(ws, *args):
    subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *args],
                   cwd=ws, check=True, capture_output=True, env={**os.environ, **GIT_ENV})


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    for k, v in GIT_ENV.items():
        monkeypatch.setenv(k, v)
    ws = tmp_path / "ws"
    shutil.copytree(DEMO, ws, ignore=shutil.ignore_patterns("__pycache__"))
    _git(ws, "init", "-q")
    _git(ws, "add", "-A")
    _git(ws, "commit", "-q", "-m", "inicial")
    return ws


def run(ws, args):
    out, _ = Proxy(str(ws)).handle("git", {"args": args})
    return out


def test_alias_con_comando_se_rechaza_sin_ejecutar(repo, tmp_path):
    marca = tmp_path / "pwned"
    out = run(repo, ["config", "alias.x", f"!touch {marca}"])
    assert out.startswith("ERROR: argumento de git no permitido")
    assert run(repo, ["x"]).startswith("ERROR")
    assert not marca.exists()
    # el alias no quedó escrito en el repo
    r = subprocess.run(["git", "config", "--get-regexp", "^alias"], cwd=repo, capture_output=True, text=True)
    assert r.stdout.strip() == ""


@pytest.mark.parametrize("args", [
    ["-c", "alias.x=!touch /tmp/nunca", "x"],
    ["-calias.x=!touch /tmp/nunca", "x"],
    ["--config-env=alias.x=X", "x"],
    ["log", "--ext-diff"], ["diff", "--textconv"], ["log", "-o", "/tmp/x"], ["show", "--output=/tmp/x"],
    ["fetch", "--upload-pack=touch /tmp/x"], ["fetch", "-u", "upload-pack"], ["push", "--receive-pack=x"],
    ["log", "--exec=touch"], ["status", "!x"], ["--exec-path=/tmp", "status"],
    ["submodule", "update"], ["filter-branch"], ["bisect", "start"], ["daemon"], ["archive", "HEAD"],
    ["bundle", "create", "x"], ["clone", "http://x"], ["init"], ["worktree", "add", "x"], ["gc"],
    ["remote", "add", "o", "http://x"], ["remote", "set-url", "origin", "http://x"], [],
])
def test_rechazos(repo, args):
    assert run(repo, args).startswith("ERROR")


def test_permitidos_siguen_funcionando(repo):
    (repo / "nota.txt").write_text("hola\n", encoding="utf-8")
    assert run(repo, ["status"]).startswith("exit 0")
    assert run(repo, ["add", "nota.txt"]).startswith("exit 0")
    assert run(repo, ["commit", "-q", "-m", "nota"]).startswith("exit 0")
    assert "nota" in run(repo, ["log", "--oneline", "-1"])
    assert run(repo, ["diff", "HEAD~1", "--stat"]).startswith("exit 0")
    assert "nota" in run(repo, ["show", "--stat", "HEAD"])
    assert run(repo, ["cat-file", "-t", "HEAD"]).startswith("exit 0")
    assert "simulado" in run(repo, ["push", "origin", "main"])
    assert "simulado" in run(repo, ["remote", "-v"])
    assert "simulado" in run(repo, ["remote", "get-url", "origin"])


def test_repo_con_alias_se_rechaza(repo, tmp_path):
    _git(repo, "config", "alias.st", "status")
    out = run(repo, ["status"])
    assert out == "ERROR: el repositorio define alias de git; no se ejecuta"


def test_configuracion_global_no_entra(tmp_path, repo, monkeypatch):
    """Un alias o un pager en la configuración global no se aplica."""
    glob = tmp_path / "global.gitconfig"
    glob.write_text("[core]\n\tpager = touch " + str(tmp_path / "pager") + "\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(glob))
    env = T._git_env(repo)
    assert env["GIT_CONFIG_GLOBAL"] == os.devnull and env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert run(repo, ["log", "-1"]).startswith("exit 0")
    assert not (tmp_path / "pager").exists()


@pytest.mark.parametrize("args,sink", [
    (["push", "origin", "main"], True), (["fetch"], True), (["pull", "origin", "main"], True),
    (["status"], False), (["log", "--oneline"], False), (["diff"], False),
])
def test_sumideros(args, sink):
    assert Proxy._is_sink("git", {"args": args}) is sink


def _old_git(workspace, args):
    """La herramienta git de main antes de #137 (sin lista de permitidos ni configuración anulada)."""
    for a in args:
        if a in ("-C", "-c") or a.startswith(("--git-dir", "--work-tree", "--exec-path", "--upload-pack",
                                              "--receive-pack", "--config")):
            raise T.ToolError(f"argumento de git no permitido: {a}")
    sub = next((a for a in args if not a.startswith("-")), "")
    if sub in T.NETWORK_SUBCOMMANDS:
        return f"exit 0\n{sub} simulado (sin red): {' '.join(args)}"
    root = Path(workspace).resolve()
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_CEILING_DIRECTORIES": str(root.parent)}
    res = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8",
                         errors="replace", timeout=T.GIT_TIMEOUT_S, env=env)
    out = res.stdout + (("\n" + res.stderr) if res.stderr else "")
    return f"exit {res.returncode}\n{out}".rstrip()


def test_benign_produce_las_mismas_llamadas(tmp_path, monkeypatch):
    """python -m proxy.benign --n 3 --seed 0 da las mismas llamadas con el código nuevo y con el de main."""
    from proxy.benign import generate
    new = generate(3, seed=0, out_dir=str(tmp_path / "nuevo"))
    monkeypatch.setattr(T, "git", _old_git)
    old = generate(3, seed=0, out_dir=str(tmp_path / "main"))
    assert len(new) == 3
    for a, b in zip(new, old):
        assert a.read_bytes() == b.read_bytes(), a.name
    # y el CLI escribe lo mismo
    cli = tmp_path / "cli"
    subprocess.run([sys.executable, "-m", "proxy.benign", "--n", "3", "--seed", "0", "--out", str(cli)],
                   cwd=ROOT, check=True, capture_output=True)
    for a in new:
        assert (cli / a.name).read_bytes() == a.read_bytes(), a.name
