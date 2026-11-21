# Plan operativo: medidor de información filtrada para agentes de IA

**Este es el plan original.** El proyecto terminó llamándose Alicanto, el escenario se decidió (hospital ficticio, `docs/ESCENARIO.md`), y el congelamiento y la evaluación final se adelantaron al sábado a las 09:40 (`redteam/SELLO.md`, `results/test/`). Lo que sigue se conserva como registro de lo planificado; el estado real está en `docs/ESTADO.md`.

Resumen para agentes del documento «Medidor de información filtrada para agentes de IA», versión 4.0 (21 de noviembre de 2026). Si este resumen y el documento difieren, manda el documento. El orquestador reparte el trabajo desde aquí (ver `AGENTS.md`, sección 7).

## Qué se construye

Un proxy entre un agente de IA y sus herramientas. En cada llamada mide cuánta información de cada secreto ya salió (en bits) y cuánta evidencia de ataque hay (CUSUM). Con eso decide: permitir, bloquear o rotar la clave. No modifica el agente y no usa un LLM para decidir.

La demo que gana es una pantalla dividida con el mismo ataque: a la izquierda, sin protección, el atacante recibe 200 con la clave robada; a la derecha, con el sistema, la clave rota y el atacante recibe 401.

## Reloj

H0 es el viernes 20 a las 23:00. Para saber la hora H actual: horas transcurridas desde entonces.

| Puerta | Cuándo | Qué debe estar verde | Si no |
|---|---|---|---|
| H6 | Sáb 05:00 | Servicios, proxy y motor de bits pasan sus tests | Se recorta el agente en vivo; todo en reproducción |
| H12 | Sáb 11:00 | Primer análisis en validación con ℓ_t y CUSUM | Features más simples; el GFF queda solo para visualizar |
| H15 | Sáb 14:00 | Demo mínima de punta a punta (paso 9) | Todos al paso 9 hasta que funcione |
| H17 | Sáb 16:00 | Crescendo y goteo funcionan en reproducción | La reproducción es la demo principal |
| H20 | Sáb 19:00 | Parámetros congelados; enjambre (paso 17) en `main` | Se congela lo que haya; sin el paso 17, el pitch dice «cuenta por sesión» |
| H23 | Sáb 22:00 | Evaluación final hecha, una sola vez | Se reporta lo que alcanzó, con intervalos |
| H27 | Dom 02:00 | Congelamiento total: solo errores, láminas y ensayo | — |

El documento fija el cierre en H34 (domingo 09:00). La hora exacta de fin del hacking hay que confirmarla con la organización.

## Contratos (se congelan en H2)

Nadie los cambia sin avisar en el board y sin el visto bueno del líder.

```
ToolCall = { id, t, tool, args, output, resources: [path|env|service],
             is_sink: bool, untrusted: bool, session_id, label: benign|attack }

Decision = { action: "allow"|"block"|"rotate+allow"|"rotate+block",
             S, R_plus, leak: {secret_id: {bits, fraction}},
             path: [call_ids], reason, latency_ms }
```

Orden dentro del proxy en cada llamada: interceptar y resolver recursos tocados → actualizar GFF y DAG → bits por secreto → features, ℓ_t y CUSUM → decisión → ejecutar, bloquear o pedir rotación al gestor. Todo queda en el registro de eventos, que alimenta la visualización y el análisis.

Las líneas de base usan la misma interfaz: `decide(ToolCall)`.

## Stack

- Proxy y herramientas: servidor MCP en Python.
- Motor: `numpy`, `scipy.sparse` (GFF), `networkx` o `python-igraph` (DAG).
- Servicios simulados: FastAPI, uno por servicio.
- Análisis: `pandas`, `scipy.stats`, `statsmodels`, `hypothesis`, `datasets`.
- Visualización: una página con d3 o cytoscape.js que reproduce el registro. Streamlit como respaldo.

## Carpetas (propuesta; se confirma en el paso 1a)

| Carpeta | Contenido |
|---|---|
| `contracts/` | `ToolCall`, `Decision` y el esquema del registro de eventos |
| `proxy/` | Servidor MCP, herramientas (`read_file`, `list_dir`, `http_request`, `git`, `github_issue`, `github_comment`), agente mínimo |
| `engine/` | Motor de bits, GFF, DAG, features, CUSUM, regla de decisión |
| `services/` | Gestor de secretos (`vault.test`), API protegida (`api.empresa.test`), servidor del atacante (`attacker.test`), GitHub y web simulados, destino de deploy |
| `redteam/` | Plantillas de ataque, conversión de trazas, set de prueba sellado |
| `eval/` | Arnés de reproducción, líneas de base, búsqueda de umbrales, pruebas T1 a T6 |
| `demo/` | Repositorio de demostración y visualización |
| `pitch/` | Láminas y guion |

## Pasos

Si un criterio de aceptación no se cumple, no se avanza a lo que depende de él.

### Nivel 0: demo mínima (H0 a H15)

| # | Paso | Ventana | Dueño | Aceptación |
|---|---|---|---|---|
| 1a | Contratos y esqueleto: `contracts/` con `ToolCall`, `Decision`, el esquema del registro de eventos y un ejemplo de cada uno | H0–H2 | Proxy | Una llamada viaja agente → proxy → herramienta y vuelve con una `Decision` |
| 1b | Repo de demo neutro: estructura con `.env`, `secrets.yaml` y `docs/`, secretos sintéticos y nombres genéricos (ver «Escenario pendiente») | H0–H4 | Demo | El repo tiene al menos 3 secretos sintéticos declarados en un manifiesto que el motor puede leer |
| 2a | Gestor de secretos con rotación y API protegida | H0–H4 | Servicios | Clave vieja 401, nueva 200 |
| 2b | Servidor del atacante con verdad de terreno | H2–H6 | Servicios | El atacante cuenta bien los bits de un fragmento en claro, en base64 y con XOR |
| 2c | GitHub y web simulados | H2–H6 | Rojo | Crear y leer un issue y un comentario; servir una página con contenido no confiable |
| 3a | Proxy MCP y herramientas | H0–H6 | Proxy | Cada herramienta pasa por el proxy y deja su `ToolCall` en el registro |
| 3b | Agente mínimo: bucle de ~150 líneas, temperatura 0 | H2–H6 | Demo | El agente resuelve un issue legítimo y pasa el test de «sin herramientas escondidas» |
| 4 | Motor de bits: decodificadores, regla de contenido k = 8, posiciones candidatas con caducidad, I_t y λ_t por secreto | H2–H6 | Análisis | Pruebas por propiedades en verde |
| 5a | Plantillas de ataque A1–A4, A5′ y B1–B2 | H2–H8 | Rojo | 80 ataques de entrenamiento entregados en H8 |
| 5b | Conversión de un subconjunto de trazas públicas con secretos insertados | H2–H8 | Rojo | Al menos 3.000 llamadas benignas expuestas |
| 6 | Arnés de reproducción | H4–H8 | Demo | 1.000 llamadas por minuto y el mismo resultado dos veces |
| 7 | GFF y DAG: grafo de archivos con conductancias, condicionamiento, salto y sensibilidad tocada; DAG con aristas de contenido y etiquetas de ancestros | H4–H10 | Proxy | Test de condicionamiento; `.env` y `secrets.yaml` calientes, `docs/` frío |
| 8 | Features y CUSUM | H8–H13 | Análisis | ℓ_t calculado en todas las trazas de entrenamiento y deriva negativa en las benignas |
| 9 | Decisión y rotación de punta a punta | H10–H15 | Servicios | El escenario de goteo produce el diente de sierra en bits y el 401 en la API. **Puerta H15** |

Simplificación del nivel 0: la regla de bloqueo por evidencia usa los ancestros del DAG de forma determinista (el sumidero desciende de algo no confiable y de una lectura del secreto). El Monte Carlo de R⁺ y las aristas de sospecha son nivel 1.

### Nivel 1: credibilidad (H8 a H23)

| # | Paso | Ventana | Dueño | Aceptación |
|---|---|---|---|---|
| 10 | Líneas de base: allowlist, detect-secrets, su combinación y la réplica de Nimbus | H4–H14 | Servicios | Cada una corre sobre 100 llamadas |
| 11 | Resto del rojo: A5, A7, A9, A10, A12, B3–B5 | H8–H17 | Rojo | Set de prueba sellado con hash |
| 12 | Aristas de sospecha y R⁺ | H10–H16 | Proxy | Test contra enumeración exacta |
| 13 | Estimación y búsqueda de umbrales | H13–H20 | Análisis | Frontera de Pareto en validación; configuración congelada con hash en H20 |
| 14 | Evaluación final: T1 a T6, ablación, líneas de base, una sola corrida | H20–H23 | Análisis | Tabla de resultados con intervalos |
| 15 | Visualización: pantalla dividida sincronizada | H8–H26 | Demo | Reproducción completa del escenario principal; video de respaldo grabado en H26 |
| 16 | Pitch | H24–H34 | Demo | Láminas con cifras reales, tres ensayos cronometrados |
| 17 | Enjambre: cuenta global por secreto compartida entre varios agentes y sesiones, con persistencia en disco (`SharedLedger`, issue #114) | H7–H12 | Proxy | Con la fuga repartida entre 5 agentes, sin cuenta global salen los 160 bits sin rotación; con cuenta global rota a más tardar en el tercer fragmento y de ninguna versión salen más de H − β bits |
| 18 | Demo del enjambre en la pantalla dividida: cuenta por agente contra cuenta global (issue #115) | H9–H15 | Demo | Corrida real: izquierda 200 sin rotaciones, derecha 401 con al menos una rotación |

**Enjambre (decisión del líder, H7).** Que Alicanto funcione con un enjambre de agentes es objetivo del proyecto y está prometido en la descripción. Los pasos 17 y 18 deben entrar antes del congelamiento de H20. El paso 17 cambia el detector: lleva fila en `docs/BITACORA_DETECTOR.md` y, por ser una capacidad general, no cuenta como regla para un ataque concreto. Alcance: varios agentes en un mismo proceso y persistencia entre sesiones; varios procesos o máquinas a la vez quedan fuera. Si el paso 17 no está en `main` en H20, la descripción y el pitch dicen «cuenta por sesión» y el enjambre se presenta como trabajo futuro: no se promete lo que no corre.

### Nivel 2: solo si sobra

Después de H17 y con las puertas en verde: A6, A8, A11, A13, corridas en vivo con un agente existente, datos no rotables, credenciales señuelo.

## Escenario pendiente

El escenario de la demo (el rubro de la empresa ficticia) no está decidido. Casi nada depende de él: contratos, proxy, motor, servicios, ataques, arnés y análisis son iguales para cualquier rubro. El escenario es una capa de datos que se aplica al final.

- Mientras no se decida, todo usa nombres genéricos: `api.empresa.test`, `vault.test`, `attacker.test`, secretos `SECRET_1…N`.
- Esperan la decisión: el contenido del repo de demo (nombres, datos, issues que resuelve el agente), los textos de la visualización y el pitch.
- Fecha límite para decidirlo: H8 (sábado 07:00), cuando parte la visualización.

## Áreas

Reparto provisional del 21 de noviembre: mientras no haya demo que armar, Demo toma el agente mínimo y el arnés de reproducción, y Servicios adelanta las líneas de base. Los pasos grandes están partidos (1a, 1b, 2a…) para que cada persona tenga varias tareas independientes.

Los logins están en la tabla de dueños de `AGENTS.md`.

| Área | Responsable de | Pasos |
|---|---|---|
| Proxy | Contratos, proxy MCP, herramientas, GFF, DAG, R⁺, cuenta global del enjambre | 1a, 3a, 7, 12, 17 |
| Análisis | Motor de bits, features, CUSUM, búsqueda, pruebas, ablación. Modera al equipo morado | 4, 8, 13, 14 |
| Servicios | Gestor de secretos, API protegida, servidor del atacante, rotación de punta a punta, líneas de base | 2a, 2b, 9, 10 |
| Rojo | Plantillas, conversión de trazas, GitHub y web simulados, set sellado, ataque adaptativo | 2c, 5a, 5b, 11 |
| Demo | Repo de demo, agente mínimo, arnés de reproducción, visualización, pitch, demo del enjambre, conversaciones con compradores | 1b, 3b, 6, 15, 16, 18 |

## Reglas que no se negocian

**Seguridad del banco de pruebas.** Solo secretos sintéticos. Solo servidores simulados con nombres `.test`. Las herramientas del agente no tienen salida a internet. Nada sale del banco de pruebas.

**El agente no tiene herramientas propias.** Si usa su terminal o lectura interna, se salta el proxy. Prueba: se le pide leer un archivo; si la lectura aparece en su transcripción y no en el registro del proxy, la corrida no vale.

**Tres registros independientes** con la misma marca de tiempo y sesión: el del proxy (decisiones), el del agente (transcripción) y el del atacante (verdad de terreno). Los bits que obtuvo el atacante los calcula el servidor del atacante, no el detector.

**Equipo morado (contra el sobreajuste).**

1. El rojo no mira el código del detector antes de H20. El agente del área Rojo no abre `engine/` hasta entonces.
2. El set de prueba lo genera el rojo, guarda su hash y queda sellado hasta H20. Sus familias no aparecen en entrenamiento.
3. Revisiones de 15 minutos en H6, H12 y H17, solo sobre fallas de entrenamiento y validación.
4. El azul puede corregir errores y ajustar parámetros en validación. No puede agregar reglas para un ataque concreto. Si lo hace, se anota.
5. En H20 se congela. El rojo recibe la configuración completa y tiene 2 horas de ataque adaptativo, que se reporta aparte y no se usa para reajustar.
6. Bitácora con hora y motivo de cada cambio al detector.

**Las cifras de las láminas son resultados reales.** Nunca se inventan.

## Notas de la revisión del 21 de noviembre

Detalle en el proyecto «platathon» de Claude (`usuario-objetivo-y-revision-de-la-propuesta.md`).

- El período de rotación T no está en la tabla de parámetros y necesita valor inicial. La cota del teorema exige d₀·T < c(H − β) − b.
- T1 solo pasa con cero falsas alarmas en 3.000 llamadas expuestas. Para tolerar una hacen falta unas 5.000.
- Falta respuesta para el competidor directo (brokers de credenciales como Agent Vault): son complementarios; el medidor cubre lo que queda en el repositorio y lo que sale por canales permitidos.
- El escenario de la demo está pendiente de decisión del equipo (ver «Escenario pendiente»). La propuesta es un servicio de agenda y ficha clínica de un centro médico ficticio, con pacientes sintéticos.
