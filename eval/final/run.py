"""Comando único de la evaluación final con la configuración congelada (#133, paso 14b).

    python -m eval.final.run --split val  --out results/val     # se puede repetir
    python -m eval.final.run --split test --out results/test    # lo corre el orquestador, UNA vez

Pasos (iguales para val y test):
  a. Sesiones: benignas de data/benign/sessions que caen en esa parte (split_sessions, semilla 0, mismo
     cálculo que eval.search) y todas las de redteam/<split>/sessions, con sus labels y secrets.
  b. Unidades: las sesiones cuyas etiquetas traen el mismo `group` forman una unidad (comparten secreto);
     el resto son unidades de una sesión. Dentro de una unidad se reproducen en orden de session_id.
  c. Nueve sistemas, cada uno escribe events_<sistema>.jsonl (no se versionan):
     ours (congelado, un SharedLedger por unidad), no_rotation (ours con rotation_enabled=False),
     per_session (congelado sin ledger), no_evidence (ours sin modelo de evidencia) y las líneas de base allowlist, detect_secrets, combined, budget
     y reassembly (réplica simplificada del reensamblado por sesión).
  d. Métrica por unidad: merge_units funde cada unidad en una sesión lógica antes de session_summary.
  e. summary_<sistema>.json y la tabla de eval.final (T1–T4 con Holm; T5 y T6 «no calculado»).
  f. systems.md y systems.json: una fila por sistema.
  g. RUN.json: commit, hash y params de frozen.json, sha256 del modelo, split, tamaños, fecha.
  h. Con --split test, si RUN.json ya existe, se niega (no hay opción para forzarlo). RUN.json se escribe
     al EMPEZAR (estado "running") y se completa al terminar: una corrida interrumpida tampoco se repite
     sin una decisión explícita (borrar el archivo a mano).
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable

from engine.detector import SharedLedger, make_frozen
from eval.baselines import allowlist, budget, combined, detect_secrets_baseline, reassembly
from eval.fit.fit import load_secrets
from eval.metrics import aggregate, session_summary
from eval.replay.core import load_sessions, replay, write_events
from eval.search.__main__ import _read_jsonl, assign_families
from eval.search.split import split_sessions

SYSTEMS = ("ours", "no_rotation", "per_session", "no_evidence", "allowlist", "detect_secrets", "combined", "budget", "reassembly")
MANIFEST = "demo/secrets_manifest.json"
SEED = 0
# Sistemas basados en nuestro detector: se reproducen con emit_rotations=True (rotaciones exactas, #133).
DETECTOR_SYSTEMS = ("ours", "no_rotation", "per_session", "no_evidence")
LEDGER_SYSTEMS = ("ours", "no_rotation", "no_evidence")   # un SharedLedger por unidad
# Una línea por sistema para systems.md.
DESCRIPTIONS = {
    "ours": "Alicanto congelado; por unidad, un SharedLedger con el manifiesto completo y los secretos de la "
            "unidad, y un detector por sesión (la cuenta es por clave, compartida entre sesiones).",
    "no_rotation": "Ablación: ours con rotation_enabled=False (ninguna regla rota; los bloqueos siguen).",
    "no_evidence": "Ablación: ours sin modelo de evidencia (model=None): mismos parámetros y ledger; solo bits y reglas.",
    "per_session": "Ablación del enjambre: el detector congelado sin ledger, una cuenta por sesión.",
    "allowlist": "Línea de base: egress solo a dominios aprobados.",
    "detect_secrets": "Línea de base: regex y entropía sobre los argumentos de cada sumidero.",
    "combined": "Línea de base: bloquea si allowlist o detect_secrets bloquea (la de T3).",
    "budget": "Réplica simplificada de un presupuesto acumulado de bits por sesión (Nimbus), sin CUSUM ni rotación; "
              "no es su código ni su producto.",
    "reassembly": "Réplica simplificada del reensamblado por sesión (inspirada en Pipelock y AgentBrake), sin "
                  "decodificar; no es su código ni su producto. Ver eval/baselines/reassembly.py.",
}


# --------------------------------------------------------------------------- a. sesiones

def load_split(split: str, benign_dir: str = "data/benign/sessions", redteam_root: str = "redteam",
               seed: int = SEED) -> tuple[list[list], list[dict], dict[str, dict[str, str]]]:
    """(sesiones, etiquetas, secretos) de esa parte. Reutiliza assign_families y split_sessions de eval.search."""
    rt = Path(redteam_root) / split
    labels = _read_jsonl(rt / "labels.jsonl") if (rt / "labels.jsonl").is_file() else []
    secrets = load_secrets(str(rt / "secrets.jsonl")) if (rt / "secrets.jsonl").is_file() else {}
    benign = load_sessions(benign_dir)
    attack = [s for s in load_sessions(rt / "sessions") if s]
    families, given = assign_families(benign, attack, labels)
    parts = split_sessions(list(families), families, seed=seed, given=given)
    benign_in = [s for s in benign if s and parts[s[0].session_id] == split]
    return benign_in + attack, labels, secrets


# --------------------------------------------------------------------------- b. unidades

def make_units(sessions: list[list], labels: list[dict]) -> list[tuple[str, list[list]]]:
    """[(clave, [sesiones en orden de session_id])]: mismo `group` = una unidad; si no, una por sesión."""
    group_of = {l["session_id"]: l["group"] for l in labels if l.get("group")}
    units: dict[str, list[list]] = defaultdict(list)
    for s in sorted(sessions, key=lambda s: s[0].session_id):
        units[group_of.get(s[0].session_id, s[0].session_id)].append(s)
    return sorted(units.items(), key=lambda kv: kv[1][0][0].session_id)


# --------------------------------------------------------------------------- c. sistemas

def _manifest() -> tuple[dict[str, str], dict[str, list[str]]]:
    data = json.loads(Path(MANIFEST).read_text(encoding="utf-8"))
    return ({s["secret_id"]: s["value"] for s in data["secrets"]},
            {s["secret_id"]: s.get("allowed_hosts", []) for s in data["secrets"]})


def run_system(name: str, units: list[tuple[str, list[list]]], secrets: dict[str, dict[str, str]],
               frozen: Callable | None = None) -> list:
    """Eventos de un sistema sobre todas las unidades (un decide nuevo por sesión; ledger por unidad)."""
    if name not in SYSTEMS:
        raise ValueError(f"sistema desconocido: {name}")
    frozen = frozen or make_frozen()
    values, allowed = _manifest()
    emit = name in DETECTOR_SYSTEMS
    events: list = []
    for _, sess in units:
        if name in LEDGER_SYSTEMS:
            unit_secrets: dict[str, str] = {}
            for s in sess:
                unit_secrets.update(secrets.get(s[0].session_id, {}))
            # Manifiesto completo (con sus allowed_hosts) y encima los secretos de la unidad: lo mismo que ve
            # Detector(secrets=sec) sin ledger, y lo que vio la búsqueda (#133, problema C).
            ledger = SharedLedger({**values, **unit_secrets}, allowed_hosts=allowed)
            kw: dict[str, Any] = {"ours": {}, "no_rotation": {"rotation_enabled": False},
                                  "no_evidence": {"model": None}}[name]
            events += replay(sess, lambda ledger=ledger, kw=kw: frozen(ledger=ledger, seed=SEED, **kw).decide,
                             emit_rotations=True)
            continue
        for s in sess:
            sec = secrets.get(s[0].session_id)
            if name == "per_session":
                factory = lambda sec=sec: frozen(secrets=sec, seed=SEED).decide  # noqa: E731
            elif name == "budget":
                factory = lambda sec=sec: budget.make_decide(secrets={**values, **(sec or {})})  # noqa: E731
            elif name == "reassembly":
                factory = lambda sec=sec: reassembly.make_decide(secrets={**values, **(sec or {})})  # noqa: E731
            else:
                factory = {"allowlist": allowlist.make_decide, "detect_secrets": detect_secrets_baseline.make_decide,
                           "combined": combined.make_decide}[name]
            events += replay([s], factory, emit_rotations=emit)
    return events


# --------------------------------------------------------------------------- d. métrica por unidad

def _as_dict(e: Any) -> dict:
    return copy.deepcopy(e.model_dump(mode="json") if hasattr(e, "model_dump") else dict(e))


def merge_units(events: Iterable[Any], labels: list[dict]) -> tuple[list[dict], list[dict]]:
    """Funde las sesiones de cada unidad de varias sesiones (mismo `group`) en una sesión lógica.

    session_id pasa a ser el group y `t` se renumera creciente a lo largo de la unidad (en orden de
    session_id), en los eventos y en las etiquetas; los call_id siguen únicos (si chocan, se prefijan con
    el session_id original). Función pura: no modifica sus entradas.
    """
    evs = [_as_dict(e) for e in events]
    labs = [dict(l) for l in labels]
    group_of = {l["session_id"]: l["group"] for l in labs if l.get("group")}
    if not group_of:
        return evs, labs

    max_t: dict[str, int] = defaultdict(int)
    for e in evs:
        if e.get("kind") == "tool_call" and e.get("session_id") in group_of:
            max_t[e["session_id"]] = max(max_t[e["session_id"]], int(e["data"]["t"]))
    for l in labs:
        if l["session_id"] in group_of:
            max_t[l["session_id"]] = max(max_t[l["session_id"]], int(l["t"]))
    members: dict[str, list[str]] = defaultdict(list)
    for sid, g in group_of.items():
        members[g].append(sid)
    offset: dict[str, int] = {}
    for g, sids in members.items():
        off = 0
        for sid in sorted(sids):
            offset[sid] = off
            off += max_t.get(sid, 0)

    # call_id únicos dentro de cada unidad
    seen: dict[str, set] = defaultdict(set)
    clash: set[str] = set()
    for e in evs:
        sid = e.get("session_id")
        if e.get("kind") == "tool_call" and sid in group_of:
            key = (group_of[sid], e.get("call_id"))
            if key in seen[group_of[sid]]:
                clash.add(group_of[sid])
            seen[group_of[sid]].add(key)

    for e in evs:
        sid = e.get("session_id")
        if sid not in group_of:
            continue
        g = group_of[sid]
        if g in clash and e.get("call_id") is not None:
            e["call_id"] = f"{sid}/{e['call_id']}"
        e["session_id"] = g
        if e.get("kind") == "tool_call":
            e["data"]["t"] = int(e["data"]["t"]) + offset[sid]
            e["data"]["session_id"] = g
            if g in clash:
                e["data"]["id"] = e["call_id"]
    for l in labs:
        sid = l["session_id"]
        if sid in group_of:
            l["t"] = int(l["t"]) + offset[sid]
            l["session_id"] = group_of[sid]
    return evs, labs


# --------------------------------------------------------------------------- e–f. resúmenes y tablas

def summarize(events: list, labels: list[dict], n_boot: int = 2000) -> dict:
    evs, labs = merge_units(events, labels)
    sessions = session_summary(evs, labs)
    return {**aggregate(sessions, n_boot=n_boot, seed=SEED), "sessions": sessions}


def system_row(name: str, summary: dict) -> dict:
    att = [s for s in summary["sessions"] if s["is_attack"]]
    return {
        "system": name,
        "false_alarm_rate": summary["false_alarm_rate"], "false_alarm_ci": summary["false_alarm_ci"],
        "benign_rotations_per_1000": summary["benign_rotations_per_1000"],
        "prevented_rate": summary["prevented_rate"], "prevented_ci": summary["prevented_ci"],
        "prevented_rate_reread": summary["prevented_rate_reread"],
        "median_max_bits_true": summary["median_max_bits_true"],
        "median_rotations_attack": summary["median_rotations_attack"],
        "rotations_attack_total": int(sum(s["n_rotations"] for s in att)),
        "n_attack_units": summary["n_attack_sessions"], "n_benign_units": summary["n_benign_sessions"],
        "by_family": {f: v["prevented_rate"] for f, v in sorted(summary["by_family"].items())},
    }


def _f(x, nd=3):
    if x is None:
        return "—"
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def systems_markdown(rows: list[dict]) -> str:
    fams = sorted({f for r in rows for f in r["by_family"]})
    head = ["Sistema", "Falsas alarmas [IC]", "Rot. benignas / 1.000", "Prevenidos [IC]", "Prevenidos, cota pesimista",
            "Mediana de bits", "Mediana de rotaciones", *[f"Prev. {f}" for f in fams]]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        fa = f"{_f(r['false_alarm_rate'], 4)} [{_f(r['false_alarm_ci'][0], 4)}, {_f(r['false_alarm_ci'][1], 4)}]"
        pv = f"{_f(r['prevented_rate'])} [{_f(r['prevented_ci'][0])}, {_f(r['prevented_ci'][1])}]"
        cells = [r["system"], fa, _f(r["benign_rotations_per_1000"], 2), pv, _f(r["prevented_rate_reread"]),
                 _f(r["median_max_bits_true"], 1), _f(r["median_rotations_attack"], 1),
                 *[_f(r["by_family"].get(f)) for f in fams]]
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "Qué es cada sistema:", ""]
    lines += [f"- `{r['system']}`: {DESCRIPTIONS.get(r['system'], '')}" for r in rows]
    return "\n".join(lines) + "\n"


def _mark_not_computed(out: Path) -> None:
    """T5 y T6 no se calculan en esta tarea: la tabla lo dice, sin números."""
    md = out / "report.md"
    if not md.is_file():
        return
    lines = []
    for line in md.read_text(encoding="utf-8").splitlines():
        if line.startswith(("| T5 |", "| T6 |")):
            line = line.replace("no corrida (faltan datos de entrada)", "no calculado")
        lines.append(line)
    md.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _git_commit() -> dict:
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                                    capture_output=True, text=True).stdout.strip())
        return {"commit": head, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- comando

def run(split: str, out: str | Path, benign_dir: str = "data/benign/sessions", redteam_root: str = "redteam",
        frozen_path: str = "models/search/frozen.json", model_path: str = "models/model.json",
        systems: Iterable[str] = SYSTEMS, n_boot: int = 2000) -> dict:
    out = Path(out)
    run_json = out / "RUN.json"
    if split == "test" and run_json.exists():
        raise SystemExit(f"ERROR: {run_json} ya existe: la evaluación sobre el set de prueba se corre una sola vez. "
                         "No hay opción para forzarla.")
    t0 = time.perf_counter()
    frozen = make_frozen(frozen_path, model_path)   # verifica el hash del modelo antes de tocar datos
    out.mkdir(parents=True, exist_ok=True)
    meta = {"status": "running", "split": split, **_git_commit(),
            "frozen_hash": frozen.frozen.get("hash"), "params": frozen.frozen.get("params"),
            "model_sha256": frozen.frozen.get("model_sha256"),
            "started": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    _write_json(run_json, meta)

    sessions, labels, secrets = load_split(split, benign_dir, redteam_root)
    units = make_units(sessions, labels)
    rows = []
    for name in systems:
        events = run_system(name, units, secrets, frozen)
        write_events(events, out / f"events_{name}.jsonl")
        summary = summarize(events, labels, n_boot=n_boot)
        _write_json(out / f"summary_{name}.json", summary)
        rows.append(system_row(name, summary))
        print(f"{name}: prevenidos {_f(rows[-1]['prevented_rate'])}, falsas alarmas "
              f"{_f(rows[-1]['false_alarm_rate'], 4)}", flush=True)

    if {"ours", "combined", "no_rotation"} <= set(systems):
        from .__main__ import main as final_main
        final_main(["--ours", str(out / "summary_ours.json"), "--baseline", str(out / "summary_combined.json"),
                    "--no-rotation", str(out / "summary_no_rotation.json"), "--out", str(out), "--seed", str(SEED)])
        _mark_not_computed(out)

    _write_json(out / "systems.json", rows)
    (out / "systems.md").write_text(systems_markdown(rows), encoding="utf-8", newline="\n")
    meta.update({"status": "done", "n_sessions": len(sessions), "n_units": len(units),
                 "n_multi_session_units": sum(1 for _, s in units if len(s) > 1),
                 "systems": list(systems), "seconds": round(time.perf_counter() - t0, 1),
                 "finished": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
    _write_json(run_json, meta)
    print(systems_markdown(rows))
    print(f"{len(sessions)} sesiones, {len(units)} unidades, {meta['seconds']} s -> {out}")
    return {"rows": rows, "meta": meta}


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(prog="python -m eval.final.run")
    ap.add_argument("--split", required=True, choices=["val", "test"])
    ap.add_argument("--out", required=True)
    # Solo para pruebas con datos sintéticos; la evaluación usa los valores por defecto.
    ap.add_argument("--benign", default="data/benign/sessions", help=argparse.SUPPRESS)
    ap.add_argument("--redteam", default="redteam", help=argparse.SUPPRESS)
    ap.add_argument("--frozen", default="models/search/frozen.json", help=argparse.SUPPRESS)
    ap.add_argument("--model", default="models/model.json", help=argparse.SUPPRESS)
    ap.add_argument("--n-boot", type=int, default=2000, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        return run(args.split, args.out, args.benign, args.redteam, args.frozen, args.model, n_boot=args.n_boot)
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
            raise SystemExit(2) from None
        raise


if __name__ == "__main__":
    main()
