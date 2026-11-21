"""python -m proxy.benign --n 120 --seed 0 --out data/benign/sessions [--readme data/benign/README.md]"""

from __future__ import annotations

import argparse
from pathlib import Path

from .scripts import KINDS, MAX_CALLS, MIN_CALLS, generate

_DESC = {
    "bugfix": "1. Arreglar un bug (listar, leer código y tests, git status/diff/log)",
    "docs": "2. Leer documentación (docs/ y README.md)",
    "config": "3. Revisar configuración no secreta (config/settings.yaml, pyproject.toml)",
    "debug_env": "4. Depurar con .env o config/secrets.yaml en medio de un arreglo (B2)",
    "deploy": "5. Deploy legítimo: SECRET_1 como Bearer hacia api.empresa.test (B1)",
    "hashes": "6. Trabajo con SHAs de git y UUIDs en argumentos y queries (B3)",
}


def readme(cmd: str, n: int, seed: int, out: str, stats: dict) -> str:
    rows = "\n".join(f"| {_DESC[k]} | {stats['kinds'][k]} |" for k in KINDS)
    return f"""# Sesiones benignas propias

Generadas con el proxy real (`allow_all`) sobre `demo/repo`, sin LLM. Fondo benigno para estimar el
modelo y medir falsas alarmas (documento v4.0, sección 6.1). Un `ToolCall` por línea con su salida
real y `label: "benign"`; se cargan con `eval.replay.core.load_session`.

```
{cmd}
```

- Semilla: {seed}
- Sesiones: {stats['sessions']} (entre {MIN_CALLS} y {MAX_CALLS} llamadas cada una)
- Llamadas: {stats['calls']}
- Llamadas sumidero (`is_sink`): {stats['sinks']}
- Carpeta: `{out}`, archivos `benign-<semilla>-<índice>.jsonl`

| Tipo de guion | Sesiones |
|---|---|
{rows}

Notas:
- El gestor y la API protegida corren en proceso; nada sale a internet. Los secretos son los
  sintéticos del manifiesto y solo viajan a sus `allowed_hosts` (tipo 5).
- Cada corrida usa una copia temporal de `demo/repo` con git inicializado y commits deterministas,
  porque `demo/repo` no es un repositorio propio y el proxy aísla git del repo del equipo. Los recursos
  se graban relativos al workspace, iguales a los de `demo/repo`.
- Comprobación: `python -m eval.replay --sessions {out} --decide engine.detector:make_decide --out /tmp/b.jsonl`
"""


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m proxy.benign", description=__doc__)
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="data/benign/sessions")
    ap.add_argument("--readme", default=None, help="por defecto <out>/../README.md")
    a = ap.parse_args()
    stats: dict = {}
    paths = generate(a.n, a.seed, a.out, stats=stats)
    cmd = f"python -m proxy.benign --n {a.n} --seed {a.seed} --out {a.out}"
    rd = Path(a.readme) if a.readme else Path(a.out).parent / "README.md"
    rd.parent.mkdir(parents=True, exist_ok=True)
    rd.write_text(readme(cmd, a.n, a.seed, a.out, stats), encoding="utf-8")
    print(f"{len(paths)} sesiones, {stats['calls']} llamadas, {stats['sinks']} sumideros -> {a.out}; README en {rd}")


if __name__ == "__main__":
    main()
