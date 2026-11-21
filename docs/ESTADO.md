# Estado del proyecto (traspaso entre sesiones de agente)

Actualizado: sábado 21 de noviembre de 2026, 09:55 (H10,9). Lo mantiene el orquestador. Si empiezas una sesión nueva, lee esto, `AGENTS.md` y tu issue; no necesitas el historial del board.

## En una frase

El producto funciona de punta a punta (proxy, medidor de bits, rotación, demo con 200 contra 401). Falta la parte de datos: modelo de evidencia, umbrales, set sellado y evaluación final; y lo de entrega: pitch con cifras, video, README, deploy.

## Estado de `main`

- 589 tests en verde en macOS.
- Demo: `python demo/run_split.py --out-dir <tmp>` da 200 a la izquierda y 401 a la derecha. En vivo: `python -m services.scenarios goteo --out <tmp>`.
- Demo visual: tema oscuro, medidor grande de bits por lado y sello 200/401 (`demo/viz/split.js`, `style.css`, `home.html`); la página se desplaza en vertical con paneles de altura fija.
- Escenario: Hospital Regional Tres Cóndores, ficticio (`docs/ESCENARIO.md`). Es solo capa de presentación: no se renombran hosts, `SECRET_n`, keys, `demo/repo` ni datos.
- Datos: `data/benign/sessions` (120 sesiones, 4.885 llamadas benignas) `redteam/train` (80 sesiones de ataque y 20 benignas difíciles, 458 llamadas de ataque) y `redteam/val` (mismo formato, semilla 1, 461 llamadas de ataque, etiquetas con `split: "val"`).
- Modelo de evidencia y búsqueda en `models/`. En validación, con la métrica por contenido: 0 falsas alarmas y 90 % de ataques prevenidos (cota pesimista 83,75 %). **Va a cambiar:** falta contar las rotaciones con eventos exactos y reajustar el modelo solo con la parte de entrenamiento del fondo benigno (ver #133). El congelamiento es el `frozen.json` que resulte de eso.
- La demo y el goteo en vivo corren el detector **sin** modelo de evidencia, con rotación al 30 % de la clave. La configuración evaluada es otra (la congelada). Hay que decirlo así.

## Tareas abiertas

| Issue | Quién | Qué | Vence |
|---|---|---|---|
| #150 | `JCBasulto` | 14c Simulación de un atacante adaptativo, reportada aparte | H14 |
| #142 | `VictoriaGuerriero` | 16e Pitch para el formato de finales (3 minutos con corte) | H14 |
| #151 | `VictoriaGuerriero` | 16f Cifras de la evaluación final en el pitch y página de resultados | H14 |
| #138 | `VictoriaGuerriero` | 9p Enjambre en vivo: cuenta compartida entre procesos del proxy y guía de inicio | H17 |


`Terdmannsdorffer` no recibe tareas ni pedidos de corridas por ahora (decisión del líder).

**Reparto (decisión del líder, H8,6):** `matix3000` y `Terdmannsdorffer` no reciben tareas ni pedidos de corridas. Todo lo del área Análisis (`engine/`, `eval/`: #126, congelamiento de H20 y evaluación final) es de `JCBasulto`, con traspaso en cada issue. Agentes activos: `JCBasulto`, `VictoriaGuerriero` y la sesión Rojo del líder.

## Congelamiento y evaluación final: hechos

- Configuración congelada en `models/search/frozen.json` (`b 4`, `b_rot 2`, `lambda_rot 0,1`, `T 75`), etiqueta `congelamiento`. **`engine/` y `models/` no cambian más** salvo orden del líder.
- Set sellado abierto (`redteam/test`, sello comprobado) y evaluación final corrida una vez: `results/test/`. El comando se niega a repetirla.
- Resultado: 180 de 180 ataques prevenidos, 0 de 5.879 llamadas benignas bloqueadas. **Lee `results/test/LECTURA.md` antes de escribir cualquier cifra**: ataques grabados, costo de 34 rotaciones de más en 90 sesiones benignas difíciles, y el contador de bits solo previene 40 de 180.
- Pendiente de decisión del líder: clave de API para `python -m proxy.agent.runs` (corridas con un LLM real).

## Decisiones vigentes

- **Nombre del proyecto: Cuentagotas.** Ya está en la portada, la pantalla dividida, la lámina 1, `platanus-hack-project.jsonc` y `project-description.md`.
- **Enjambre: hecho y en `main`** (pasos 17 y 18 del plan). `SharedLedger` y `make_decide_shared` en `engine/detector`; demo en `split.html?demo=enjambre` (cuenta por agente 200, cuenta global 401). Ya se puede decir «la cuenta es por clave, no por agente», con el límite: un solo proceso, persistencia entre sesiones.
- **Equipo morado.** El agente que haya leído `engine/` no escribe ataques ni el set sellado. Las tareas de `redteam/` se hacen en una sesión de agente nueva, con la instrucción de no abrir `engine/`, y siguiendo la especificación del issue al pie de la letra. Si te llega una tarea de `redteam/` y ya leíste `engine/`, avisa en el board.
- **Todo PR que toque `engine/`** agrega su fila en `docs/BITACORA_DETECTOR.md`.
- **Métricas** (`eval.metrics`): las claves son `max_bits_true`, `max_bits_true_by_secret` y `median_max_bits_true`. Tras una rotación, una llamada etiquetada sin `version` cuenta solo si hubo relectura del secreto.
- **Detector:** `T` por defecto es 150; `Params` tiene `max_rotations` y `rotation_window`; el detector pasa `secret_values` al DAG.
- **Pruebas T1 y T2:** cota unilateral al 95 %.
- **Pitch:** no citar la fecha de vigencia de la Ley 21.719 ni nombrar un hospital real como ejemplo de la demo. Datos permitidos y fuentes: `docs/ESCENARIO.md`.
- **Agenda del domingo sin confirmar:** planificar con el cierre más temprano (08:30).

## Pendiente de decisión del líder

- Demo interactiva con el público: en espera hasta que el líder avise.
- Conversión de trazas públicas (5b): sin repartir; el fondo benigno propio ya existe.

## Para la sesión del orquestador

- El clon del equipo está en `~/platanus-hack-26-cl-team-47`; `origin` empuja a la organización y al espejo. Tras cada merge: `git pull --rebase`, suite completa, `git push`.
- Verificación de un PR: worktree temporal de la rama, merge de `origin/main`, comando de aceptación del issue, suite completa, y comprobar que solo toca carpetas de su dueño. Merge con squash.
- Entorno de Python para verificar: un venv con `pip install -r` de cada `requirements.txt` del repo (`contracts/`, `engine/`, `eval/`, `proxy/`, `services/`, `demo/`, `docker/`, `redteam/`) más `pytest` e `hypothesis`.
- Seguimiento visual: `python3 -m http.server 8200 --bind 127.0.0.1` desde la raíz del clon; páginas en `/demo/viz/home.html`, `/demo/viz/split.html`, `/demo/viz/report.html` y `/pitch/index.html`.
