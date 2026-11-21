"""Búsqueda de umbrales sobre validación, frontera de Pareto y congelamiento con hash
(documento v4.0, sección 6.2)."""

from __future__ import annotations

import datetime as _dt
import hashlib
import itertools
import json
import multiprocessing as mp
import os
from pathlib import Path
from typing import Any

from contracts import ToolCall
from engine.detector import Detector, Params
from eval.metrics import aggregate, session_summary
from eval.replay.core import replay

GRID = {"b": [4, 6, 8, 9.2, 11, 13], "b_rot": [2, 3, 4, 5, 6],
        "lambda_rot": [0.1, 0.2, 0.3, 0.4, 0.5], "T": [50, 100, 200, 400, 800]}   # 750 combinaciones

OBJECTIVES = ("false_alarm_rate", "benign_rotations_per_1000", "median_max_bits_true")   # se minimizan


def combos(grid: dict[str, list]) -> list[dict]:
    keys = list(grid)
    return [dict(zip(keys, vals)) for vals in itertools.product(*(grid[k] for k in keys))]


def evaluate(params: Params, model, sessions: list[list[ToolCall]], labels: list[dict],
             secrets: dict[str, dict[str, str]] | None = None, seed: int = 0) -> dict:
    """Una fila: los parámetros más las métricas de eval.metrics.aggregate. Un detector por sesión."""
    secrets = secrets or {}
    events = []
    for s in sessions:
        if not s:
            continue
        sec = secrets.get(s[0].session_id)
        events += replay([s], lambda sec=sec: Detector(params=params, model=model, secrets=sec, seed=seed).decide)
    agg = aggregate(session_summary(events, labels), n_boot=50, seed=seed)
    row = {k: getattr(params, k) for k in ("b", "b_rot", "lambda_rot", "T")}
    for k in ("false_alarm_rate", "benign_rotations_per_1000", "prevented_rate", "median_max_bits_true"):
        row[k] = agg[k]
    return row


# --- paralelo ----------------------------------------------------------------

_W: dict[str, Any] = {}


def _init(model, sessions, labels, secrets, seed):
    _W.update(model=model, sessions=sessions, labels=labels, secrets=secrets, seed=seed)


def _work(combo: dict) -> dict:
    return evaluate(Params(**combo), _W["model"], _W["sessions"], _W["labels"], _W["secrets"], _W["seed"])


def search(model, val_sessions: list[list[ToolCall]], labels: list[dict], secrets: dict | None,
           grid: dict[str, list] = GRID, workers: int = 0, seed: int = 0) -> list[dict]:
    """Recorre la grilla con la misma semilla en todas las combinaciones. Filas en el orden de la grilla."""
    return search_combos(model, val_sessions, labels, secrets, combos(grid), workers, seed)


def search_combos(model, val_sessions: list[list[ToolCall]], labels: list[dict], secrets: dict | None,
                  cs: list[dict], workers: int = 0, seed: int = 0) -> list[dict]:
    """Como search, pero sobre una lista explícita de combinaciones (para --limit-combos)."""
    n = workers or os.cpu_count() or 1
    if n <= 1 or len(cs) <= 1:
        return [evaluate(Params(**c), model, val_sessions, labels, secrets, seed) for c in cs]
    ctx = mp.get_context("spawn")
    with ctx.Pool(min(n, len(cs)), initializer=_init, initargs=(model, val_sessions, labels, secrets, seed)) as pool:
        return pool.map(_work, cs, chunksize=max(1, len(cs) // (4 * n)))


# --- selección ------------------------------------------------------------------

def _obj(row: dict, k: str) -> float:
    v = row.get(k)
    return float("inf") if v is None else float(v)


def _dominates(a: dict, b: dict) -> bool:
    va, vb = [_obj(a, k) for k in OBJECTIVES], [_obj(b, k) for k in OBJECTIVES]
    return all(x <= y for x, y in zip(va, vb)) and any(x < y for x, y in zip(va, vb))


def pareto(rows: list[dict]) -> list[dict]:
    return [r for r in rows if not any(_dominates(o, r) for o in rows if o is not r)]


def choose(rows: list[dict], max_false_alarm: float = 1e-3, max_benign_rot_per_1000: float = 5.0) -> dict | None:
    """Neyman–Pearson: entre las que cumplen las metas, menor mediana de bits; empate, mayor prevented_rate."""
    ok = [r for r in rows
          if (r.get("false_alarm_rate") or 0.0) <= max_false_alarm
          and (r.get("benign_rotations_per_1000") or 0.0) <= max_benign_rot_per_1000]
    if not ok:
        return None
    return min(ok, key=lambda r: (_obj(r, "median_max_bits_true"), -(r.get("prevented_rate") or 0.0)))


# --- congelamiento --------------------------------------------------------------

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_dirs(dirs: list[str]) -> str:
    """SHA-256 del contenido ordenado de las carpetas (ruta relativa + bytes de cada archivo)."""
    h = hashlib.sha256()
    for d in sorted(dirs):
        root = Path(d)
        for p in sorted(x for x in root.rglob("*") if x.is_file()):
            h.update(p.relative_to(root).as_posix().encode("utf-8") + b"\0")
            h.update(p.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def freeze(params: dict, model_path: str, data_dirs: list[str], out: str, date: str | None = None) -> dict:
    body = {
        "params": params,
        "model_sha256": sha256_file(model_path),
        "data_sha256": sha256_dirs(data_dirs),
        "date": date or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }
    frozen = {**body, "hash": hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(frozen, indent=2, sort_keys=True), encoding="utf-8")
    return frozen
