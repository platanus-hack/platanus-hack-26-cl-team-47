#!/usr/bin/env bash
# Demo real de la pantalla dividida con un solo comando (tarea 15d).
# Uso, desde la raíz del repo:  bash demo/demo.sh   (Ctrl+C para cerrar el servidor)
set -euo pipefail

cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"
PORT="${PORT:-8200}"

"$PY" demo/run_split.py --out-dir demo/out

echo
echo "Abre: http://127.0.0.1:${PORT}/viz/split.html?left=../out/left.jsonl&right=../out/right.jsonl"
echo "Sin correr nada: http://127.0.0.1:${PORT}/viz/split.html?left=fixtures/real_left.jsonl&right=fixtures/real_right.jsonl"
echo

exec "$PY" -m http.server "$PORT" --bind 127.0.0.1 --directory demo
