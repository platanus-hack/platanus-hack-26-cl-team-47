"""La evaluación con las banderas que calcula el proxy (#167). Análisis aparte, con el detector congelado.

    python -m eval.final.proxy_flags --out results/proxy_flags [--split test]

El «180 de 180» de results/test/ se midió con las banderas is_sink y untrusted que escribió el generador de
los ataques (redteam/sealed.py). El proxy en vivo las calcula con proxy.core.is_sink y proxy.core.untrusted.
Este comando corre los mismos sistemas sobre tres variantes de las mismas sesiones:

  grabadas     las sesiones tal como están (reproduce results/test/systems.json)
  proxy        cada ToolCall con is_sink y untrusted calculados como el proxy; nada más cambia
  proxy_push   como proxy, y cada `git push` lleva args["outgoing"], como en vivo (Proxy._call_args): en una
               grabación no hay repositorio, así que es la unión de los mensajes -m de los `git commit`
               anteriores de la sesión desde el push anterior

Sistemas: los nueve de eval.final.run y taint_rule (regla simple, eval/baselines/taint_rule.py).
Salidas: systems.json, systems.md, changes.json y RUN.json. Se puede repetir; no lleva candado.
"""

from __future__ import annotations

import argparse
import datetime
import json
from collections import Counter
from pathlib import Path
from typing import Iterable

from engine.detector import make_frozen
from eval.baselines import taint_rule
from eval.replay.core import replay
from proxy.core import is_sink, untrusted
from proxy.tools import url_host

from . import run as R

VARIANTS = ("grabadas", "proxy", "proxy_push")
SYSTEMS = (*R.SYSTEMS, "taint_rule")
TAINT_DESCRIPTION = ("Línea de base: regla simple, «leyó un secreto (su valor completo en una salida) y esta llamada "
                     "sale hacia un destino no confiable»: rota lo leído; nunca bloquea.")


# --------------------------------------------------------------------------- variantes

def _git_sub(args: dict) -> str:
    return next((a for a in (args or {}).get("args") or [] if isinstance(a, str) and not a.startswith("-")), "")


def _commit_message(args: dict) -> str | None:
    a = list((args or {}).get("args") or [])
    for i, x in enumerate(a):
        if x == "-m" and i + 1 < len(a):
            return str(a[i + 1])
    return None


def with_proxy_flags(session: list, push_outgoing: bool = False) -> list:
    """La sesión con las banderas del proxy (y, si se pide, el outgoing de cada push)."""
    out, pending = [], []
    for c in sorted(session, key=lambda c: c.t):
        args = dict(c.args or {})
        if push_outgoing and c.tool == "git":
            sub = _git_sub(args)
            if sub == "commit":
                msg = _commit_message(args)
                if msg is not None:
                    pending.append(msg)
            elif sub == "push":
                args["outgoing"] = "\n".join(pending)
                pending = []
        out.append(c.model_copy(update={"is_sink": is_sink(c.tool, args), "untrusted": untrusted(c.tool, args),
                                         "args": args}))
    return out


def variant(sessions: list[list], name: str) -> list[list]:
    if name == "grabadas":
        return sessions
    return [with_proxy_flags(s, push_outgoing=(name == "proxy_push")) for s in sessions]


def _where(c) -> str:
    if c.tool == "git":
        return _git_sub(c.args)
    if c.tool == "http_request":
        return url_host(str((c.args or {}).get("url", "")))
    if c.tool in ("github_issue", "github_comment"):
        return "github.test"
    return ""


def flag_changes(before: Iterable[list], after: Iterable[list]) -> dict:
    """Cuántas llamadas cambian de banderas, por (label, tool, host o subcomando de git, antes -> después)."""
    counts: Counter = Counter()
    total = 0
    for sb, sa in zip(before, after):
        for b, a in zip(sorted(sb, key=lambda c: c.t), sorted(sa, key=lambda c: c.t)):
            total += 1
            fb, fa = f"{int(b.is_sink)}{int(b.untrusted)}", f"{int(a.is_sink)}{int(a.untrusted)}"
            if fb != fa:
                counts[(b.label or "", b.tool, _where(b), f"{fb} -> {fa}")] += 1
    rows = [{"label": k[0], "tool": k[1], "where": k[2], "flags": k[3], "calls": n}
            for k, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    return {"calls": total, "changed": sum(counts.values()), "by": rows,
            "flags_legend": "dos dígitos: is_sink y untrusted (1 = sí)"}


# --------------------------------------------------------------------------- sistemas

def run_taint_rule(units, secrets) -> list:
    values, _ = R._manifest()
    events: list = []
    for _, sess in units:
        for s in sess:
            sec = {**values, **(secrets.get(s[0].session_id) or {})}
            events += replay([s], lambda sec=sec: taint_rule.make_decide(secrets=sec), emit_rotations=True)
    return events


def evaluate(sessions, labels, secrets, frozen, systems=SYSTEMS, n_boot: int = 2000) -> list[dict]:
    units = R.make_units(sessions, labels)
    rows = []
    for name in systems:
        events = run_taint_rule(units, secrets) if name == "taint_rule" else R.run_system(name, units, secrets, frozen)
        rows.append(R.system_row(name, R.summarize(events, labels, n_boot=n_boot)))
    return rows


# --------------------------------------------------------------------------- tablas

def _prevented(row: dict) -> str:
    n = row["n_attack_units"]
    k = round((row["prevented_rate"] or 0.0) * n)
    return f"{k} de {n}"


def summary_markdown(by_variant: dict[str, list[dict]]) -> str:
    names = [r["system"] for r in by_variant["grabadas"]]
    lines = ["| Sistema | Grabadas | Banderas del proxy | Banderas del proxy e inspección del push |",
             "|---|---|---|---|"]
    for i, name in enumerate(names):
        lines.append(f"| {name} | " + " | ".join(_prevented(by_variant[v][i]) for v in VARIANTS) + " |")
    return "\n".join(lines) + "\n"


def full_markdown(by_variant: dict[str, list[dict]], split: str) -> str:
    title = {"grabadas": "Grabadas (las banderas del generador)", "proxy": "Banderas del proxy",
             "proxy_push": "Banderas del proxy e inspección del push"}
    parts = [f"# Evaluación con las banderas del proxy · set `{split}`", "",
             "Análisis aparte, con el detector congelado. Ataques prevenidos en cada variante:", "",
             summary_markdown(by_variant)]
    for v in VARIANTS:
        md = R.systems_markdown(by_variant[v]).replace("- `taint_rule`: ", f"- `taint_rule`: {TAINT_DESCRIPTION}")
        parts += [f"## {title[v]}", "", md]
    return "\n".join(parts)


# --------------------------------------------------------------------------- comando

def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(prog="python -m eval.final.proxy_flags")
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="test", choices=["val", "test"])
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--benign", default="data/benign/sessions", help=argparse.SUPPRESS)
    ap.add_argument("--redteam", default="redteam", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    R.safe_console()

    frozen = make_frozen()
    sessions, labels, secrets = R.load_split(args.split, args.benign, args.redteam)
    by_variant = {}
    for v in VARIANTS:
        by_variant[v] = evaluate(variant(sessions, v), labels, secrets, frozen, n_boot=args.n_boot)
        print(f"{v}: " + ", ".join(f"{r['system']} {_prevented(r)}" for r in by_variant[v]), flush=True)
    changes = flag_changes(sessions, variant(sessions, "proxy"))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    R._write_json(out / "systems.json", by_variant)
    R._write_json(out / "changes.json", changes)
    (out / "systems.md").write_text(full_markdown(by_variant, args.split), encoding="utf-8", newline="\n")
    R._write_json(out / "RUN.json", {**R._git_commit(), "split": args.split, "frozen_hash": frozen.frozen.get("hash"),
                                     "params": frozen.frozen.get("params"), "model_sha256": frozen.frozen.get("model_sha256"),
                                     "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
    print(summary_markdown(by_variant))
    print(f"Cambian de banderas {changes['changed']} de {changes['calls']} llamadas -> {out}")
    return {"by_variant": by_variant, "changes": changes}


if __name__ == "__main__":
    main()
