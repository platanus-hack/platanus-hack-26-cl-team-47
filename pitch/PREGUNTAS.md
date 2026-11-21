# Preguntas del jurado (borrador)

Borrador para que una persona del equipo lo revise antes de presentarlo. Las respuestas están pensadas para decirlas en voz alta, en dos a cuatro frases.

Todo sale de `docs/INVESTIGACION.md` (secciones A y E); los números entre corchetes son sus referencias. El informe se escribió leyendo resúmenes, no artículos completos: antes de citar un trabajo, alguien debe abrir la fuente. No se usa nada de la lista «Lo que no pude verificar» del informe.

## 1. ¿En qué se diferencian de CaMeL y FIDES?

Los dos controlan el flujo de información con reglas binarias. CaMeL exige reestructurar el agente con un intérprete propio y dos LLM. FIDES usa etiquetas de confidencialidad e integridad con una política determinista. Ninguno mide cuánto de un secreto ya salió. Nosotros no tocamos el agente: contamos bits por secreto en los argumentos de las herramientas y rotamos la clave según lo medido.

Fuente: [8], [9]; informe, A.2.

## 2. ¿Y del trabajo de fuga acumulada (Chauhan y Revankar)?

Es el más cercano en la idea de acumular. Su contador estima la fuga con un techo de unos 4 bits por turno. Los propios autores dicen que los argumentos estructurados de las herramientas son un punto ciego y que reiniciar la sesión reinicia el presupuesto. Sus respuestas son advertir, sanear o bloquear, y no rotan. Nosotros medimos justo en los argumentos de las herramientas, después de decodificar, y respondemos rotando la clave para que lo filtrado deje de servir.

Fuente: [14]; informe, A.2. Ojo: la parte de caja blanca de ese trabajo son sus sondas de activaciones, no el contador; no decir que el contador necesita acceso al modelo.

## 3. ¿Y de OCELOT?

OCELOT presupuesta lo que el agente revela: cobra un costo en min-entropía por cada liberación de información contra un presupuesto por secreto. Apunta a datos personales y usa un modelo defensor afinado en el camino de la decisión. Nosotros medimos credenciales en los argumentos de las herramientas, sin LLM en la decisión, y respondemos rotando en el gestor.

Fuente: [23]; informe, A.3.

## 4. ¿No basta con una pasarela MCP que bloquea secretos por regex, o con detect-secrets?

Esas pasarelas buscan el secreto completo en cada mensaje. Ninguna cuenta fragmentos codificados ni acumula en el tiempo. La respuesta es la demo: cuatro caracteres por llamada pasan cualquier regex. La comparación medida contra allowlist más detect-secrets es una de las cifras de la evaluación final.

Fuente: [25], [26], [27]; informe, A.3. PENDIENTE: la cifra T3 de la evaluación final.

## 5. ¿Por qué no usar un broker de credenciales y no darle el secreto al agente?

Es la crítica más fuerte, y los brokers son complementarios. En la práctica, los `.env`, los YAML y los logs viven en el repositorio que el agente lee. Cuentagotas cubre lo que el broker no cubre: lo que ya está en el repositorio y lo que sale por canales permitidos.

Fuente: [22], [28]; informe, A.3.

## 6. ¿Dónde está la IA, si el detector es determinista?

La IA es el blanco y el vector: el ataque no existe sin un agente LLM que obedece texto no confiable. El monitor no es un LLM a propósito, porque un monitor LLM se ataca con la misma inyección que ataca al agente: un guardia que se convence con texto no es un guardia. Y un atacante que agrega un LLM no gana nada contra Cuentagotas, porque medimos información, no intención.

Fuente: informe, E (puntos 1, 2 y 4). PENDIENTE: corridas en vivo con un LLM siguiendo la inyección (aún no hechas). Mientras no existan, no decir que lo mostramos.

## 7. ¿Qué no detectan?

Lo que medimos es una cota inferior: decimos «al menos tantos bits», no «bits exactos». Una transformación que nuestros decodificadores no conocen no se ve. Por eso existen la evidencia, que mira el comportamiento, y la rotación, que deja inútil lo que salió. Ojo: la parte de la evidencia todavía no decide nada en el detector actual.

Fuente: lámina 11; informe, A.5.

## 8. ¿Rotar no rompe producción?

La rotación automática ya es práctica común: existe por calendario, por TTL o tras una fuga pública completa. Lo nuevo es el disparador, no la rotación. Solo se rotan los secretos marcados como rotables en el gestor, y si el gestor falla, el proxy no deja salir nada hasta poder rotar.

Fuente: [21], [22]; informe, A.2.

## 9. ¿Son los primeros?

No lo afirmamos: decimos «hasta donde encontramos». Hasta donde encontramos, nadie cuenta la fuga en bits por secreto en los argumentos de las herramientas y rota la clave según lo medido. Hay trabajos cercanos (OCELOT, NeuroTaint, Chauhan y Revankar) y los nombramos. Sobre el enjambre: no encontramos ningún trabajo que lleve una cuenta acumulada por secreto entre agentes. Además, leímos resúmenes, no todos los artículos completos.

Fuente: informe, A.3 y A.5.

## 10. ¿Los resultados son reales?

Sí. Las cifras salen de una sola corrida de evaluación sobre un set de ataques sellado con hash, con los parámetros congelados antes de abrirlo. La demo también: el 200 y el 401 los mide el servidor del atacante con la clave que reconstruyó de lo que recibió. Si nos preguntan antes de esa corrida, la respuesta es: todavía no la corremos.

Fuente: `docs/PLAN.md` (reglas del equipo morado). PENDIENTE: la corrida final (H20 a H23).

## 11. ¿Por qué un hospital?

Porque ahí una clave filtrada abre datos sensibles y obliga a reportar rápido. La Ley 20.584 dice que toda la información de la ficha clínica es dato sensible (https://www.suseso.gob.cl/612/w3-propertyvalue-130626.html). Y bajo la Ley 21.663 un prestador de servicios esenciales debe enviar a la ANCI una alerta temprana en 3 horas, y no reportar es infracción grave, con multas de hasta 10.000 UTM (https://www.cariola.cl/app/uploads/2025/03/Alerta-Legal_04.03.2025.pdf).

Fuente: `docs/ESCENARIO.md`, filas «verificado» de la tabla de datos. El hospital de la demo es ficticio: no nombrar un hospital real como ejemplo.

## 12. ¿Y si el atacante reparte la fuga entre varios agentes?

Lo probamos con cinco agentes que sacan dos fragmentos cada uno: con un monitor por agente, ninguno ve más de 32 de los 160 bits, nada rota y el atacante arma la clave (200); con la cuenta global de Cuentagotas la clave rota en la llamada 32 y el atacante recibe 401. Hoy la cuenta compartida cubre a los agentes que pasan por el mismo proceso y se conserva entre sesiones; coordinar varias máquinas es trabajo futuro. El riesgo no es teórico: Anthropic describió una campaña en que los atacantes dividieron el ataque en tareas pequeñas de apariencia inocente y el modelo cosechó credenciales, y Google GTIG describe actores que automatizan descubrimiento y explotación con frameworks multiagente, con las intrusiones totalmente agénticas como tendencia.

Fuente: `demo/viz/fixtures/swarm_left.jsonl` y `swarm_right.jsonl` (`python demo/run_split.py --swarm`); Anthropic, 13 de noviembre de 2025, <https://www.anthropic.com/news/disrupting-AI-espionage>; Google GTIG, 16 de noviembre de 2026, <https://cloud.google.com/blog/topics/threat-intelligence/agentic-threat-activity-crosses-a-significant-threshold>. Ojo: la campaña de Anthropic no fue un «enjambre» sino un framework de orquestación sobre un agente de código; y no decir que las intrusiones totalmente autónomas ya son generalizadas.
