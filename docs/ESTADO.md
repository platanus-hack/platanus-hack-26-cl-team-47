# Estado del proyecto (traspaso entre sesiones de agente)

Actualizado: sábado 21 de noviembre de 2026, 05:50 (H6,8). Lo mantiene el orquestador. Si empiezas una sesión nueva, lee esto, `AGENTS.md` y tu issue; no necesitas el historial del board.

## En una frase

El producto funciona de punta a punta (proxy, medidor de bits, rotación, demo con 200 contra 401). Falta la parte de datos: modelo de evidencia, umbrales, set sellado y evaluación final; y lo de entrega: pitch con cifras, video, README, deploy.

## Estado de `main`

- 484 tests en verde en macOS; verde también en Windows.
- Demo: `python demo/run_split.py --out-dir <tmp>` da 200 a la izquierda y 401 a la derecha. En vivo: `python -m services.scenarios goteo --out <tmp>`.
- Demo visual: tema oscuro, medidor grande de bits por lado y sello 200/401 (`demo/viz/split.js`, `style.css`, `home.html`); la página se desplaza en vertical con paneles de altura fija.
- Escenario: Hospital Regional Tres Cóndores, ficticio (`docs/ESCENARIO.md`). Es solo capa de presentación: no se renombran hosts, `SECRET_n`, keys, `demo/repo` ni datos.
- Datos: `data/benign/sessions` (120 sesiones, 4.885 llamadas benignas) `redteam/train` (80 sesiones de ataque y 20 benignas difíciles, 458 llamadas de ataque) y `redteam/val` (mismo formato, semilla 1, 461 llamadas de ataque, etiquetas con `split: "val"`).
- Todavía no hay `models/model.json`: sin modelo, el detector opera solo con las reglas de bits y rotación.

## Tareas abiertas

| Issue | Quién | Qué | Vence |
|---|---|---|---|

| #110 | `matix3000` | 13d Primer modelo de evidencia y búsqueda con validación real. Sin dependencias pendientes | H11 (10:00) |

`VictoriaGuerriero` y `JCBasulto` no tienen tarea abierta. `Terdmannsdorffer` no recibe tareas ni pedidos de corridas por ahora (decisión del líder).

## Lo que viene, en orden

1. Puerta H12 (11:00): primer análisis en validación. Sale de #110.
2. Paso 11: set de prueba sellado con familias que no están en entrenamiento. Sin asignar. Lo escribe un agente que no haya leído `engine/`.
3. Puerta H20 (19:00): parámetros congelados con hash.
4. H20–H23: evaluación final, una sola corrida (T1 a T6, ablación, líneas de base).
5. Pitch: cifras reales en `pitch/index.html` (hoy dicen «PENDIENTE»), video de respaldo en H26, tres ensayos. Congelamiento total en H27 (domingo 02:00).
6. Entrega (lo hace una persona): `README.md`, `project-description.md`, los cuatro campos de `platanus-hack-project.jsonc` y el deploy en Vercel desde el espejo.

## Decisiones vigentes

- **Equipo morado.** El agente que haya leído `engine/` no escribe ataques ni el set sellado. Las tareas de `redteam/` se hacen en una sesión de agente nueva, con la instrucción de no abrir `engine/`, y siguiendo la especificación del issue al pie de la letra. Si te llega una tarea de `redteam/` y ya leíste `engine/`, avisa en el board.
- **Todo PR que toque `engine/`** agrega su fila en `docs/BITACORA_DETECTOR.md`.
- **Métricas** (`eval.metrics`): las claves son `max_bits_true`, `max_bits_true_by_secret` y `median_max_bits_true`. Tras una rotación, una llamada etiquetada sin `version` cuenta solo si hubo relectura del secreto.
- **Detector:** `T` por defecto es 150; `Params` tiene `max_rotations` y `rotation_window`; el detector pasa `secret_values` al DAG.
- **Pruebas T1 y T2:** cota unilateral al 95 %.
- **Pitch:** no citar la fecha de vigencia de la Ley 21.719 ni nombrar un hospital real como ejemplo de la demo. Datos permitidos y fuentes: `docs/ESCENARIO.md`.
- **Agenda del domingo sin confirmar:** planificar con el cierre más temprano (08:30).

## Pendiente de decisión del líder

- Cuenta global de bits por secreto entre sesiones y agentes (hoy es por sesión). Mientras no se implemente, no decir «por secreto, no por agente» en el pitch.
- Demo interactiva con el público: en espera hasta que el líder avise.
- Conversión de trazas públicas (5b): sin repartir; el fondo benigno propio ya existe.

## Para la sesión del orquestador

- El clon del equipo está en `~/platanus-hack-26-cl-team-47`; `origin` empuja a la organización y al espejo. Tras cada merge: `git pull --rebase`, suite completa, `git push`.
- Verificación de un PR: worktree temporal de la rama, merge de `origin/main`, comando de aceptación del issue, suite completa, y comprobar que solo toca carpetas de su dueño. Merge con squash.
- Entorno de Python para verificar: un venv con `pip install -r` de cada `requirements.txt` del repo (`contracts/`, `engine/`, `eval/`, `proxy/`, `services/`, `demo/`, `docker/`, `redteam/`) más `pytest` e `hypothesis`.
- Seguimiento visual: `python3 -m http.server 8200 --bind 127.0.0.1` desde la raíz del clon; páginas en `/demo/viz/home.html`, `/demo/viz/split.html`, `/demo/viz/report.html` y `/pitch/index.html`.
