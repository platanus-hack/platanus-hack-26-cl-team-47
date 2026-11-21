# Alicanto · team-47 · Platanus Hack 26: Santiago

<img src="./project-logo.png" alt="Logotipo de Alicanto: un ave en vuelo con alas doradas y plateadas" width="200" />

Track: 🛡️ AI Security

**Tu agente de IA puede regalar tus claves de a cuatro letras. Alicanto cuenta cada gota y cambia la cerradura antes de que la llave esté completa.**

En la leyenda del desierto de Atacama, el alicanto es un ave que brilla como el oro; quien la sigue por codicia termina perdido y con las manos vacías. Aquí, quien sigue la clave termina igual.

## Equipo

- Tomas Erdmannsdorffer Muñoz ([@terdmannsdorffer](https://github.com/terdmannsdorffer))
- José Carlos Basulto ([@jcbasulto](https://github.com/jcbasulto))
- Juan Pedro Lira ([@jplira2](https://github.com/jplira2))
- Victoria Guerriero ([@VictoriaGuerriero](https://github.com/VictoriaGuerriero))
- Matías Morgado ([@matix3000](https://github.com/matix3000))

**Demo en línea:** https://alicanto.vercel.app · [resultados y sus límites](https://alicanto.vercel.app/results.html)

**Evaluación:** con las banderas que calcula el proxy en vivo, 120 de 180 ataques grabados: cuatro de las seis familias; las dos que no se cubren son la clave enviada a su propio destino permitido y la fuga por commits de git. Cero llamadas benignas bloqueadas en 5.879, con las banderas del generador y con las del proxy. Cómo leer las cifras: [results/test/LECTURA.md](results/test/LECTURA.md).

## Qué es

Un proxy entre un agente de IA y sus herramientas. En cada llamada mide cuántos bits de cada clave ya salieron hacia afuera, aunque salgan de a pocos caracteres o codificados, y rota la clave en el gestor de secretos antes de que la fuga se complete. No modifica el agente y no usa un LLM para decidir.

La descripción completa está en [project-description.md](project-description.md).

## Verlo funcionar

Requiere Python 3.11 o superior.

```bash
pip install -r requirements.txt
```

**La demo en el navegador** (sitio estático, sin instalar nada más):

```bash
python -m http.server 8200 --directory demo/viz
```

- `http://127.0.0.1:8200/home.html`: portada.
- `http://127.0.0.1:8200/split.html`: el mismo ataque dos veces. Sin protección el atacante arma la clave y recibe 200; con Alicanto la clave rota y recibe 401.
- `http://127.0.0.1:8200/split.html?demo=enjambre`: cinco agentes se reparten la fuga. Con una cuenta por agente nadie la ve; con la cuenta global, rota.

**El ataque en vivo**, con el gestor de secretos, la API protegida, el servidor del atacante y el proxy reales (todo local):

```bash
python -m services.scenarios goteo --out logs/goteo
```

**Regenerar la demo desde cero:**

```bash
python demo/run_split.py --out-dir demo/out            # goteo
python demo/run_split.py --swarm --out-dir demo/out    # enjambre
```

**Tests:**

```bash
python -m pytest -q
```

**Conectarlo a tu agente de código** (servidor MCP, con la cuenta compartida entre agentes): [docs/QUICKSTART.md](docs/QUICKSTART.md).

**Como hook de Claude Code** (cuenta los bits que salen por `Bash`, `WebFetch` y `Read`, sin cambiar las herramientas del agente): [integrations/claude_code/README.md](integrations/claude_code/README.md). Límite: ve lo que el modelo escribe en los comandos, no lo que un comando hace por dentro. Probado en una sesión real de Claude Code: corre en cada llamada, permite sin fricción y niega con el motivo; el contador de bits con un modelo real no quedó probado, porque el modelo se negó por su cuenta a enviar los trozos de la clave.

## Para quien evalúa (y para su agente)

Cada afirmación del proyecto, con el archivo que la sostiene y un comando que la comprueba en menos de un minuto. Todo corre en local, sin claves ni servicios externos.

| Afirmación | Dónde está | Cómo comprobarla |
|---|---|---|
| Cuenta cuántos bits de cada clave ya salieron, sumando fragmentos entre llamadas | `engine/bits/engine.py` | `python -m pytest engine/bits -q` (incluye pruebas por propiedades) |
| Lee fragmentos en claro y en base64, hexadecimal, URL, ROT13, invertidos y separados | `engine/bits/decoders.py` | `python -m pytest engine/bits/tests/test_short_encoded.py -q` |
| Rota la clave en el gestor: la vieja deja de servir (401) y la nueva sirve (200) | `proxy/live.py`, `services/vault/` | `python -m services.scenarios goteo --out logs/goteo` |
| El mismo ataque termina en 200 sin protección y en 401 con Alicanto | `demo/run_split.py` | `python demo/run_split.py --out-dir demo/out` (regenera la demo desde cero) |
| El grafo de archivos propaga la sensibilidad de los archivos conocidos a sus vecinos y da señales por llamada al modelo de evidencia. La formulación es la de campos gaussianos sobre un grafo para propagar etiquetas (Zhu, Ghahramani y Lafferty, Semi-Supervised Learning Using Gaussian Fields and Harmonic Functions, ICML 2003). | `engine/graph/gff.py` | `python -m pytest engine/graph -q` |
| Una sola cuenta por clave para varios agentes | `engine/detector/ledger.py` | `python demo/run_split.py --swarm --out-dir demo/out` y `python -m pytest engine/detector/tests/test_ledger.py -q` |
| Ningún LLM decide | `engine/` no importa ningún cliente de modelos | `grep -rn "anthropic\|openai" engine/` no devuelve nada |
| Si el gestor de secretos no responde, se bloquean las salidas | `proxy/live.py` (`fail_safe`) | `python -m pytest proxy/tests -q` |
| La cifra con las banderas que calcula el proxy | `results/proxy_flags/systems.md`, `results/test/LECTURA.md` | `python -m eval.final.proxy_flags --out /tmp/pf` |
| Los ataques de prueba se sellaron con hash antes de evaluar | `redteam/SELLO.md` | El comando de verificación está en ese archivo |
| Los ataques los escribió una sesión de agente aparte, que tenía prohibido abrir el código del detector. Es una regla de trabajo del equipo, anotada en `docs/PLAN.md`; desde fuera no se puede comprobar. | `docs/PLAN.md` («Equipo morado»), `docs/BITACORA_DETECTOR.md` | Cada cambio al detector está anotado con hora y motivo |
| Los ataques son un benchmark que cualquiera puede correr contra su propia defensa | [`redteam/README.md`](redteam/README.md), `eval/bench.py` | `python -m eval.bench --defense eval.baselines.example_defense:make_decide --set val --out /tmp/x` |

### De dónde sale cada umbral

Ningún número está puesto a mano sin explicación. Los que se ajustan se eligieron en validación con una búsqueda de 750 combinaciones (`python -m eval.search`, resultados en `models/search/`), con dos restricciones: como máximo una falsa alarma por cada 1.000 llamadas expuestas y 5 rotaciones benignas por cada 1.000.

| Parámetro | Valor | Qué significa y por qué |
|---|---|---|
| `k` | 8 caracteres | Largo desde el cual una coincidencia con la clave se da por confirmada. Con claves hexadecimales, 8 caracteres al azar coinciden con probabilidad despreciable |
| `MIN_CANDIDATE` | 4 caracteres | Coincidencias más cortas cuentan como candidatas: suman, pero caducan |
| `W` | 50 llamadas | Cuánto vive una candidata sin que llegue otra. Limita las coincidencias al azar en texto normal |
| `beta_bits` | 64 bits | Lo que se supone que el atacante puede adivinar por fuerza bruta. Con una clave de 160 bits, el ataque triunfa si saca más de 96 |
| `lambda_rot` | 0,3 en la demo; 0,1 en la evaluación | Fracción de la clave filtrada que dispara la rotación |
| `T` | llamadas | Rotación periódica de una clave ya leída. Debe cumplir una cota, comprobada en código (`Params.check`), **solo para pedazos de 4 caracteres o más**, los que el contador cuenta: un envío de 7 caracteres cada 51 llamadas, justo bajo el radar, no alcanza los 96 bits entre dos rotaciones (medido: 84 bits con la demo, `results/short_fragments/`). Pedazos de 1 a 3 caracteres el contador no los cuenta y la cota no los cubre: sin el modelo de evidencia, enviados seguido, sacan la clave entera antes de la rotación periódica. Las cifras, en [results/short_fragments/summary.md](results/short_fragments/summary.md) |
| `b`, `b_rot` | umbrales | Evidencia acumulada (CUSUM) para bloquear y para rotar |
| `max_rotations` | 3 cada 200 llamadas | Tope para que nadie pueda forzar rotaciones sin fin; después se bloquean las salidas de esa clave y se avisa a una persona |

Dos configuraciones, dichas con claridad:
- **La demo** usa los valores por defecto de `engine/detector/params.py` (rota al 30 % de la clave) y corre **sin** modelo de evidencia: ahí decide solo el contador de bits.
- **La evaluación** usa la configuración congelada de `models/search/frozen.json` con el modelo de `models/model.json`.

### Qué es real y qué es simulado

- **Real:** el proxy MCP y sus herramientas, el motor que mide, el gestor de secretos con rotación, la API protegida que responde 200 o 401, y el servidor del atacante que cuenta lo que recibió. Las cifras de la demo salen de ejecutarlos.
- **Simulado:** los servicios corren en local con nombres `.test`; las claves son sintéticas; el hospital y sus pacientes son ficticios; el tráfico benigno y los ataques son guiones generados por nuestro equipo rojo, no tráfico de producción.
- **El agente:** en la demo y en la evaluación el agente es un guion reproducible, sin LLM. El proxy funciona con cualquier cliente MCP (`python -m proxy.server`).

## Cómo está organizado

| Carpeta | Qué hay |
|---|---|
| `contracts/` | Los tipos compartidos: `ToolCall`, `Decision` y el registro de eventos |
| `proxy/` | Proxy MCP y sus seis herramientas |
| `engine/` | Motor de bits, grafos, evidencia acumulada, decisión y la cuenta global del enjambre |
| `services/` | Gestor de secretos con rotación, API protegida, servidor del atacante, GitHub y web simulados |
| `redteam/` | Ataques de entrenamiento y validación, generados de forma determinista |
| `eval/` | Arnés de reproducción, líneas de base, búsqueda de umbrales y pruebas de hipótesis |
| `demo/` | Repositorio de demostración y visualización |
| `pitch/` | Láminas, guion y preguntas del jurado |
| `docker/` | Red aislada con todos los servicios, sin salida a internet |

## Reglas del banco de pruebas

Solo secretos sintéticos y servidores simulados con nombres `.test`. Las herramientas del agente no tienen salida a internet. El hospital de la demo, sus pacientes y sus claves son ficticios.

## Límites

- Se mide una cota inferior: lo que pasa por el proxy, en las codificaciones que el motor sabe leer.
- **El contador no cuenta pedazos de menos de 4 caracteres.**
  - La cota de la rotación periódica vale solo para pedazos de 4 o más.
  - Con 1 a 3 caracteres por envío, la configuración de la demo y del hook (sin modelo de evidencia) deja salir la clave entera en 10 de 18 combinaciones medidas.
  - La configuración evaluada, con el modelo de evidencia, rota al primer envío y no deja pasar más de 12 bits.
  - Cifras: [results/short_fragments/summary.md](results/short_fragments/summary.md).
- Rotar limita el daño; no impide que el agente lo intente.
- Alicanto supone que toda clave se puede rotar: el campo `rotatable` del manifiesto existe, pero hoy ningún código lo lee. Una clave que no se puede rotar sin romper algo, como una llave de firma, solo se protegería bloqueando y avisando a una persona; eso no está hecho.
- La cuenta compartida cubre a varios agentes en una misma máquina, cada uno con su propio proceso, a través de un archivo común, y se conserva entre sesiones; coordinar varias máquinas queda como trabajo futuro.
