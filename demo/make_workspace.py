"""Prepara una copia de demo/repo como repositorio git real, con historial determinista.

    python demo/make_workspace.py --out demo/out/workspace [--seed 0]
    AGENT_WORKSPACE=demo/out/workspace PROXY_MODE=live python -m proxy.server

No se versiona un .git anidado: la copia vive en demo/out/ (ignorado por el repo del equipo).
.env y config/secrets.yaml se copian a disco pero quedan fuera de todo commit, como en un
repo real. Misma semilla → mismos SHA.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent
SOURCE = DEMO_DIR / "repo"

AUTHOR_NAME = "Banco de Pruebas"
AUTHOR_EMAIL = "banco@empresa.test"
IGNORED_SECRETS = (".env", "config/secrets.yaml")

# (mensaje, prefijos de ruta). Cada archivo entra en el primer grupo que lo nombra.
GROUPS = (
    ("Estructura inicial del proyecto", ("README.md", "pyproject.toml", ".gitignore")),
    ("Código de la aplicación", ("src/",)),
    ("Tests del módulo de franjas", ("tests/",)),
    ("Configuración de la aplicación", ("config/",)),
    ("Documentación de arquitectura y onboarding", ("docs/arquitectura.md", "docs/onboarding.md")),
    ("Registro del issue 14 sobre franjas", ("docs/issues/",)),
)
REST_MESSAGE = "Archivos restantes del proyecto"


class WorkspaceError(ValueError):
    pass


def _check_out_dir(out: Path) -> None:
    src = SOURCE.resolve()
    if out == src:
        raise WorkspaceError(f"{out} es demo/repo: la copia debe ir a otra carpeta")
    if src.is_relative_to(out):
        raise WorkspaceError(f"{out} contiene demo/repo: borrarla destruiría el original")
    if out.is_relative_to(src):
        raise WorkspaceError(f"{out} está dentro de demo/repo")


def _git_env(date: str | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,  # nada de la configuración del usuario
        GIT_CONFIG_NOSYSTEM="1",
        GIT_TERMINAL_PROMPT="0",
    )
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    return env


def _git(repo: Path, *args: str, date: str | None = None) -> str:
    cmd = [
        "git", "-c", f"user.name={AUTHOR_NAME}", "-c", f"user.email={AUTHOR_EMAIL}",
        "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", "-c", "init.defaultBranch=main",
        *args,
    ]
    res = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, env=_git_env(date))
    if res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falló: {res.stderr.strip()}")
    return res.stdout


def _write_gitignore(repo: Path) -> None:
    path = repo / ".gitignore"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    # El repo del equipo re-incluye .env (!.env) para versionar el original; aquí se ignora.
    lines = [ln for ln in lines if ln.strip() not in {f"!{s}" for s in IGNORED_SECRETS}]
    for s in IGNORED_SECRETS:
        if s not in lines:
            lines.append(s)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _tracked_files(repo: Path) -> list[str]:
    out = _git(repo, "ls-files", "--others", "--exclude-standard")
    return sorted(p for p in out.splitlines() if p)


def make_workspace(out_dir: str, seed: int = 0) -> Path:
    out = Path(out_dir).resolve()
    _check_out_dir(out)
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, out, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".git"))
    _write_gitignore(out)

    _git(out, "init", "-q", "-b", "main")
    pending = _tracked_files(out)
    base = datetime(2026, 1, 5, 9, 0, tzinfo=timezone(timedelta(hours=-3))) + timedelta(days=seed)
    commits = 0
    for message, prefixes in (*GROUPS, (REST_MESSAGE, ("",))):
        files = [f for f in pending if any(f == p or f.startswith(p) for p in prefixes)]
        if not files:
            continue
        pending = [f for f in pending if f not in files]
        date = (base + timedelta(hours=3 * commits)).isoformat()
        _git(out, "add", "--", *files)
        _git(out, "commit", "-q", "-m", message, date=date)
        commits += 1
    if not 5 <= commits <= 8:
        raise RuntimeError(f"se esperaban entre 5 y 8 commits y salieron {commits}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="demo/out/workspace")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    out = make_workspace(a.out, a.seed)
    print(_git(out, "log", "--oneline").rstrip())
    print(f"\nWorkspace listo en {out}\nUso: AGENT_WORKSPACE={a.out} PROXY_MODE=live python -m proxy.server")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
