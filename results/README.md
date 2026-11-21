# results/

Salidas de la evaluación final con la configuración **congelada** (#133). Se generan con un solo comando:

```
python -m eval.final.run --split val  --out results/val     # validación: se puede repetir
python -m eval.final.run --split test --out results/test    # prueba (set sellado): lo corre el orquestador UNA vez
```

Configuración congelada: `models/search/frozen.json` (hash `42cfa5e4610ae99b0d5af2f0a2bbf1800f7cfe87414ff46a0302400227e0432b`; `b 4`, `b_rot 5`, `lambda_rot 0.1`, `T 75`) con `models/model.json`. `engine.detector.make_frozen()` comprueba el sha256 del modelo contra `frozen.json` antes de correr.

## Qué hay en cada carpeta

| Archivo | Qué es |
|---|---|
| `RUN.json` | Commit de git (y si había cambios sin commitear), `hash` y `params` de `frozen.json`, sha256 del modelo, split, sesiones, unidades, segundos y fecha. Se escribe al **empezar** (`"status": "running"`) y se completa al terminar (`"done"`). |
| `systems.md`, `systems.json` | Una fila por sistema: falsas alarmas e IC, rotaciones benignas por 1.000, prevenidos e IC (por contenido), prevenidos con la cota pesimista (relectura), mediana de bits, mediana de rotaciones en ataques y prevenidos por familia. |
| `report.md`, `report.json` | Tabla de `eval.final`: T1–T4 con corrección de Holm (T3 contra `combined`, como dice el plan; `budget` y `reassembly` solo en la tabla comparativa; T4 contra `no_rotation`), la fila informativa de la cota pesimista y T5–T6 «no calculado». |
| `summary_<sistema>.json` | Lo mismo que escribe `python -m eval.metrics`: agregados y la lista `sessions`, una por **unidad**. |
| `events_<sistema>.jsonl` | Eventos crudos de la reproducción. **No se versionan** (`results/.gitignore`). |

## Sistemas

| Sistema | Qué es |
|---|---|
| `ours` | Detector congelado. Por unidad, un `SharedLedger` nuevo con los secretos de la unidad y un detector por sesión: la cuenta es por clave, compartida entre las sesiones de la unidad. |
| `no_rotation` | `ours` con las reglas de rotación de la regla 2 apagadas (`b_rot=1e9`, `lambda_rot=2`, `T=10⁹`, `check_params=False`); mismos `b` y modelo. Los bloqueos siguen activos. El bloqueo determinista (regla 1) rota la clave al bloquear, porque el motor une las dos cosas: esas rotaciones siguen. |
| `per_session` | Detector congelado sin ledger: una cuenta por sesión (ablación del enjambre). |
| `allowlist`, `detect_secrets`, `combined`, `budget` | Líneas de base de `eval/baselines`, un decide nuevo por sesión. `budget` recibe los secretos del manifiesto con los de la sesión. |
| `reassembly` | Réplica simplificada del reensamblado por sesión del estado del arte (inspirada en Pipelock y AgentBrake; no es su código ni su producto): junta lo que sale por cada campo, sin decodificar, y bloquea con 16 caracteres seguidos del secreto. Un decide nuevo por sesión. |

## Unidades

Las sesiones cuyas etiquetas traen el mismo `group` forman una **unidad** (un ataque repartido entre varias sesiones que comparten secreto); toda otra sesión es una unidad de una sesión. Se reproducen en orden de `session_id` y, antes de medir, `merge_units` las funde en una sesión lógica (`session_id` = el `group`, `t` renumerado creciente), así la métrica cuenta la unión de posiciones en toda la unidad y aplica las rotaciones donde ocurren.

## Una sola corrida sobre prueba

Con `--split test`, si `results/test/RUN.json` existe el comando se niega (código de salida 2) y no hay opción para forzarlo. Como `RUN.json` se escribe al empezar, una corrida interrumpida tampoco se repite sin borrar el archivo a mano, a sabiendas.
