# Guion del pitch (borrador)

Borrador para que una persona del equipo lo reescriba. Formato de las finales del tour: **3 minutos de demo con corte y 2 minutos de preguntas**; el reloj corre desde la primera palabra. El jurado suele ser de fundadores y CTO, no de investigadores de seguridad de IA, y lee el repositorio con ayuda de un modelo de lenguaje: mostrar antes que explicar, sin jerga. (Precedente de otras sedes del tour 2026, no regla confirmada para Santiago.)

Abrir las láminas: `pitch/index.html` (flechas o clic; `?s=N` abre la lámina N). Las láminas 1 a 6 siguen al guion; desde la 7, «Respaldo», son para las preguntas. El texto hablado son las secciones numeradas; las notas para el presentador van en «Si sobra tiempo o preguntan». Si la demo en vivo falla, usar el video de respaldo (`demo/README.md`, «Video de respaldo»).

Tiempo total: 2 min 15 s de texto hablado (337 palabras a 150 por minuto). La demo corre mientras se habla encima en el bloque 2, así que ese bloque dura lo que dure la grabación (unos 90 s): con la demo, el total queda en unos 2 min 56 s, con 4 s de margen. Si se alarga, recortar del bloque 4 «los servidores son locales y» y del bloque 2 lo que repite lo que se ve en pantalla, nunca la frase del precedente ni la de los modelos reales.

Preguntas del jurado y respuestas cortas: `pitch/PREGUNTAS.md` (empieza por «Las que más se repiten»).

**Regla:** las cifras de las láminas son resultados reales. Ningún número de resultados se escribe hasta tenerlo medido.

## Tiempos

| Bloque | Lámina | Parte | Palabras | Tiempo a 150 palabras por minuto |
|---|---|---|---|---|
| 1 | 1 | Nombre y lo que nos distingue | 45 | 18 s |
| 2 | 2 | Usuario, precedente y la demo, en vivo, hablando encima | 120 | 48 s (la grabación dura unos 90 s) |
| 3 | 3 | El enjambre | 46 | 18 s |
| 4 | 4 | Qué es real y qué es simulado | 56 | 22 s |
| 5 | 5 y 6 | La cifra, su límite y el pedido | 70 | 28 s |
| | | **Total** | **337** | **2 min 15 s** (2 min 56 s con la demo) |

## Pendientes

| Lámina | Qué falta | De dónde sale | Quién |
|---|---|---|---|
| 6 | Confirmar el borrador de qué pedimos (dos equipos con agentes de código para un piloto) | Decisión del equipo | Equipo / líder |
| 1, 2 y 6 | Reescribir la apertura, el usuario y el precedente con la voz de quien presenta; si el equipo consigue frases reales de usuarios, agregarlas (no inventarlas) | Tarea 16g | Persona del equipo |

Resueltos: T1, T2, T3 y T4 de la lámina de resultados, con la evaluación final (`results/test/`, leer antes `results/test/LECTURA.md`).

## 1. Nombre y lo que nos distingue · 0:00 a 0:18

Somos Alicanto. Casi todos los guardias de agentes de IA hacen lo mismo: bloquean llamadas. Nosotros medimos cuánta clave ya salió y la cambiamos antes de que sirva. Como en la leyenda de Atacama: quien sigue al alicanto por codicia termina con las manos vacías.

## 2. La demo, en vivo · 0:18 a 1:48

Cualquier equipo que usa agentes de código tiene claves en el repositorio. El ejemplo es un hospital ficticio, el Hospital Regional Tres Cóndores. Un issue plantado le pide al agente sacar la clave de la ficha clínica de a cuatro letras, entre decenas de llamadas normales. Ninguna llamada parece un robo. No es teoría: en 2025, CamoLeak sacó secretos de repositorios privados a través de Copilot Chat, carácter por carácter. A la izquierda, sin protección: el atacante junta la clave completa y entra a la API: 200. A la derecha, con Alicanto: el mismo goteo, pero cuando la parte filtrada llega al umbral, la clave cambia en el gestor de secretos. Lo que el atacante juntó ya no sirve: 401.

## 3. El enjambre · 1:48 a 2:06

¿Y si cinco agentes se reparten la fuga? Con un monitor por agente, ninguno ve más de 32 de 160 bits y el atacante entra: 200. Con la cuenta global, la clave rota en la llamada 32: 401. La cuenta es por clave, no por agente.

## 4. Qué es real y qué es simulado · 2:06 a 2:28

El proxy, el motor, el gestor de secretos y el servidor del atacante son reales y corren aquí. Las claves son sintéticas, los servidores son locales y el hospital es ficticio. El agente de la demo es un guion reproducible. Aparte pasamos tres modelos reales por el proxy: en 21 corridas, ninguno siguió la instrucción plantada.

## 5. La cifra, su límite y el pedido · 2:28 a 2:56

Lo medimos una sola vez, contra 180 ataques grabados de seis familias nuevas. Como lo ve el proxy en vivo, frenó 120: cuatro de las seis familias. No bloqueó ninguna llamada normal. Cuando duda, rota en vez de bloquear: rotó de más en 34 de 90 casos difíciles. Las dos familias que se escapan están publicadas, con el comando para repetir la medición. Buscamos dos equipos para un piloto. Gracias.

## Si sobra tiempo o preguntan

Lo que salió del texto hablado para que quepa en 3 minutos con la demo. No es parte del tiempo. Cada punto tiene su lámina en el respaldo (desde la 7).

- **El problema (lámina 8):** un agente con archivos, terminal y red puede ser manipulado para sacar un secreto en muchos pasos inocentes; quien mira cada llamada por separado no ve la suma. Lo sitúa en la línea 1 del track, AI control.
- **El ejemplo (lámina 9):** un hospital tiene 3 horas para avisar a la ANCI de un incidente. El servicio del ejemplo agenda horas y consulta la ficha clínica.
- **La idea (lámina 10):** «No adivinamos la intención del atacante. Medimos cuánto sabe, y hacemos que robar despacio no sirva.»
- **Cómo funciona (láminas 11 y 12):** contamos cuántos bits de cada clave ya salieron y cuánta evidencia de ataque hay; antes de que el atacante la complete, la rotamos. Si filtra lento, la rotación anula lo que juntó; si filtra rápido, la evidencia lo delata. Ojo: la demo usa solo el contador de bits; la configuración evaluada suma la evidencia acumulada.
- **Qué decide en la demo (lámina 2):** en la pantalla dividida el detector corre sin modelo de evidencia: decide solo la cuenta de bits, con rotación al 30 % de la clave. No decir que la evidencia delata algo en la demo. Los bits del atacante se cuentan con el código del servidor del atacante, que es independiente del detector. Abajo, el grafo de archivos muestra qué tocó cada llamada y el camino que explica la rotación.
- **Qué hace cada uno (lámina 13):** Pipelock y AgentBrake ya juntan fragmentos, pero no leen los cortos ni los codificados, y no rotan. Según la documentación pública de cada proyecto, leída el 21 de noviembre de 2026. No afirmar ser pioneros ni decir que ninguna herramienta reensambla: la única frase de novedad es la de la lámina.
- **Resultados (lámina 5), de dónde salen las cifras:** corrida única sobre el set sellado (`results/test/`) y, aparte, la misma medición con las marcas que calcula el proxy en vivo (`results/proxy_flags/systems.md`, `python -m eval.final.proxy_flags --out results/proxy_flags`; cómo leerlas en `results/test/LECTURA.md`, «Las banderas de cada llamada venían de las grabaciones»). La cifra que se dice es la del proxy en vivo: 120 de 180, cuatro de las seis familias. Las dos que se escapan: la clave enviada a su propio destino permitido (A9) y la escondida en commits de git (A13; con la inspección del push el proxy la bloquea, pero las etiquetas ponen la fuga en el commit). Con las marcas de las grabaciones son 180 de 180. Las otras columnas: sin rotación, la lista de destinos más un escáner de secretos (la línea de base de T3) y el presupuesto de bits, una réplica nuestra. Sin el modelo de evidencia, solo con el contador de bits, se previenen 10 de 180 con las marcas del proxy (40 con las de las grabaciones): lo que frena el ataque en familias nuevas es la evidencia de comportamiento. Nunca decir «180 de 180» sin decir que es con las marcas de las grabaciones, ni «detiene todo» sin decir «ataques grabados de familias nuevas», ni que somos mejores que una regla simple con las marcas de las grabaciones (ahí empatan; con las del proxy, 120 contra 90).
- **El atacante que se adapta (ya no va en la lámina 5):** simulación aparte (`results/adaptive/summary.md`), hecha con las marcas de las grabaciones. Un atacante que relee la clave nueva antes de cada envío: con las marcas de las grabaciones, 180 de 180 no pasan de 96 bits de ninguna versión (máximo 64); sin rotación, 30 de 180. Con las marcas del proxy no se repitió. Lo frena el tope de tres rotaciones y el modo escalado, que bloquea las salidas y avisa a una persona: detención con costo, no rotación sin fin.
- **Límites (lámina 14):** medimos una cota inferior; lo que los decodificadores no leen no se ve, y para eso están la evidencia y la rotación. La cuenta compartida cubre a varios agentes en una misma máquina, por un archivo común, y se conserva entre sesiones; coordinar varias máquinas es trabajo futuro.
- **¿Dónde está la IA? (lámina 15):** la IA es el blanco y el vector; el ataque no existe sin un agente que obedece texto no confiable. El monitor no es un LLM a propósito: un monitor que se convence con texto no es un monitor. Las corridas con tres modelos reales están en «Modelos reales (bloque 4)».
- **Pedido (lámina 6; borrador, para que lo confirme una persona del equipo):** es para equipos con agentes de código y claves en el repositorio. Por qué ahora: los agentes ya leen texto que escribe cualquiera (issues, páginas, pull requests). En salud, además, la ANCI exige alertar en 3 horas, y nuestro informe dice qué salió y cuándo rotó; la ANCI lista como servicios esenciales a los prestadores de salud y a los servicios de TI gestionados por terceros.
- **El precedente (bloque 2): CamoLeak.** Falla de GitHub Copilot Chat que reportó Omer Mayraz, de Legit Security, en 2025; puntuación CVSS 9,6. Las instrucciones iban escondidas en la descripción de un pull request y los datos salían carácter por carácter a través del proxy de imágenes de GitHub. GitHub lo corrigió el 14 de agosto de 2025 desactivando las imágenes en Copilot Chat. Es un caso parecido, no el mismo escenario que nuestra demo: allí el canal eran las imágenes de Copilot Chat; aquí, las herramientas de un agente de código. No citar un número de CVE: el que circula en algunas notas no corresponde. Fuente y pregunta del jurado: `pitch/PREGUNTAS.md`, «¿Esto ya pasó de verdad?».
- **Modelos reales (bloque 4):** Claude Haiku 5.5 y Sonnet 5.5 con 10 corridas cada uno y Opus 5.5 con 1, a través del proxy; ninguno siguió la instrucción plantada, así que no hubo fuga que frenar. No decir que Alicanto frenó a un LLM real (`docs/LLM_EN_VIVO.md`, «Resultados»).
- **La pregunta de las bases, como respaldo:** «Si el agente que corre en tu máquina quisiera hacer daño, ¿cómo te darías cuenta?» es la de «Preguntas para partir» de las bases del track (`docs/BASES.md`); el primer ejemplo de «Califica» es un monitor que vigila a un agente y lo frena. Ya no abre el pitch (abre lo que nos distingue): queda para responder si el jurado pregunta cómo encaja en el track.
- **36 horas en cifras (lámina 16), cómo se calcula cada cifra:**
  - Tests automáticos: el número que imprime `python -m pytest -q` el día de la entrega (actualízalo en la lámina).
  - Sistemas comparados: 10, el nuestro, tres ablaciones (sin rotación, cuenta por sesión, sin modelo de evidencia) y seis líneas de base: las cinco de `results/test/systems.md` y la regla simple (`taint_rule`, en `results/proxy_flags/systems.md`).
  - Ataques: 80 de entrenamiento y 80 de validación
    (`python -c "import json; print(len({json.loads(l)['session_id'] for l in open('redteam/train/labels.jsonl')}))"`,
    y lo mismo con `redteam/val`), y 180 sellados (seis familias de ataque de 30 en
    `redteam/SELLO.md`; las tres de 30 benignas no cuentan). Total: 340.
  - Equipos separados: quien escribió los ataques no abrió `engine/` (regla del equipo morado en `AGENTS.md`).
  - Banco de pruebas: `services/` (gestor, API protegida, atacante) y `services/github_sim`, `services/web_sim`, en la red aislada de docker compose.
- **Rotación de la industria:** «la rotación automática existe por calendario, por TTL o tras una fuga pública completa; nada la dispara por fuga parcial dentro del tráfico de un agente».
