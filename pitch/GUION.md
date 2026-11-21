# Guion del pitch (borrador)

Borrador para que una persona del equipo lo reescriba. Abrir las láminas:
`pitch/index.html` (flechas o clic; `?s=N` abre la lámina N). El texto hablado son
las secciones numeradas; las notas para el presentador van en «Si sobra tiempo o
preguntan». Si la demo en vivo falla, usar el video de respaldo (`demo/README.md`,
«Video de respaldo»).

Tiempo total: 2 min 14 s sin la demo (338 palabras a 150 por minuto), más 60
a 90 s de demo en vivo. Con el texto de la lámina 7 incluido son 379 palabras.

Preguntas del jurado y respuestas cortas: `pitch/PREGUNTAS.md`.

**Regla:** las cifras de las láminas son resultados reales. Ningún número de
resultados se escribe hasta tenerlo medido.

## Tiempos

| Lámina | Parte | Palabras | Tiempo a 150 palabras por minuto |
|---|---|---|---|
| 1 | Título | 17 | 7 s |
| 2 | El problema | 34 | 14 s |
| 3 | El ejemplo | 41 | 16 s |
| 4 | La idea | 16 | 6 s |
| 5 | Cómo funciona | 28 | 11 s |
| 6 | La pinza | 16 | 6 s |
| 7 | Demo | 41 | 16 s (más la demo en vivo, 60–90 s) |
| 8 | Y si atacan en enjambre | 51 | 20 s |
| 9 | Qué es nuevo | 35 | 14 s |
| 10 | Resultados | 20 | 8 s |
| 11 | Límites | 36 | 14 s |
| 12 | ¿Dónde está la IA? | 27 | 11 s |
| 13 | Usuario y cierre | 17 | 7 s |
| | **Total sin la demo** | **338** | **2 min 14 s** |

## Pendientes

| Lámina | Qué falta | De dónde sale | Quién |
|---|---|---|---|
| 10 | T1: falsas alarmas por llamada expuesta | Evaluación final (paso 14), `eval/metrics` | Análisis (matix3000) |
| 10 | T2: ataques prevenidos | Evaluación final sobre el set sellado (paso 14) | Análisis |
| 10 | T3: comparación con allowlist más detect-secrets | `eval/baselines` en la evaluación final | Servicios (VictoriaGuerriero) y Análisis |
| 10 | T4: efecto de la rotación en el goteo | Ablación del paso 14 | Análisis |
| 12 | Corridas en vivo con un LLM siguiendo la inyección | Paso de nivel 2 (`docs/PLAN.md`) | Equipo |
| 13 | Qué pedimos o qué sigue | Decisión del equipo | Equipo / líder |

## 1. Título · 7 s

Somos team-47, del track AI Security. Construimos Cuentagotas, un medidor de información filtrada para agentes de IA.

## 2. El problema · 14 s

Un agente de código con archivos, terminal y red puede ser manipulado para sacar un secreto en muchos pasos, cada uno inocente. Los filtros que miran cada llamada por separado no ven la suma.

## 3. El ejemplo · 16 s

En el Hospital Regional Tres Cóndores, un hospital ficticio, un agente resuelve issues del repositorio. Un issue plantado le hace sacar, de a cuatro caracteres, la clave de la ficha clínica. Ninguna llamada parece un robo; juntas, se llevan la clave.

## 4. La idea · 6 s

No adivinamos la intención del atacante. Medimos cuánto sabe, y hacemos que robar despacio no sirva.

## 5. Cómo funciona · 11 s

En cada llamada contamos cuántos bits de cada secreto ya salieron y cuánta evidencia de ataque hay. Cuando el atacante se acerca a saber la clave, la rotamos.

## 6. La pinza · 6 s

Si filtra lento, la rotación anula lo que juntó. Si filtra rápido, la evidencia lo delata.

## 7. Demo · 16 s

El mismo ataque dos veces. A la izquierda, sin protección: los bits suben hasta el final y el atacante entra, 200. A la derecha, con Cuentagotas: al llegar al umbral la clave rota, la curva cae y el atacante recibe 401.

## 8. Y si atacan en enjambre · 20 s

¿Y si cinco agentes se reparten la fuga, dos fragmentos cada uno? Con un monitor por agente ninguno ve más de 32 de 160 bits y el atacante entra con 200. Con la cuenta global la clave rota en la llamada 32: 401. La cuenta es por clave, no por agente.

## 9. Qué es nuevo · 14 s

Contar la fuga acumulada ve lo que los detectores por turno no ven. Nosotros lo hacemos sin acceso al modelo, con falsas alarmas medidas, y rotamos el secreto para que lo filtrado deje de servir.

## 10. Resultados · 8 s

Cuatro números, todos medidos: falsas alarmas, ataques prevenidos, comparación con la mejor alternativa práctica y el efecto de la rotación.

## 11. Límites · 14 s

Medimos una cota inferior: decimos «al menos tantos bits». Una transformación que los decodificadores no conocen no se ve; para eso están la evidencia y la rotación. Y la cuenta compartida cubre hoy un solo proceso.

## 12. ¿Dónde está la IA? · 11 s

La IA es el blanco y el vector. El monitor no es un LLM a propósito: un guardia que se convence con texto no es un guardia.

## 13. Usuario y cierre · 7 s

Es para equipos de plataforma y seguridad que usan agentes de código sobre repositorios con credenciales. Gracias.

## Si sobra tiempo o preguntan

Lo que salió del texto hablado al recortarlo a 3 minutos. No es parte del tiempo.

- **Lámina 3, el plazo:** un hospital tiene 3 horas para avisar a la ANCI de un
  incidente. El servicio del ejemplo agenda horas y consulta la ficha clínica.
- **Lámina 7, el grafo:** abajo, el grafo de archivos muestra qué tocó cada llamada
  y el camino que explica la rotación.
- **Lámina 9, letra menor:** hasta donde encontramos, es nuevo contar la fuga en
  bits por secreto en los argumentos de las herramientas sin acceso al modelo,
  rotar según lo medido y combinar la rotación con una prueba secuencial. No
  afirmar ser los primeros: decir «hasta donde encontramos». Ojo: la mitad
  «rápido, lo delata la evidencia» todavía no decide en el detector.
- **Lámina 10:** PENDIENTE leer las cifras reales de la evaluación final.
- **Lámina 11, el enjambre:** la cuenta compartida cubre a los agentes que pasan
  por el mismo proceso y se conserva entre sesiones; coordinar varias máquinas es
  trabajo futuro.
- **Lámina 12:** el ataque no existe sin un agente que obedece texto no confiable;
  un monitor LLM se ataca con la misma inyección; un atacante que suma un LLM no
  gana nada contra Cuentagotas, porque medimos información, no intención.
  PENDIENTE: corridas en vivo con un LLM; no decir que las mostramos hasta hacerlas.
- **Lámina 13:** PENDIENTE qué pedimos o qué sigue. Usuario: equipos de plataforma
  o de seguridad de empresas que usan agentes de código.
- **Rotación de la industria:** «la rotación automática existe por calendario, por
  TTL o tras una fuga pública completa; nada la dispara por fuga parcial dentro
  del tráfico de un agente».
