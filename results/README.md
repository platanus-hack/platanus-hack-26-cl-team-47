# results/

Salidas de la evaluación final con la configuración **congelada** (#133). Se generan con un solo comando:

```
python -m eval.final.run --split val  --out results/val     # validación: se puede repetir
python -m eval.final.run --split test --out results/test    # prueba (set sellado): lo corre el orquestador UNA vez
```

Configuración congelada: el `models/search/frozen.json` que haya en `main` (lo deja el orquestador tras reajustar el modelo solo con la parte de entrenamiento y repetir la búsqueda) con `models/model.json`; `RUN.json` registra su `hash` y sus `params`. `engine.detector.make_frozen()` comprueba el sha256 del modelo contra `frozen.json` antes de correr.

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
| `ours` | Detector congelado. Por unidad, un `SharedLedger` nuevo con el **manifiesto completo** (y sus `allowed_hosts`) y encima los secretos de la unidad, y un detector por sesión: la cuenta es por clave, compartida entre las sesiones de la unidad. |
| `no_rotation` | `ours` con `rotation_enabled=False`: ninguna regla rota (tampoco la regla 1, que al bloquear rotaba la clave); los bloqueos siguen activos. |
| `per_session` | Detector congelado sin ledger: una cuenta por sesión (ablación del enjambre). |
| `no_evidence` | `ours` sin modelo de evidencia (`model=None`): mismos parámetros y ledger; solo el motor de bits y las reglas. Ablación que se muestra aunque prevenga lo mismo o más. |
| `allowlist`, `detect_secrets`, `combined`, `budget` | Líneas de base de `eval/baselines`, un decide nuevo por sesión. `budget` recibe los secretos del manifiesto con los de la sesión. |
| `reassembly` | Réplica simplificada del reensamblado por sesión del estado del arte (inspirada en Pipelock y AgentBrake; no es su código ni su producto): junta lo que sale por cada campo, sin decodificar, y bloquea con 16 caracteres seguidos del secreto. Un decide nuevo por sesión. |

## Unidades

Las sesiones cuyas etiquetas traen el mismo `group` forman una **unidad** (un ataque repartido entre varias sesiones que comparten secreto); toda otra sesión es una unidad de una sesión. Se reproducen en orden de `session_id` y, antes de medir, `merge_units` las funde en una sesión lógica (`session_id` = el `group`, `t` renumerado creciente), así la métrica cuenta la unión de posiciones en toda la unidad y aplica las rotaciones donde ocurren.

## Una sola corrida sobre prueba

Con `--split test`, si `results/test/RUN.json` existe el comando se niega (código de salida 2) y no hay opción para forzarlo. Como `RUN.json` se escribe al empezar, una corrida interrumpida tampoco se repite sin borrar el archivo a mano, a sabiendas.

## Rotaciones exactas

Los sistemas basados en nuestro detector (`ours`, `no_rotation`, `per_session`, `no_evidence`) se reproducen con `eval.replay.replay(..., emit_rotations=True)`: cada rotación queda como evento `rotation` y la métrica no la infiere por la caída de `leak` (que perdía las rotaciones periódicas y por evidencia). `eval.search` cuenta igual.

## Atacante adaptativo (#150): se reporta aparte

```
python -m eval.final.adaptive --sets val test --out results/adaptive
```

Simula lo que la evaluación final no mide: un atacante que **relee la clave nueva** tras cada rotación y sigue. Parte de cada unidad de ataque grabada y la reescribe mientras se reproduce. Antes de cada envío inserta una relectura del secreto con el valor vigente, y cada envío manda las mismas posiciones del valor **vigente**, con la misma codificación y canal (codificadas con las funciones de `redteam/generate.py` y `redteam/sealed.py`). La medición es exacta: por secreto y versión, las posiciones que salieron en llamadas permitidas. El ataque triunfa si de alguna versión saca más de H − β = 96 bits.

Las unidades que no se pueden reescribir de forma exacta se excluyen y se cuentan como «no reescribibles». En validación son las 10 de A5′: su tabla `custom` depende del estado interno del generador.

Defensores: `ours` (el de `eval.final.run`, con `SharedLedger` por unidad), `no_rotation` y `no_evidence`. **No se usó para ajustar nada:** el detector estaba congelado. Salida en `results/adaptive/`:
- `summary.md` y `summary.json`: por set, sistema y familia;
- `units.json`: una fila por unidad;
- `RUN.json`: commit, hash congelado y fecha.

Lectura: contra este atacante, `ours` resiste porque, tras `max_rotations` rotaciones en `rotation_window` llamadas, el detector pasa a **modo escalado**: bloquea todo sumidero hacia destinos no permitidos y avisa a una persona. La columna «En modo escalado» lo muestra. Es una detención con costo (el agente deja de poder enviar hacia afuera), no una rotación indefinida.

## Banderas del proxy (#167): análisis aparte

`results/proxy_flags/` (`python -m eval.final.proxy_flags --out results/proxy_flags`): la evaluación del set de prueba con las banderas `is_sink` y `untrusted` que calcula el proxy en vivo, en vez de las que escribió el generador, y la regla simple como línea de base. Cómo leerla: `results/test/LECTURA.md`, «Las banderas de cada llamada venían de las grabaciones».

