# Bitácora del detector

Regla 6 del equipo morado (`docs/PLAN.md`): cada cambio al detector queda anotado con hora y motivo. El detector es todo lo que vive en `engine/`. Hora de Santiago; H0 es el viernes 20 de noviembre de 2026 a las 23:00.

Quien mergea un cambio en `engine/` agrega una fila aquí en el mismo PR o justo después. Si el cambio responde a un ataque concreto visto en entrenamiento o validación, hay que decirlo en la última columna (regla 4: el azul no agrega reglas para un ataque concreto; si lo hace, se anota).

## Cambios hasta H4 (reconstruidos del historial de git)

Todos son construcción inicial o corrección de errores de implementación. Ninguno responde a un ataque del equipo rojo: el set de entrenamiento todavía no existe.

| Hora | Commit | Motivo |
|---|---|---|
| 2026-11-21 02:08 | `b3aa33e` | 4 Motor de bits: I_t y λ_t por secreto con decodificadores y candidatas (#21) |
| 2026-11-21 02:10 | `b9741cb` | 7a: grafo de archivos con GFF (#22) |
| 2026-11-21 02:10 | `b60abcb` | 7b DAG de llamadas con aristas de contenido (#23) |
| 2026-11-21 02:13 | `d54601b` | 8a Modelo de evidencia (histogramas LLR) y CUSUM de Page (#27) |
| 2026-11-21 02:17 | `1178779` | 12: aristas de sospecha y R+ (y exposed() con sumideros no confiables) (#31) |
| 2026-11-21 02:19 | `b7b7a70` | 9a Detector del nivel 0: decide(ToolCall) -> Decision (#33) |
| 2026-11-21 02:20 | `664a2d9` | 12b: g de sospecha con el lado que tiene nodos (#35) |
| 2026-11-21 02:22 | `6261528` | 9b leak con candidatas y fábrica make_measure_only (#39) |
| 2026-11-21 02:36 | `3108900` | 9e Camino explicativo en las rotaciones (#54) |
| 2026-11-21 02:43 | `4ad36fe` | 8b Pipeline de estimación del modelo de evidencia (#61) |
| 2026-11-21 02:58 | `7351a8b` | 12c Explicación de los bloqueos por dominadores (#74) |

## Cambios desde H4

| Hora | Commit o PR | Qué cambió | Motivo | ¿Responde a un ataque concreto? |
|---|---|---|---|---|
| 2026-11-21 03:26 | #86 (7c) | `engine/graph/dag.py`: con `secret_values`, la etiqueta S de un secreto solo viaja por una arista de contenido si el material compartido incluye k caracteres seguidos de su valor (en claro o en una variante); una salida con el valor cuenta como lectura; `set_secret_value` tras rotar. Índice global de k-gramas (bloques ordenados que se fusionan) en vez de comparar contra cada llamada anterior. Sin `secret_values`, mismas aristas y etiquetas que antes (test de equivalencia en 30 sesiones). | S se heredaba con cualquier texto del archivo del secreto (URLs, hosts del `.env`); el costo de `add` crecía con la sesión (p95 15,6 ms con 1.000 llamadas, ahora 0,55 ms). | No: revisión de diseño |
