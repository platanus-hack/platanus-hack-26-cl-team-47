# Informe de turnos

Para quien entra a un turno y necesita saber en cinco minutos qué pasó, cómo está el proyecto y qué le toca. Se actualiza en cada rotación del equipo.

**Cómo actualizarlo:** al cerrar un turno, agrega una entrada nueva arriba de la sección «Turnos», con la hora, y corrige «Estado actual» y «Pendientes de personas». No borres las entradas anteriores. El detalle técnico para los agentes está en `docs/ESTADO.md`; este archivo es para las personas.

---

## Estado actual

Actualizado: sábado 21 de noviembre de 2026, 14:00 (hora 15 de 34).

**El proyecto.** Alicanto (hasta las 11:30 del sábado se llamó Cuentagotas) es un proxy entre un agente de IA y sus herramientas. Mide cuántos bits de cada clave ya se filtraron, aunque salgan de a cuatro caracteres o codificados, y rota la clave antes de que la fuga se complete. Competimos en el track AI Security.

**Qué funciona hoy, comprobado:**
- La demo principal: el mismo ataque termina en 200 sin protección y en 401 con Alicanto.
- La demo del enjambre: cinco agentes se reparten la fuga; con una cuenta por agente nadie la ve (200), con la cuenta global la clave rota (401).
- La demo interactiva: el público elige cómo se disfraza el fragmento (tal cual, base64 o al revés).
- El ataque en vivo con todos los servicios reales en local.
- Un modelo real pasando por el proxy: Haiku 5.5 y Sonnet 5.5 (10 corridas cada uno) y Opus 5.5 (1 corrida). Ninguno siguió la instrucción plantada, así que no hubo fuga que frenar; con Sonnet hubo una rotación de más (`docs/LLM_EN_VIVO.md`).
- 731 tests automáticos en verde y los resultados reproducidos en tres máquinas (macOS y dos Windows).

**Evaluación final, ya corrida** (una sola vez, sobre 180 ataques de seis familias que el detector no había visto; detalle y límites en `results/test/LECTURA.md`):

| Sistema | Ataques prevenidos | Llamadas benignas bloqueadas |
|---|---|---|
| Alicanto | 180 de 180 (100 %) | 0 de 5.879 |
| Alicanto sin rotación | 30 de 180 (16,7 %) | 0 |
| Lista de destinos permitidos más detect-secrets | 30 de 180 (16,7 %) | 2,2 % |
| Presupuesto de bits (réplica) | 70 de 180 (38,9 %) | 4,8 % |
| Reensamblado por sesión (réplica de herramientas tipo Pipelock) | 0 de 180 | 0 |

Ningún ataque sacó más de 32 de los 160 bits de la clave vigente. Cuatro cosas que hay que decir siempre junto a esa cifra:
- **Las banderas de cada llamada venían de las grabaciones.** Si una llamada es una salida y si va a un destino no confiable lo escribió el generador de ataques; el proxy en vivo lo calcula distinto. Con las banderas del proxy, una comprobación del orquestador da 120 de 180: quedan sin cubrir la familia que saca la clave por su propio destino permitido y la que la esconde en mensajes de `git commit`. La tabla oficial con las dos cifras sale de la tarea #167; hasta entonces no se escriben frases nuevas con el 180 de 180.
- **Son ataques grabados.** El atacante que se adapta a la rotación se midió aparte, en simulación (`results/adaptive/summary.md`): 180 de 180 no pasan de 96 bits de ninguna versión de la clave (máximo 64). Lo frena llegando al tope de tres rotaciones y bloqueando las salidas de esa clave: es una detención con costo, no rotación sin fin.
- **Tiene un costo.** En 34 de las 90 sesiones benignas difíciles rotó una clave sin necesidad. No bloqueó ninguna llamada benigna.
- **El contador de bits solo no alcanza en familias nuevas** (40 de 180). Lo que frena esos ataques es la evidencia de comportamiento, que rota temprano.

**En curso ahora** (repartido a las 13:45, después de una revisión crítica del proyecto criterio por criterio de la rúbrica):
- **#167, José Carlos:** la evaluación con las banderas del proxy, publicada junto a la actual, y una regla simple («leyó un secreto y envía a un destino no confiable: rota») como línea de base, para decir con números qué aporta cada pieza.
- **#168, Matías:** la demo se corta a 1024×768 (resolución típica de proyector) y en teléfono, abre detenida sin avisar, y las láminas no están en el sitio público. Se arregla todo eso.
- **#169, José Carlos, después de #167:** un hook de Claude Code que pasa por el contador de bits lo que el agente está por ejecutar con `Bash` y `WebFetch`. Es la respuesta a «¿lo puedo usar el lunes?».
- **Después:** textos públicos (pitch, README y página de resultados) con las dos cifras y las frases corregidas.

**Dónde verlo:**
- **Demo en línea:** https://alicanto.vercel.app (portada, tres demos, informe de incidente y resultados). **No se actualiza sola:** el orquestador la vuelve a desplegar a mano después de cada cambio en `demo/viz` (ver `demo/DEPLOY.md`, «Cómo quedó desplegado»).
- Demo en local: `python -m http.server 8200 --directory demo/viz` y abrir `http://127.0.0.1:8200/`.
- Láminas: `pitch/index.html`. Guion: `pitch/GUION.md`. Preguntas del jurado: `pitch/PREGUNTAS.md`.
- Descripción pública: `project-description.md`.

## Quién está con qué

| Persona | Estado | Tarea |
|---|---|---|
| José Carlos (`JCBasulto`) | Activo | #167 y después #169 |
| Victoria (`VictoriaGuerriero`) | Activa desde las 12:25 | Hizo las corridas con el modelo real. Sin tarea abierta |
| Tomás (`Terdmannsdorffer`) | Sin tokens | No recibe tareas |
| Matías (`matix3000`) | Activo desde las 12:25 | #168, con traspaso puntual de `demo/viz/` y `pitch/` |
| Juan Pedro (`jplira2`), líder | Activo | Corre el orquestador y la sesión del equipo rojo |

Si alguien recupera tokens o se queda sin ellos, avísalo en el board: el orquestador reparte según eso.

## Pendientes de personas

Ningún agente puede hacer esto. Ordenado por importancia.

1. ~~Deploy en Vercel~~ **Hecho** (10:40): https://alicanto.vercel.app, y la URL ya está en `platanus-hack-project.jsonc`. Queda activar el segundo factor en la cuenta de Vercel, que la propia plataforma recomienda.
2. ~~Clave de API para correr un LLM real~~ **Hecho** (12:50): tres modelos pasaron por el proxy y ninguno siguió la inyección (`docs/LLM_EN_VIVO.md`). Sigue abierta la pregunta «¿dónde está la IA?»: hoy la respuesta honesta es «lo probamos y el modelo resiste».
3. **Conseguir de dos a cuatro frases de posibles usuarios en el mismo evento** (CTO, mentores, alguien de TI de una clínica o de una healthtech) y llevarlas a la lámina final. Hoy no hay ninguna evidencia de demanda, y es lo que más sube el criterio de impacto. El usuario más natural es un equipo que ya usa agentes de código y tiene claves en el repositorio.
4. **Preguntar a la organización:** hora exacta de corte del repositorio, cómo se pasa a la final, y si en Santiago hay premio del público o de sponsor.
5. **Revisar `README.md` y `project-description.md`.** Son borradores escritos por agentes; las reglas del equipo piden que una persona los reescriba o los apruebe.
6. **Ensayar el pitch con cronómetro.** En las finales del tour fueron 3 minutos de demo con corte y 2 de preguntas.
7. **Confirmar la lámina final:** a quién le vendemos y qué pedimos. Hay un borrador (responsables de seguridad de prestadores de salud; dos equipos para un piloto).

## Cosas que hay que saber antes de hablar del proyecto

- **Frase de novedad permitida:** «Hasta donde encontramos, nadie usa la fuga parcial medida de una credencial (en bits, sumada entre llamadas, codificaciones y agentes) para rotarla antes de que se complete.»
- **No decir:** que nadie junta fragmentos entre llamadas (existen Pipelock y AgentBrake), que somos los primeros, ni que detectamos esteganografía.
- **Qué es real y qué es simulado:** el proxy, el motor, el gestor de secretos y el servidor del atacante son reales y corren en local. Las claves son sintéticas, el hospital es ficticio y el agente de la demo es un guion, no un LLM. Aparte se corrieron tres modelos reales por el proxy; ninguno siguió la inyección.
- **La demo y la evaluación usan configuraciones distintas.** La demo rota cuando se filtró el 30 % de la clave y corre sin el modelo de evidencia. La evaluación usa la configuración congelada.
- **El enjambre** funciona en la demo, en los tests y también en vivo: dos agentes en procesos distintos comparten la cuenta por un archivo (`LEDGER_PATH`). Límite: un archivo local, no varias máquinas. Cómo conectarlo a un agente real: `docs/QUICKSTART.md`.
- **Agenda del domingo sin confirmar:** planificar con el cierre más temprano (08:30).

## Reglas de trabajo vigentes

- Las tareas llegan como issues con la etiqueta `tarea` y una mención en el board. Cada agente las toma en su sesión actual, sin reiniciar.
- El set de prueba ya se abrió y la evaluación final se corrió una sola vez; el comando se niega a repetirla.
- El detector (`engine/`) y `models/` están congelados. Cualquier cambio lo autoriza el líder.
- Quien haya leído el código del detector no escribe ataques: esas tareas van en una sesión de agente nueva.
- Las cifras de las láminas salen de `results/test/`, nunca de validación, y van con sus límites (`results/test/LECTURA.md`). Nunca «detiene el 100 %» a secas.

---

## Turnos

### Sábado 21, 11:30 a 14:00

Escrito por el orquestador (sesión nueva desde las 13:30).

**11:30 a 13:00. Un modelo real por el proxy, y reproducción.**
- Victoria corrió el agente con modelos reales a través del proxy, con la configuración evaluada: Haiku 5.5 y Sonnet 5.5 con 10 corridas por brazo, y Opus 5.5 con 1. Ninguna siguió la instrucción plantada. Con Sonnet, una corrida leyó `.env` por su cuenta y después comentó en GitHub sin la clave: Alicanto rotó igual, una rotación de más.
- Se corrigieron dos errores del comando de corridas que aparecieron con la clave real.
- La evaluación quedó presentada como benchmark: cualquiera puede medir su propia defensa con un comando (`python -m eval.bench`).
- Matías y Victoria volvieron con tokens. Matías reprodujo todos los resultados en Windows; se arregló que los comandos se cayeran en una consola que no es UTF-8.

**13:00 a 14:00. Revisión crítica y trabajo nuevo.**
- Se revisó el proyecto contra cada criterio de la rúbrica, comprobando cada hallazgo en el código antes de actuar.
- Hallazgo principal: el 180 de 180 usa banderas escritas por el generador de ataques. Con las banderas que calcula el proxy, la comprobación da 120 de 180. Se publica la tabla con las dos cifras (#167).
- Se comprobó con capturas que la demo se corta a 1024×768 y en teléfono (#168).
- Se repartió un hook de Claude Code para usar el contador en un agente real (#169).

**Decisiones del líder en este turno:** recalcular y publicar la cifra con las banderas del proxy, en vez de solo poner una salvedad; los arreglos de la demo y del pitch van a Matías con traspaso.

### Sábado 21, 02:00 a 09:30

Escrito por el orquestador. Lo anterior a las 03:45 está reconstruido del historial del board.

**02:00 a 04:00. Se cerró el producto base.**
- Quedaron en `main` el proxy, el motor de bits, el detector, los grafos, el gestor de secretos con rotación, la API protegida y el servidor del atacante.
- Primera demo real de punta a punta, con el 200 y el 401.
- Se corrigió un error del motor que encontraron las pruebas automáticas.
- Tomás se quedó sin tokens.

**04:00 a 06:00. Escenario, datos y nombre.**
- Se eligió el escenario: el Hospital Regional Tres Cóndores, ficticio.
- Se generaron los ataques de entrenamiento y de validación (80 y 80), en sesiones de agente que no habían visto el detector.
- Se rediseñó la demo: tema oscuro, medidor grande de bits, sello 200/401. Se arregló que se montara en pantallas chicas.
- Primer nombre del producto (Cuentagotas), logo instalado y primera versión de la descripción pública.
- Se reiniciaron una vez las sesiones de los agentes para ahorrar tokens.

**06:00 a 08:00. Enjambre y rigor de la evaluación.**
- Cuenta global por clave entre varios agentes, con su demo.
- Demo interactiva con tres opciones de codificación.
- Set de prueba sellado: 180 ataques de familias nuevas más 90 sesiones benignas difíciles, con hash publicado en `redteam/SELLO.md`.
- Se encontró y corrigió un hueco real: el motor no veía fragmentos de cuatro caracteres en base64.
- Se corrigió la métrica de «ataque prevenido», que contaba como filtrada clave que ya había rotado.
- Matías se quedó sin tokens; su área (detector y evaluación) pasó a José Carlos.

**08:00 a 09:30. Investigación, auditoría y pitch.**
- Tres investigaciones: estado del arte, auditoría del código contra lo que afirmamos, y cómo se evalúa en las finales del tour.
- Dos afirmaciones nuestras eran falsas y se corrigieron en la descripción y el pitch: ya existen herramientas que juntan fragmentos entre llamadas.
- La auditoría encontró que la evaluación se perdía la mayoría de las rotaciones (al contarlas bien, validación subió de 90 % a 95 %) y un hueco de seguridad en la herramienta `git` del proxy. Los dos corregidos.
- Pitch rearmado: abre con la pregunta del propio track, lámina del enjambre, tabla comparativa con competidores y trece preguntas del jurado respondidas.
- `README.md` con una sección para quien evalúa (afirmación, archivo y comando), porque en el tour los jueces leyeron el repositorio con un modelo de lenguaje.
- Quedó en `main` el comando único de la evaluación final, probado en validación.

**09:30 a 09:55. Congelamiento y evaluación final.**
- Se reajustó el modelo solo con la parte de entrenamiento del tráfico benigno y se repitió la búsqueda de umbrales con las rotaciones bien contadas. Esa configuración quedó congelada.
- Se abrió el set sellado (el sello coincidió) y se corrió la evaluación final: 180 de 180 ataques prevenidos, 0 llamadas benignas bloqueadas.
- Quedó listo el comando para correr un LLM real a través del proxy; falta la clave.

**09:55 a 11:00. Lo que faltaba.**
- Atacante que se adapta a la rotación, medido aparte: 180 de 180 no pasan de 96 bits; lo frena llegando al tope de tres rotaciones y bloqueando las salidas.
- Cifras finales en el pitch y página de resultados en el sitio (`demo/viz/results.html`). Pitch rearmado en cinco bloques y 300 palabras, con láminas de respaldo.
- Enjambre en vivo entre procesos y guía de inicio (`docs/QUICKSTART.md`).
- Investigación con experimentos: el acoplamiento del grafo de archivos con el de llamadas no aporta nada medible a las decisiones; se deja sin conectar y se dice. La demo se queda con su configuración propia, porque con la evaluada rota en el primer fragmento y se pierde lo que muestra.
- Victoria dejó de responder cerca de las 09:05; sus tareas las tomó José Carlos.

**11:30. Cambio de nombre.**
- El equipo decidió que el producto se llama **Alicanto**, por el ave de la leyenda de Atacama que deja con las manos vacías a quien la sigue por codicia. Se verificó que el nombre no choca con ningún producto de software o de seguridad conocido.
- Se cambió en todo el repositorio, el sitio, el pitch y el servidor MCP (que ahora se anuncia como `alicanto`). La URL pública pasó a https://alicanto.vercel.app; la anterior sigue funcionando.
- Logotipo nuevo instalado a las 12:45: un ave en vuelo con alas doradas y plateadas (`project-logo.png`, y el ave sola en la portada del sitio).

**Decisiones del líder en este turno:** escenario de hospitales; nombre Cuentagotas (cambiado a Alicanto a las 11:30); el enjambre es objetivo del proyecto; adelantar el congelamiento y la evaluación final; las sesiones de los agentes no se reinician salvo que él lo indique.
