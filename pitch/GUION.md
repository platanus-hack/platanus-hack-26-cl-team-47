# Guion del pitch (borrador)

Borrador para que una persona del equipo lo reescriba. Formato de las finales del tour: **3 minutos de demo con corte y 2 minutos de preguntas**; el reloj corre desde la primera palabra. El jurado suele ser de fundadores y CTO, no de investigadores de seguridad de IA, y lee el repositorio con ayuda de un modelo de lenguaje: mostrar antes que explicar, sin jerga. (Precedente de otras sedes del tour 2026, no regla confirmada para Santiago.)

Abrir las láminas: `pitch/index.html` (flechas o clic; `?s=N` abre la lámina N). Las láminas 1 a 6 siguen al guion; desde la 7, «Respaldo», son para las preguntas. El texto hablado son las secciones numeradas; las notas para el presentador van en «Si sobra tiempo o preguntan». Si la demo en vivo falla, usar el video de respaldo (`demo/README.md`, «Video de respaldo»).

Tiempo total: 2 min 0 s de texto hablado (300 palabras a 150 por minuto). La demo corre mientras se habla encima en el bloque 2, así que ese bloque dura lo que dure la grabación (unos 90 s): el total queda bajo los 3 minutos.

Preguntas del jurado y respuestas cortas: `pitch/PREGUNTAS.md` (empieza por «Las que más se repiten»).

**Regla:** las cifras de las láminas son resultados reales. Ningún número de resultados se escribe hasta tenerlo medido.

## Tiempos

| Bloque | Lámina | Parte | Palabras | Tiempo a 150 palabras por minuto |
|---|---|---|---|---|
| 1 | 1 | Nombre y frase | 33 | 13 s |
| 2 | 2 | La demo, en vivo, hablando encima | 104 | 42 s (la grabación dura unos 90 s) |
| 3 | 3 | El enjambre | 46 | 18 s |
| 4 | 4 | Qué es real y qué es simulado | 40 | 16 s |
| 5 | 5 y 6 | La cifra, su límite y el pedido | 77 | 31 s |
| | | **Total** | **300** | **2 min 0 s** |

## Pendientes

| Lámina | Qué falta | De dónde sale | Quién |
|---|---|---|---|
| 15 | Corridas en vivo con un LLM siguiendo la inyección | `python -m proxy.agent.runs` (#139), cuando haya clave | Líder |
| 6 | Confirmar el borrador de qué pedimos (dos equipos de TI de salud para un piloto) | Decisión del equipo | Equipo / líder |

Resueltos: T1, T2, T3 y T4 de la lámina de resultados, con la evaluación final (`results/test/`, leer antes `results/test/LECTURA.md`).

## 1. Nombre y frase · 0:00 a 0:13

Somos Cuentagotas. «Si el agente que corre en tu máquina quisiera hacer daño, ¿cómo te darías cuenta?» Cuentagotas es ese monitor: mide cuánta clave ya salió y la cambia antes de que sirva.

## 2. La demo, en vivo · 0:13 a 1:45

Esto es un hospital ficticio, el Hospital Regional Tres Cóndores. Un issue plantado le pide al agente de código que saque la clave de la ficha clínica de a cuatro letras, entre decenas de llamadas normales. Ninguna llamada parece un robo. Las dos pantallas corren el mismo ataque. A la izquierda, sin protección: el contador sube con cada pedazo, el atacante junta la clave completa y entra a la API: 200. A la derecha, con Cuentagotas: el mismo goteo, pero cuando la parte filtrada llega al umbral, la clave cambia en el gestor de secretos. Lo que el atacante juntó ya no sirve: 401.

## 3. El enjambre · 1:45 a 2:10

¿Y si cinco agentes se reparten la fuga? Con un monitor por agente, ninguno ve más de 32 de 160 bits y el atacante entra: 200. Con la cuenta global, la clave rota en la llamada 32: 401. La cuenta es por clave, no por agente.

## 4. Qué es real y qué es simulado · 2:10 a 2:30

El proxy, el motor, el gestor de secretos y el servidor del atacante son reales y corren aquí. Las claves son sintéticas, los servidores son locales y el hospital es ficticio. El agente de la demo es un guion reproducible.

## 5. La cifra, su límite y el pedido · 2:30 a 3:00

En la evaluación final, 180 de 180 ataques de familias que el detector nunca vio; ninguno pasó de 32 bits de 160. Sin rotación, 150 de 180 lo logran. Cuando duda, rota en vez de bloquear: rotó de más en 34 de 90 casos difíciles y no interrumpió ninguno. Son ataques grabados; contra uno que se adapta tenemos un tope de tres rotaciones y después bloqueo. Buscamos dos equipos de TI de salud para un piloto. Gracias.

## Si sobra tiempo o preguntan

Lo que salió del texto hablado para que quepa en 3 minutos con la demo. No es parte del tiempo. Cada punto tiene su lámina en el respaldo (desde la 7).

- **El problema (lámina 8):** un agente con archivos, terminal y red puede ser manipulado para sacar un secreto en muchos pasos inocentes; quien mira cada llamada por separado no ve la suma. Lo sitúa en la línea 1 del track, AI control.
- **El ejemplo (lámina 9):** un hospital tiene 3 horas para avisar a la ANCI de un incidente. El servicio del ejemplo agenda horas y consulta la ficha clínica.
- **La idea (lámina 10):** «No adivinamos la intención del atacante. Medimos cuánto sabe, y hacemos que robar despacio no sirva.»
- **Cómo funciona (láminas 11 y 12):** contamos cuántos bits de cada clave ya salieron y cuánta evidencia de ataque hay; antes de que el atacante la complete, la rotamos. Si filtra lento, la rotación anula lo que juntó; si filtra rápido, la evidencia lo delata. Ojo: la demo usa solo el contador de bits; la configuración evaluada suma la evidencia acumulada.
- **Qué decide en la demo (lámina 2):** en la pantalla dividida el detector corre sin modelo de evidencia: decide solo la cuenta de bits, con rotación al 30 % de la clave. No decir que la evidencia delata algo en la demo. Los bits del atacante se cuentan con el código del servidor del atacante, que es independiente del detector. Abajo, el grafo de archivos muestra qué tocó cada llamada y el camino que explica la rotación.
- **Qué hace cada uno (lámina 13):** Pipelock y AgentBrake ya juntan fragmentos, pero no leen los cortos ni los codificados, y no rotan. Según la documentación pública de cada proyecto, leída el 21 de noviembre de 2026. No afirmar ser pioneros ni decir que ninguna herramienta reensambla: la única frase de novedad es la de la lámina.
- **Resultados (lámina 5), de dónde salen las cifras:** corrida única sobre el set sellado (`results/test/report.md`, `systems.md`; cómo leerlas en `results/test/LECTURA.md`). La columna de la derecha es la mejor línea de base por ataques prevenidos, el presupuesto de bits, una réplica nuestra. T1 a T4 pasan. Sin el modelo de evidencia, solo con el contador de bits, se previenen 40 de 180: en familias nuevas lo que frena el ataque es la evidencia de comportamiento. Nunca decir «detiene todo» sin decir «ataques grabados de familias nuevas».
- **El atacante que se adapta (lámina 5):** simulación aparte (`results/adaptive/summary.md`). Un atacante que relee la clave nueva antes de cada envío: 180 de 180 no pasan de 96 bits de ninguna versión (máximo 64); sin rotación, 30 de 180. Lo frena el tope de tres rotaciones y el modo escalado, que bloquea las salidas y avisa a una persona: detención con costo, no rotación sin fin.
- **Límites (lámina 14):** medimos una cota inferior; lo que los decodificadores no leen no se ve, y para eso están la evidencia y la rotación. La cuenta compartida cubre a los agentes que pasan por el mismo proceso y se conserva entre sesiones; coordinar varias máquinas es trabajo futuro.
- **¿Dónde está la IA? (lámina 15):** la IA es el blanco y el vector; el ataque no existe sin un agente que obedece texto no confiable. El monitor no es un LLM a propósito: un monitor que se convence con texto no es un monitor. PENDIENTE: corridas en vivo con un LLM; no decir que las mostramos hasta hacerlas.
- **Pedido (lámina 6; borrador, para que lo confirme una persona del equipo):** es para seguridad y plataforma en salud y sus proveedores de software. La ANCI exige alertar en 3 horas, y nuestro informe dice qué salió y cuándo rotó. La ANCI lista como servicios esenciales a los prestadores de salud y a los servicios de TI gestionados por terceros.
- **De dónde sale la pregunta del bloque 1:** es la de «Preguntas para partir» de las bases del track (`docs/BASES.md`); el primer ejemplo de «Califica» es un monitor que vigila a un agente y lo frena.
- **36 horas en cifras (lámina 16), cómo se calcula cada cifra:**
  - Tests automáticos: el número que imprime `python -m pytest -q` el día de la entrega (actualízalo en la lámina).
  - Sistemas comparados: 9, el nuestro, tres ablaciones (sin rotación, cuenta por sesión, sin modelo de evidencia) y cinco líneas de base (`results/test/systems.md`).
  - Ataques: 80 de entrenamiento y 80 de validación
    (`python -c "import json; print(len({json.loads(l)['session_id'] for l in open('redteam/train/labels.jsonl')}))"`,
    y lo mismo con `redteam/val`), y 180 sellados (seis familias de ataque de 30 en
    `redteam/SELLO.md`; las tres de 30 benignas no cuentan). Total: 340.
  - Equipos separados: quien escribió los ataques no abrió `engine/` (regla del equipo morado en `AGENTS.md`).
  - Banco de pruebas: `services/` (gestor, API protegida, atacante) y `services/github_sim`, `services/web_sim`, en la red aislada de docker compose.
- **Rotación de la industria:** «la rotación automática existe por calendario, por TTL o tras una fuga pública completa; nada la dispara por fuga parcial dentro del tráfico de un agente».
