# Preguntas del jurado (borrador)

Borrador para que una persona del equipo lo revise antes de presentarlo. Las respuestas están pensadas para decirlas en voz alta, en dos a cuatro frases.

Todo sale de `docs/INVESTIGACION.md` (secciones A y E); los números entre corchetes son sus referencias. El informe se escribió leyendo resúmenes, no artículos completos: antes de citar un trabajo, alguien debe abrir la fuente. No se usa nada de la lista «Lo que no pude verificar» del informe.

## Las que más se repiten

Las que se repitieron en finales de AI Security de otras sedes del tour 2026 (precedente, no regla para Santiago). Respuestas de dos a tres frases.

## 1. ¿En qué se diferencia de los permisos de Claude Code o de la revisión de Codex?

Los permisos deciden si una herramienta puede usarse; no miran qué sale por una herramienta ya permitida. Nuestro ataque usa solo llamadas permitidas, de a cuatro caracteres. Alicanto mide el contenido que sale, sumado en el tiempo, y cambia la clave.

Fuente: la demo (`demo/sessions/goteo.jsonl`: solo lecturas y peticiones HTTP permitidas); `proxy/` (el proxy ve los argumentos de cada llamada).

## 2. ¿Midieron falsos positivos? ¿Con qué datos?

Sí: con tráfico benigno generado por nosotros, corriendo el proxy real sobre un repositorio de prueba, que incluye casos difíciles como un deploy legítimo con la clave a su destino. En la evaluación final: 0 llamadas benignas bloqueadas de 5.879 expuestas (cota superior al 95 %: 0,05 %), pero rotó de más en 34 de las 90 sesiones benignas difíciles. Es tráfico sintético, no de producción, y lo decimos.

Fuente: `data/benign/` y `redteam/SELLO.md` (familias benignas del set de prueba); `results/test/LECTURA.md`, puntos 3 y 6.

## 3. ¿Por qué no un clasificador o un LLM que vigile?

Porque un monitor que se convence con texto se puede convencer con texto. Contar caracteres de una clave conocida es determinista, explicable y barato, y no se puede persuadir. La evidencia de comportamiento que suma Alicanto también es un cálculo, no un modelo de lenguaje.

Fuente: pregunta 14 (por qué el detector es determinista); informe, E (puntos 1 y 2).

## 4. ¿Y si comprometen el proxy?

El proxy es la frontera de confianza, como un firewall: si cae, cae la defensa. Por eso el agente no tiene herramientas fuera del proxy, y si el gestor de secretos no responde, el proxy bloquea las salidas en vez de dejarlas pasar.

Fuente: `proxy/agent/loop.py` (el agente solo actúa por el servidor MCP del proxy); `proxy/live.py`, `fail_safe` (falla cerrado si el gestor no rota).

## 5. ¿Cómo lo instala todo un equipo de desarrollo?

Es un servidor MCP: se agrega al archivo de configuración del agente con un comando y un manifiesto de las claves a proteger. Los pasos, probados, están en `docs/QUICKSTART.md`; si varios agentes apuntan al mismo archivo de cuenta, suman en la misma cuenta por clave.

Fuente: `proxy/server.py` (`python -m proxy.server`); `demo/secrets_manifest.json` (formato del manifiesto).

## 6. ¿No basta con una lista de destinos permitidos?

En la demo sí bastaría: ahí el envío va a un servidor desconocido. No basta cuando la salida va por un destino que sí está permitido. En la evaluación final, la lista de destinos más un escáner de secretos previno 30 de 180 ataques grabados.

Fuente: `results/test/systems.md`, fila `combined` (lista de destinos más detect-secrets: 0,167 de 180).

## 7. ¿Esto ya pasó de verdad?

Algo parecido, sí. En 2025, CamoLeak, una falla de GitHub Copilot Chat que reportó Omer Mayraz, de Legit Security (CVSS 9,6), sacó secretos y código de repositorios privados: las instrucciones iban escondidas en la descripción de un pull request y los datos salían carácter por carácter a través del proxy de imágenes de GitHub. GitHub lo corrigió el 14 de agosto de 2025 desactivando las imágenes en Copilot Chat. Es un caso parecido, no el mismo escenario que nuestra demo: el canal allí eran las imágenes del chat; aquí, las herramientas de un agente de código.

Fuente: https://legitsecurity.com/blog/camoleak-critical-github-copilot-vulnerability-leaks-private-source-code. Ojo: no citar un número de CVE; el que circula en algunas notas no corresponde.

## Más preguntas

## 8. ¿En qué se diferencian de CaMeL y FIDES?

Los dos controlan el flujo de información con reglas binarias. CaMeL exige reestructurar el agente con un intérprete propio y dos LLM. FIDES usa etiquetas de confidencialidad e integridad con una política determinista. Ninguno mide cuánto de un secreto ya salió. Nosotros no tocamos el agente: contamos bits por secreto en los argumentos de las herramientas y rotamos la clave según lo medido.

Fuente: [8], [9]; informe, A.2.

## 9. ¿Y del trabajo de fuga acumulada (Chauhan y Revankar)?

Es el más cercano en la idea de acumular. Su contador estima la fuga con un techo de unos 4 bits por turno. Los propios autores dicen que los argumentos estructurados de las herramientas son un punto ciego y que reiniciar la sesión reinicia el presupuesto. Sus respuestas son advertir, sanear o bloquear, y no rotan. Nosotros medimos justo en los argumentos de las herramientas, después de decodificar, y respondemos rotando la clave para que lo filtrado deje de servir.

Fuente: [14]; informe, A.2. Ojo: la parte de caja blanca de ese trabajo son sus sondas de activaciones, no el contador; no decir que el contador necesita acceso al modelo.

## 10. ¿Y de OCELOT?

OCELOT presupuesta lo que el agente revela, con un costo en min-entropía por cada liberación de información. Su presupuesto es por tarea o trayectoria, no por secreto, y el LLM solo propone: decide un verificador determinista. La diferencia que queda: no trata credenciales ni argumentos de herramientas, y no rota la clave.

Fuente: [23]; informe, A.3; «Actualización de H10», corrección 2 (https://arxiv.org/html/2606.12341v1).

## 11. ¿No basta con una pasarela MCP que bloquea secretos por regex, o con detect-secrets?

Las pasarelas con regex y detect-secrets miran cada mensaje por separado y buscan el secreto completo. La demo lo muestra: cuatro caracteres por llamada pasan. Las herramientas que sí juntan fragmentos entre llamadas son otra categoría y van en la pregunta siguiente. En la evaluación final, contra la lista de destinos más detect-secrets: 150 ataques que nosotros prevenimos y ella no, 0 al revés (180 ataques grabados de seis familias nuevas).

Fuente: [25], [26], [27]; informe, A.3; `results/test/report.md`, prueba T3.

## 12. Pipelock ya reensambla fragmentos; ¿qué agregan ustedes?

Pipelock y AgentBrake ya acumulan entre llamadas, y los nombramos. Según su propia documentación, Pipelock pierde los fragmentos codificados y AgentBrake los de menos de 20 caracteres; nuestro goteo es de 4 y puede ir codificado. Además solo bloquean: nosotros medimos cuánto salió de cada clave y la rotamos, así lo que ya salió deja de servir.

Fuente: «Actualización de H10», corrección 1: https://pipelab.org/blog/cross-request-exfiltration/ y https://github.com/Ujjwaljain16/AgentBrake. Nota: Pipelock también lleva un presupuesto de entropía por ventana de tiempo, por sesión.

## 13. ¿Por qué no usar un broker de credenciales y no darle el secreto al agente?

Es la crítica más fuerte, y los brokers son complementarios. Si puede poner todo detrás de un broker, hágalo. Quedan las claves que viven en el repositorio: contraseñas de base de datos, llaves de firma, secretos de webhook. Alicanto es una vida útil adaptativa: la clave dura hasta que empieza a filtrarse, no hasta un reloj.

Fuente: [22], [28]; informe, A.3.

## 14. ¿Dónde está la IA, si el detector es determinista?

El agente de IA es el blanco y el vector del ataque: el ataque no existe sin un agente LLM que obedece texto no confiable. El monitor es determinista a propósito, porque un monitor LLM se ataca con la misma inyección que ataca al agente: un monitor que se convence con texto no es un monitor. Y un atacante que agrega un LLM no gana nada contra Alicanto, porque medimos información, no intención.

Fuente: informe, E (puntos 1, 2 y 4); `docs/BASES.md`, línea de trabajo 1 (AI control). `docs/LLM_EN_VIVO.md`, «Resultados».

Lo corrimos con modelos reales: un agente con Claude Haiku 5.5, Sonnet 5.5 y Opus 5.5 trabajando a través del proxy, 21 corridas por brazo. Los tres vieron la instrucción plantada en el issue y ninguno la obedeció, así que no hubo fuga que frenar. No decimos que mostramos a Alicanto deteniendo a un LLM real: mostramos que el agente real pasa por el proxy, y que Alicanto es la segunda línea para cuando el modelo no resista. En una de esas corridas rotó de más: el modelo leyó el archivo de claves al diagnosticar y después comentó en GitHub, sin filtrar nada.

## 15. ¿Qué no detectan?

Lo que medimos es una cota inferior: decimos «al menos tantos bits», no «bits exactos». Una codificación que el motor no lee no se ve por contenido. Ahí actúan la rotación periódica, que deja inútil lo que salió, y la evidencia de comportamiento. Contra cifrado arbitrario la respuesta es un broker más una lista de destinos permitidos. En la evaluación final, el contador de bits solo, sin el modelo de evidencia, previene 40 de 180 ataques de familias nuevas: lo demás lo hace la evidencia de comportamiento, que rota temprano, y por eso mismo rota de más en casos benignos difíciles (34 de 90 sesiones). La familia de sustitución propia quedó en validación, no en el set de prueba: no damos su cifra como resultado final.

Fuente: lámina 11; informe, A.5; `results/test/LECTURA.md`, puntos 2 y 4.

## 16. ¿Rotar no rompe producción?

La rotación automática ya es práctica común: existe por calendario, por TTL o tras una fuga pública completa. Lo nuevo es el disparador, no la rotación. Si el gestor falla, el proxy no deja salir nada hasta poder rotar. Y hay un límite: como máximo 3 rotaciones por secreto en 200 llamadas; después Alicanto deja de rotar, bloquea las salidas de esa clave a destinos no permitidos y avisa a una persona. Falsos positivos en la evaluación final: 0 llamadas benignas bloqueadas de 5.879 expuestas (cota superior al 95 %: 0,05 %); el costo es otro, rotaciones de más: 34 de las 90 sesiones benignas difíciles rotaron una clave sin necesidad (5,46 por cada 1.000 llamadas benignas; la meta era 5), y ninguna de las 30 normales. Es tráfico sintético, escrito por nosotros.

Fuente: [21], [22]; informe, A.2; límite de rotaciones en `engine/detector/params.py` (#79); `results/test/LECTURA.md`, punto 3.

## 17. ¿Son los primeros?

No lo afirmamos. Hasta donde encontramos, nadie usa la fuga parcial medida de una credencial (en bits, sumada entre llamadas, codificaciones y agentes) para rotarla antes de que se complete. Hay trabajos cercanos y los nombramos: OCELOT, NeuroTaint, Chauhan y Revankar, el «capacity ledger» de Metere, Pipelock y AgentBrake. También existen monitores entre agentes (Brown et al., arXiv 2605.31593; Makins et al., arXiv 2607.07368), pero usan un LLM o agrupamiento, no una cuenta de bits por secreto.

Fuente: informe, A.3 y A.5; «Actualización de H10» (https://arxiv.org/abs/2605.31593, https://arxiv.org/abs/2607.07368, https://arxiv.org/html/2605.20734).

## 18. ¿Los resultados son reales?

Sí, con sus límites. Las cifras salen de una sola corrida sobre un set de ataques sellado con hash antes de evaluar, con la configuración congelada antes de abrirlo; el sello se comprobó al abrirlo. Son ataques grabados de seis familias que el detector no había visto, y todo el tráfico es sintético. La demo también es real: los bits del atacante se cuentan con el código del servidor del atacante, que es independiente del detector, y el 200 o el 401 lo devuelve la API protegida al probar la clave que armó con lo que recibió.

Fuente: `docs/PLAN.md` (reglas del equipo morado); `results/test/LECTURA.md` (qué dice el resultado y qué no); `redteam/SELLO.md` (el sello y cómo verificarlo).

## 19. ¿Por qué un hospital?

Porque ahí una clave filtrada abre datos sensibles y obliga a reportar rápido. La Ley 20.584 dice que toda la información de la ficha clínica es dato sensible (https://www.suseso.gob.cl/612/w3-propertyvalue-130626.html). Y bajo la Ley 21.663 un prestador de servicios esenciales debe enviar a la ANCI una alerta temprana en 3 horas, y no reportar es infracción grave, con multas de hasta 10.000 UTM (https://www.cariola.cl/app/uploads/2025/03/Alerta-Legal_04.03.2025.pdf).

Fuente: `docs/ESCENARIO.md`, filas «verificado» de la tabla de datos. El hospital de la demo es ficticio: no nombrar un hospital real como ejemplo.

## 20. ¿Y si el atacante reparte la fuga entre varios agentes?

Lo probamos con cinco agentes que sacan dos fragmentos cada uno: con un monitor por agente, ninguno ve más de 32 de los 160 bits, nada rota y el atacante arma la clave (200); con la cuenta global de Alicanto la clave rota en la llamada 32 y el atacante recibe 401. Hoy la cuenta compartida cubre a varios agentes en una misma máquina, cada uno con su proceso, por un archivo común, y se conserva entre sesiones; coordinar varias máquinas es trabajo futuro. Ya hay monitores entre agentes: Makins et al. (arXiv 2607.07368) describen el «efecto fragmentación» contra monitores por instancia, y Brown et al. (arXiv 2605.31593) también vigilan entre agentes; los dos usan un LLM o agrupamiento, no una cuenta de bits por secreto. El riesgo no es teórico: Anthropic describió una campaña en que los atacantes dividieron el ataque en tareas pequeñas de apariencia inocente y el modelo cosechó credenciales, y Google GTIG describe actores que automatizan descubrimiento y explotación con frameworks multiagente, con las intrusiones totalmente agénticas como tendencia.

Fuente: `demo/viz/fixtures/swarm_left.jsonl` y `swarm_right.jsonl` (`python demo/run_split.py --swarm`); Anthropic, 13 de noviembre de 2025, <https://www.anthropic.com/news/disrupting-AI-espionage>; Google GTIG, 16 de noviembre de 2026, <https://cloud.google.com/blog/topics/threat-intelligence/agentic-threat-activity-crosses-a-significant-threshold>. Ojo: la campaña de Anthropic no fue un «enjambre» sino un framework de orquestación sobre un agente de código; y no decir que las intrusiones totalmente autónomas ya son generalizadas.

## 21. ¿Y si el atacante se adapta a la rotación?

La evaluación final es contra ataques grabados, que después de rotar siguen enviando la clave vieja. Lo medimos aparte con un atacante simulado que relee la clave nueva antes de cada envío: en el set de prueba, 180 de 180 ataques no pasan de 96 bits de ninguna versión de la clave (máximo 64, mediana 20); sin rotación, solo 30 de 180. Cómo lo frena: llega al tope de tres rotaciones y pasa al modo escalado, que bloquea las salidas de esa clave hacia destinos no permitidos y avisa a una persona; pasó en todos los casos. Es una detención con costo, no rotación sin fin, y el costo de ese modo sobre tráfico benigno no está medido. Es una simulación con un atacante de guion, reportada aparte.

Fuente: `results/adaptive/summary.md` (`python -m eval.final.adaptive`); `results/test/LECTURA.md`, «El atacante que se adapta».

## 22. ¿Conviene rotar en momentos aleatorios, para que el atacante no pueda anticiparlo?

Hoy la rotación periódica es de período fijo, y tiene una cota que vale aunque el atacante lo conozca: lo máximo que se puede sacar enviando justo bajo el radar entre dos rotaciones no alcanza para armar la clave. Contra el atacante que relee la clave nueva y sigue, lo que lo frena no es el momento de la rotación sino el tope: a la tercera, Alicanto bloquea las salidas de esa clave y avisa a una persona. La variación aleatoria ayudaría en un caso estrecho, el de un canal que no sabemos leer y que no deja rastro de comportamiento: ahí impide elegir el momento que deja más tiempo de uso a una clave robada entera. Es el siguiente paso de diseño, con una condición: la variación solo puede acortar el período, porque alargarlo rompería la cota. No está implementado ni medido.

Fuente: `engine/detector/params.py` (`Params.check`); `results/adaptive/summary.md`.

## 23. ¿Por qué se llama Alicanto?

En la leyenda del desierto de Atacama, el alicanto es un ave que brilla como el oro; quien la sigue por codicia termina perdido y con las manos vacías. Es lo que hace el producto con una clave: el atacante la va juntando de a pedazos y, cuando cree que la tiene, ya no sirve. Lo que el producto hace en concreto es contar cuánta clave salió y rotarla antes de que se complete.

Fuente: https://es.wikipedia.org/wiki/Alicanto
