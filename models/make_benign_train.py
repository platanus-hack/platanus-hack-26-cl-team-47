"""Arma una carpeta con solo la parte de entrenamiento del fondo benigno (mismo reparto que eval.search)."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from eval.replay.core import load_sessions
from eval.search.split import split_sessions

out = Path(sys.argv[1])
shutil.rmtree(out, ignore_errors=True)
out.mkdir(parents=True)
src = Path("data/benign/sessions")
ids = {}
for f in sorted(src.glob("*.jsonl")):
    s = load_sessions(str(src)) if False else None
import json
for f in sorted(src.glob("*.jsonl")):
    first = json.loads(f.read_text(encoding="utf-8").splitlines()[0])
    ids[first["session_id"]] = f
parts = split_sessions(list(ids), {sid: None for sid in ids}, seed=0)
count = {"train": 0, "val": 0, "test": 0}
for sid, f in ids.items():
    count[parts[sid]] += 1
    if parts[sid] == "train":
        shutil.copy(f, out / f.name)
print(count, "->", out)
