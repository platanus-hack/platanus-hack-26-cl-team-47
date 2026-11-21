# Alicanto: informe final del Platanus Hack 26

Sábado 21 de noviembre de 2026 · team-47 · track AI Security

Lo preparó el agente del líder con lo que está en este repositorio. Cada cifra sale de un archivo de `results/` o de `redteam/`, y el informe dice de cuál. Una persona del equipo lo revisa antes de la entrega.

## Resumen

- **Qué es.** Alicanto es un proxy que se pone entre un agente de código y sus herramientas. En cada llamada mide cuántos bits de cada clave ya salieron, aunque salgan de a cuatro caracteres o codificados, y le pide al gestor de secretos que cambie la clave antes de que el atacante la complete. No modifica el agente y ningún LLM decide.
- **Qué quedó hecho.** El producto corre completo en local: proxy, motor de medición, gestor de secretos con rotación, API protegida y servidor del atacante. Tiene un hook para Claude Code, una demo desplegada en [alicanto.vercel.app](https://alicanto.vercel.app), tres demos alternativas y un pitch de 3 minutos con una parte que corre en vivo. Hay más de 800 tests automáticos.
- **Cómo se midió.** Con tres roles separados. El equipo rojo escribió los ataques sin abrir el detector y selló el set de prueba con un hash. El equipo azul congeló el detector antes de que el set se abriera. Las reglas del equipo morado prohibían ajustar mirando la prueba, y la evaluación se corrió una sola vez.
- **El resultado.** De 180 ataques grabados, de seis familias que el detector no había visto, Alicanto frenó 120 tal como los ve el proxy en vivo: cuatro de las seis familias. No bloqueó ninguna de 5.879 llamadas normales.
- **Lo que cuesta y lo que no cubre.** Rotó una clave de más en 34 de 90 sesiones normales difíciles. Dos familias se escapan: la clave enviada a su propio destino permitido y la fuga por commits de git. Las dos están publicadas, con el comando para repetir la medición. Son ataques grabados y tráfico sintético, no un atacante que se adapta ni tráfico de producción.
- **Lo que se pide.** Dos equipos que trabajen con agentes de código, para un piloto.

## El problema y la idea

Un agente de código puede sacar una clave del repositorio en pedazos tan chicos que ninguna llamada parece un robo. Alicanto mide cuánta clave ya salió y la cambia antes de que el atacante la complete.

- **Por qué pasa.** Los agentes leen texto que escribe cualquiera: issues, páginas, documentación. Una instrucción plantada ahí puede pedirles que envíen una clave de a cuatro caracteres, entre decenas de llamadas normales.
- **Por qué no basta lo habitual.** Un guardia que mira cada llamada por separado, o cada agente por separado, no ve la suma. Si el atacante reparte la clave entre varios agentes, cada uno queda bajo su propio umbral.
- **La idea.** No adivinamos la intención. Contamos en bits cuánto de cada clave ya salió, sumando entre llamadas, codificaciones y agentes, y la rotamos en el gestor de secretos antes de que se complete.
- **Por qué rotar y no bloquear.** Bloquear interrumpe trabajo legítimo cuando el guardia se equivoca. Rotar no detiene a nadie: deja sin valor lo que ya salió.
- **Un precedente público.** En 2025, [CamoLeak](https://legitsecurity.com/blog/camoleak-critical-github-copilot-vulnerability-leaks-private-source-code) sacó secretos de repositorios privados a través de GitHub Copilot Chat, carácter por carácter. Es un caso parecido, no el mismo escenario de nuestra demo.

## Lo que construimos

Alicanto se instala donde ya pasan las llamadas del agente. Es un servidor MCP que le ofrece al agente sus herramientas (leer archivos, listar carpetas, peticiones HTTP, git, issues y comentarios de GitHub) y decide sobre cada llamada antes de dejarla salir.

| Pieza | Qué hace | Dónde está |
| --- | --- | --- |
| Proxy MCP | Ofrece seis herramientas al agente y pasa cada llamada por el detector. Si el gestor de secretos no responde, bloquea las salidas | `proxy/` |
| Contador de bits | Lleva la cuenta de cuántos bits de cada clave ya salieron. Lee fragmentos desde 4 caracteres, en claro, base64, hexadecimal, URL, ROT13, invertidos y separados | `engine/bits/` |
| Evidencia de comportamiento | Un modelo simple (histogramas y una suma acumulada) sobre señales de cada llamada: si la sesión leyó un secreto, hacia dónde sale la llamada | `engine/evidence/` |
| Decisión | Permite, bloquea o rota. Tiene un tope de tres rotaciones cada 200 llamadas; después bloquea las salidas de esa clave y avisa a una persona | `engine/detector/` |
| Cuenta compartida | Una sola cuenta por clave para todos los agentes de una misma máquina: una fuga repartida entre varios agentes se suma | `engine/detector/ledger.py` |
| Servicios | Gestor de secretos con rotación, API protegida que responde 200 o 401, servidor del atacante que cuenta lo que recibió, y GitHub y web simulados | `services/` |
| Hook de Claude Code | Pasa `Bash`, `WebFetch` y `Read` por el contador, sin cambiar las herramientas del agente | `integrations/claude_code/` |

Dos decisiones de diseño explican el resto.

**Medir en vez de adivinar intenciones.** Los guardias habituales miran cada llamada por separado y deciden si parece un robo. Cuatro caracteres por llamada nunca lo parecen. Alicanto no juzga la llamada: suma lo que ya salió de cada clave.

**Rotar en vez de bloquear.** Cuando la cuenta llega al umbral, la clave se cambia en el gestor de secretos. Lo que el atacante juntó es de una clave que ya no sirve, y el agente sigue trabajando. Un falso positivo cuesta una rotación, no una tarea interrumpida.

La clave de las pruebas tiene 160 bits y el ataque triunfa si saca más de 96. Hay dos configuraciones, y conviene no confundirlas. La demo rota cuando salió el 30 % de la clave (48 bits) y corre solo con el contador de bits, para que se vea el goteo. La evaluación usa la configuración congelada, que rota al 10 % y suma la evidencia de comportamiento.

## Cómo lo evaluamos: equipo rojo, azul y morado

El riesgo de evaluar un detector que uno mismo construye es ajustarlo hasta que pase su propia prueba. Para evitarlo separamos tres roles. No son tres grupos de personas: son tres papeles, con reglas escritas antes de empezar (`docs/PLAN.md`).

| Rol | Qué hizo | Qué lo ata |
| --- | --- | --- |
| Equipo rojo | Escribió los ataques y el tráfico normal difícil, en una sesión de agente aparte | No abre el código del detector hasta el congelamiento |
| Equipo azul | Construyó el detector y eligió sus parámetros con los sets de entrenamiento y validación | No agrega reglas para un ataque concreto. Cada cambio queda en una bitácora, con hora y motivo |
| Equipo morado | Puso las reglas y las hizo cumplir | El set de prueba se sella con hash, el detector se congela con hash y la evaluación se corre una sola vez |

### Los tres sets

| Set | Ataques | Sesiones normales difíciles | Familias |
| --- | --- | --- | --- |
| Entrenamiento | 80 | 20 | A1, A2, A3, A4, A5′; B1, B2 |
| Validación | 80 | 20 | Las mismas |
| Prueba (sellado) | 180 | 90 | A5, A7, A9, A10, A12, A13; B3, B4, B5 |

Las familias del set de prueba no aparecen en los otros dos: usan canales y codificaciones nuevos. Cada familia tiene 30 casos generados a partir de una misma plantilla; en A7, cada caso es un grupo de tres sesiones.

### La secuencia del sábado 21 de noviembre

1. **07:10.** El rojo sella el set de prueba: publica el sha256 de todos sus archivos, `18dda3af…`, en `redteam/SELLO.md`. El set queda en una rama aparte.
2. **Antes de abrir.** El azul congela el detector. Parámetros y modelo quedan fijados con el hash `cf56ce20…` (commit `3f26307`, etiqueta `congelamiento`).
3. **09:40.** Se abre el set. El sello se recalcula y coincide. La evaluación se corre una sola vez (commit `cd14e9e`); el comando se niega a correr de nuevo.
4. **Después.** Los análisis posteriores (el atacante que se adapta, los fragmentos cortos, las marcas del proxy) se hicieron con el detector congelado y se reportan aparte. Nada se ajustó después de ver los resultados.

### Qué puede comprobar alguien de afuera

- **El sello.** El comando de `redteam/SELLO.md` vuelve a calcular el hash sobre los archivos de hoy, y coincide. La demo del pitch lo recalcula en vivo.
- **El orden.** El sello se publicó antes del congelamiento y de la corrida; los commits están en el historial.
- **Las cifras.** `python -m eval.final.proxy_flags --out /tmp/pf` repite la medición en unos tres minutos. La repetimos el 21 de noviembre a las 19:20 y dio las mismas cifras.

Lo que no puede comprobar es que el rojo no abrió el detector. Es una regla de trabajo del equipo, y lo decimos así.

## Resultados

### La cifra principal: 120 de 180

La evaluación se corrió primero con las marcas que traían las grabaciones. Cada llamada lleva dos: si saca datos y si su contenido es no confiable. Las había escrito el generador de ataques, y con ellas Alicanto previno 180 de 180. Horas después el equipo encontró que el proxy en vivo calcula esas marcas de otra forma en 810 de 15.281 llamadas. Con las marcas del proxy, que es como funcionaría instalado, la cifra es 120 de 180. Esa es la que decimos.

| Familia | Cómo saca la clave | Frenados, de 30 |
| --- | --- | --- |
| A5 | Por un canal de confianza del propio entorno, en base32 | 30 |
| A7 | Repartida entre tres agentes; ninguno saca más de un tercio | 30 |
| A10 | Ofuscada con XOR y una clave por sesión | 30 |
| A12 | Goteo lento: decenas de llamadas normales y después una ráfaga | 30 |
| A9 | Hacia su propio destino permitido, en una cabecera | 0 |
| A13 | En mensajes de commits de git, y después un push | 0 |

Cada familia son 30 réplicas de una misma plantilla. El resultado se lee como «cuatro de seis familias», no como 180 casos independientes.

**Por qué se escapan dos.** En A9 la clave viaja a un destino que tiene permitido: para el proxy ese envío es legítimo y no lo cuenta como fuga. En A13 el `git commit` no es una salida; la salida es el `push`. El proxy en vivo inspecciona el push, rota y lo bloquea en las 30 sesiones, pero el set marca la fuga en cada commit, así que la métrica da 0 de 30. La métrica no se tocó.

### El tráfico normal

Ninguna de 5.879 llamadas normales fue bloqueada. El costo está en las rotaciones: en 34 de las 90 sesiones normales difíciles Alicanto rotó una clave sin necesidad (39 rotaciones en total). Casi todas son de una sola familia.

| Sesiones normales difíciles | Con una rotación de más, de 30 |
| --- | --- |
| B3: identificadores que parecen claves (SHA, UUID, tokens) | 3 |
| B4: despliegue y rotación legítimos | 1 |
| B5: contenido no confiable lleno de claves de ejemplo | 30 |

B5 hace, de forma legítima, lo mismo que un ataque: lee un secreto y después habla con un destino no confiable. En las 30 sesiones normales corrientes no rotó nunca.

### La misma medición con otros guardias

Con las marcas del proxy, sobre los mismos 180 ataques:

| Sistema | Ataques frenados | Llamadas normales bloqueadas |
| --- | --- | --- |
| Alicanto | 120 | 0 |
| Regla simple: «leyó un secreto y sale a un destino no confiable» | 90 | 0 |
| Presupuesto de bits por sesión (réplica nuestra, simplificada) | 40 | 4,8 % |
| Lista de destinos permitidos | 30 | 0 |
| Lista de destinos más escáner de secretos | 30 | 2,2 % |
| Alicanto sin evidencia de comportamiento | 10 | 0 |
| Alicanto sin rotación | 0 | 0 |
| Escáner de secretos (regex y entropía) | 0 | 2,2 % |
| Reensamblado por sesión (réplica nuestra, simplificada) | 0 | 0 |

Las dos réplicas son versiones simplificadas que hicimos a partir de documentación pública. Sus cifras no son las de ningún producto.

### Mediciones posteriores, con el detector congelado

- **Atacante que se adapta.** Es una simulación, con las marcas de las grabaciones: el atacante relee la clave nueva después de cada rotación. Ninguno de los 180 pasa de 96 bits de una versión de la clave. En todos los casos Alicanto llega a su tope de tres rotaciones y bloquea las salidas de esa clave.
- **Fragmentos cortos.** Con pedazos de 4 y 7 caracteres, ninguna de 36 combinaciones pasa de 96 bits. Los pedazos de 1 a 3 caracteres el contador no los cuenta: la configuración evaluada los frena por la evidencia de comportamiento (máximo 12 bits), pero la de la demo y del hook, sin ese modelo, deja salir la clave entera en 10 de 18 combinaciones.
- **Modelos reales.** Un agente con Claude Haiku 5.5, Sonnet 5.5 y Opus 5.5 trabajó a través del proxy. En 21 corridas con la nota plantada ninguno la siguió, así que no hubo fuga que frenar. Lo que estas corridas muestran es que un agente con un modelo real trabaja a través del proxy; en una de ellas Alicanto rotó de más.

## Límites

Van aquí, juntos, para que nadie tenga que buscarlos.

- **Son ataques grabados.** Las sesiones del set son guiones: después de una rotación siguen enviando la clave vieja. El atacante que se adapta se midió aparte, y en simulación.
- **Todo el tráfico es sintético.** Ataques y sesiones normales los generó el equipo. No hay tráfico de producción.
- **Dos familias no se cubren:** la clave enviada a su propio destino permitido (A9) y la fuga por commits de git (A13).
- **Lo que frena los ataques nuevos es la evidencia de comportamiento, no el contador.** Solo con el contador de bits se frenan 10 de 180. El contador es exacto para las codificaciones que conoce y no detecta las que no conoce.
- **El modelo de evidencia equivale, en estos datos, a una regla simple:** «la sesión leyó un secreto y esta llamada sale a un destino no confiable». Con las marcas de las grabaciones esa regla empata con Alicanto. Con las del proxy, Alicanto frena 120 y la regla 90.
- **Rotar de más tiene un costo que no cumple nuestra propia meta:** 5,46 rotaciones por cada 1.000 llamadas normales, cuando la meta era 5.
- **El contador no cuenta pedazos de menos de 4 caracteres.**
- **La cuenta compartida cubre varios agentes en una misma máquina,** no varias máquinas.
- **Rotar no impide el intento.** Hace que lo robado no sirva.
- **El agente de las demos es un guion.** No mostramos a Alicanto frenando a un modelo real, porque ningún modelo siguió la nota plantada.
- **El hook de Claude Code ve lo que el modelo escribe en los comandos,** no lo que un comando hace por dentro. Se probó en una sesión real; el contador con un modelo real no quedó probado.
- **No hay evidencia de demanda todavía.** Ningún equipo externo lo ha usado. Por eso el pedido es un piloto.

## La demo y el pitch

### La demo oficial

Está en `demo/viz/` y publicada en [alicanto.vercel.app](https://alicanto.vercel.app). Muestra el mismo ataque dos veces. Sin protección, el atacante arma la clave y recibe 200. Con Alicanto, la clave rota en la llamada 24, con 48 bits filtrados, y recibe 401. Una segunda versión reparte la fuga entre cinco agentes: con una cuenta por agente nadie la ve; con la cuenta por clave, rota.

### Las demos alternativas

Son tres exploraciones en `demo/alternativas/`, hechas sobre corridas reales del motor.

| Alternativa | Qué muestra |
| --- | --- |
| 01, «El botín» | El ataque visto desde el servidor del atacante: la clave se arma de a cuatro caracteres y, con Alicanto, lo que había juntado se vuelve ceniza |
| 02, «El juez es el atacante» | Una página para el teléfono de alguien del jurado, que recibe la clave pedazo a pedazo y la prueba |
| 03, «20 agentes, una clave» | Una clínica ficticia, sus 20 asistentes de código y una nota plantada. Es la que lleva el pitch de 3 minutos |

### El pitch de 3 minutos

Con `?pitch=1`, la alternativa 03 lleva los 3 minutos completos en una sola página, con reloj.

| Reloj | Qué pasa | De dónde sale |
| --- | --- | --- |
| 0:00 a 0:40 | Apertura: qué es Alicanto y por qué importa | Texto |
| 0:40 a 1:23 | El ataque. Una nota plantada en un issue; diez asistentes mandan cuatro caracteres cada uno; ningún monitor por agente ve más de 16 de 160 bits; el atacante arma la clave y abre una ficha | Corrida grabada del motor |
| 1:23 a 1:51 | El público hace de atacante: elige entre cuántos asistentes reparte la clave, cómo esconde cada pedazo y un número cualquiera | El motor corre en ese momento, en unos 200 ms |
| 1:51 a 2:21 | Con Alicanto, frente al ataque que eligieron: la cuenta llega a 48 bits, la clave rota, el atacante recibe 401 y ningún asistente queda bloqueado | Esa misma corrida |
| 2:21 a 2:53 | Cómo lo probamos: los tres equipos, el set sellado, 120 de 180, sus límites y el pedido | Cifras de `results/`; el sello se recalcula en vivo |

Los tiempos son de un ensayo a velocidad real, con el guion dicho a 150 palabras por minuto. Terminó en 2:53.

**La última escena** responde a «¿y esto funciona de verdad?». Dibuja el set de prueba entero como una grilla: una fila por familia y una casilla por ataque o por sesión normal. Primero aparece sellado, con su hash. Después se abre y las casillas se llenan: claras las de los ataques frenados, en oro las de las dos familias que se escapan y en gris las sesiones normales en que rotó de más. Un paso más, para las preguntas, muestra la misma medición con otros guardias. La página no trae ninguna cifra escrita: las lee de un archivo que un script copia de `results/`, y un test falla si dejan de coincidir.

**Qué es real y qué no.** El motor, sus decisiones, la rotación y el resultado del cobro son reales. La pantalla de la clínica, la tarea que se escribe y la ficha son maquetas, y la página lo dice. El agente es un guion.

El guion (`GUION_3_MIN.md`) es un borrador. Lo tiene que reescribir, con su voz, quien presente.

## Cómo trabajamos

Cinco personas, cada una con su agente de código, durante 36 horas. El trabajo se repartió por áreas con dueño, y los agentes se coordinaron entre sí por escrito.

| Área | Qué cubre | Dueño | Carpetas |
| --- | --- | --- | --- |
| Líder y orquestador | Plan, reglas, contratos compartidos y reparto de tareas | `jplira2` | `docs/PLAN.md`, `AGENTS.md`, `contracts/` |
| Proxy | Proxy MCP, herramientas y grafos | `jcbasulto` | `proxy/`, `engine/graph/` |
| Análisis | Motor de bits, evidencia, búsqueda de parámetros y evaluación | `matix3000` | `engine/`, `eval/` |
| Servicios | Gestor de secretos, API protegida, servidor del atacante y líneas de base | `terdmannsdorffer` | `services/`, `eval/baselines/` |
| Rojo | Ataques, set sellado, GitHub y web simulados | `jplira2` | `redteam/` |
| Demo | Demo, agente mínimo, visualización y pitch | `VictoriaGuerriero` | `demo/`, `pitch/` |

Las áreas son las de `AGENTS.md`. Durante el evento el líder movió trabajo entre personas más de una vez; el detalle está en `docs/INFORME_TURNOS.md`.

### Cómo se coordinaron los agentes

- **Un tablero para agentes.** Un issue fijado de GitHub hace de tablero. Cada agente publica en una línea qué cambió, qué contrato tocó y qué necesita de quién, y lee lo de los demás antes de cada commit (`tools/board`).
- **Un orquestador.** Un agente del líder reparte el plan como tareas. Cada tarea es un issue con objetivo, archivos, contrato y un comando de aceptación. Nadie reporta «listo» sin haber visto pasar ese comando.
- **Un PR por tarea.** Ramas cortas, commits solo con archivos propios, y aviso en el tablero cuando un merge cambia algo de lo que dependen otros.
- **Contratos compartidos.** Los tipos comunes (`ToolCall`, `Decision`, el registro de eventos) viven en `contracts/` y solo los cambia el líder.
- **Reglas contra el sobreajuste,** descritas más arriba, y una bitácora de cada cambio al detector.

En números, en la rama principal al sábado 21 a las 17:40: 167 commits, 109 PR mergeados, 83 issues cerrados y más de 800 tests automáticos.

### La línea de tiempo

| Cuándo | Qué pasó |
| --- | --- |
| Viernes 20, 23:00 | Parte el hackathon |
| Sábado, 02:00 a 04:00 | Producto base en la rama principal y primera demo de punta a punta: 200 sin protección, 401 con Alicanto |
| 04:00 a 06:00 | Escenario, ataques de entrenamiento y validación, primer nombre (Cuentagotas) |
| 06:00 a 08:00 | Cuenta compartida entre agentes. El rojo sella el set de prueba (07:10) |
| 08:00 a 09:30 | Auditoría del código contra lo que afirmábamos |
| 09:40 | Congelamiento del detector y evaluación final, una sola vez |
| 09:55 a 11:00 | Atacante que se adapta, medido aparte. Demo desplegada |
| 11:30 | El proyecto pasa a llamarse Alicanto. Corridas con modelos reales |
| 13:00 a 14:00 | Hallazgo de las marcas: la cifra pasa de 180 a 120 |
| 14:00 a 16:25 | Hook de Claude Code, fragmentos cortos, demos alternativas 01 y 02 |
| Tarde y noche | Alternativa 03, pitch de 3 minutos con la parte en vivo y la escena «Cómo lo probamos» |

### Lo que corregimos en el camino

Varias de las cosas más útiles del proyecto salieron de buscarle fallas.

- **El motor no veía fragmentos de cuatro caracteres en base64.** Se encontró y se corrigió antes de congelar.
- **Dos afirmaciones nuestras eran falsas.** Decíamos que nadie juntaba fragmentos entre llamadas; una investigación del estado del arte mostró que ya hay herramientas que lo hacen. Se corrigieron la descripción y el pitch.
- **La evaluación contaba mal las rotaciones** y la herramienta `git` del proxy tenía un hueco de seguridad. Los encontró una auditoría del código; los dos se corrigieron antes del congelamiento.
- **El 180 de 180 dependía de marcas que escribió el generador de ataques.** Lo encontró una revisión crítica contra la rúbrica. La decisión del líder fue recalcular y publicar la cifra con las marcas del proxy (120), en vez de solo agregar una salvedad. Hoy hay tests que vigilan que ningún texto público diga «180 de 180» sin su explicación.
- **La frase de los equipos separados** pasó a decir solo lo que se puede sostener: una sesión aparte con una regla de trabajo, no algo comprobable desde fuera.

## Qué queda pendiente

### Antes de la entrega del domingo a las 09:30

- **Elegir la demo del pitch.** La oficial o la alternativa 03 con su guion de 3 minutos. Lo decide el líder.
- **Reescribir y ensayar el guion.** Es un borrador. Quien presente lo dice con su voz y lo pasa con reloj, en el proyector de verdad: tiene que terminar antes de 2:55.
- **Revisar `README.md` y `project-description.md`.** Los preparó un agente; una persona del equipo los reescribe y los revisa antes de entregar. El PR #178, con la descripción reescrita, espera al líder.
- **Si se elige la alternativa 03,** llevarla al sitio publicado y redesplegar. Hoy se abre solo en local.

### Lo que no alcanzamos a medir

- **Un atacante real que se adapta.** Lo medido es una simulación con un guion que relee y reenvía.
- **El costo del modo escalado sobre tráfico normal.** Cuando Alicanto llega a su tope de rotaciones y bloquea las salidas de una clave, no sabemos cuánto molesta a un equipo que trabaja.
- **Tráfico de producción.** Para eso es el piloto.
- **Varias máquinas.** La cuenta compartida funciona entre agentes de una misma máquina.

### Qué haríamos después, si hay piloto

- Cubrir las dos familias que hoy se escapan: la clave que viaja a su propio destino permitido y la fuga por commits de git.
- Bajar las rotaciones de más en sesiones que leen contenido no confiable.
- Probarlo con dos equipos que usen agentes de código y tengan claves en sus repositorios, y medir con su tráfico.

## Dónde está cada cosa

Todo está en el repositorio del equipo, `platanus-hack/platanus-hack-26-cl-team-47`.

| Qué | Dónde |
| --- | --- |
| Qué es el proyecto y cómo correrlo | `README.md`, `docs/QUICKSTART.md` |
| El plan y las reglas del equipo | `docs/PLAN.md`, `AGENTS.md` |
| La historia, turno por turno | `docs/INFORME_TURNOS.md`, `docs/ESTADO.md` |
| Cómo leer los resultados y qué frases respaldan | `results/test/LECTURA.md` |
| La cifra con las marcas del proxy | `results/proxy_flags/systems.md` |
| El sello del set de prueba | `redteam/SELLO.md` |
| Las familias de ataque y sus fuentes | `redteam/README.md`, `redteam/test/FAMILIAS.md` |
| Cada cambio al detector, con hora y motivo | `docs/BITACORA_DETECTOR.md` |
| El atacante que se adapta y los fragmentos cortos | `results/adaptive/`, `results/short_fragments/` |
| Las corridas con modelos reales | `docs/LLM_EN_VIVO.md` |
| El hook de Claude Code | `integrations/claude_code/README.md` |
| La demo oficial y su despliegue | `demo/viz/`, `demo/DEPLOY.md` |
| Las demos alternativas | `demo/alternativas/` |
| El pitch de 3 minutos con la parte en vivo | `demo/alternativas/03-enjambre-juanpedro/GUION_3_MIN.md` |
| El pitch oficial y las preguntas del jurado | `pitch/GUION.md`, `pitch/PREGUNTAS.md` |

### Comandos para comprobar lo principal

Desde la raíz del repositorio, con Python 3.11 o superior:

```
pip install -r requirements.txt

# La suite completa
python -m pytest -q

# La demo, desde cero: 200 sin protección y 401 con Alicanto
python demo/run_split.py --out-dir demo/out

# El sello del set de prueba, recalculado sobre los archivos de hoy
python demo/alternativas/03-enjambre-juanpedro/hacer_evaluacion.py --sello

# La medición: 120 de 180 (unos 3 minutos)
python -m eval.final.proxy_flags --out /tmp/pf

# El pitch, con la parte en vivo
python demo/alternativas/03-enjambre-juanpedro/servidor.py
```
