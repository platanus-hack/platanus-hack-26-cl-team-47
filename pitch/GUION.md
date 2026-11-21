# Guion del pitch (borrador)

Borrador para que una persona del equipo lo reescriba. Abrir las láminas:
`pitch/index.html` (flechas o clic; `?s=N` abre la lámina N). Tiempo total objetivo:
unos 3 minutos sin la demo, más la demo.

Preguntas del jurado y respuestas cortas: `pitch/PREGUNTAS.md`. Si alguien
habla de la rotación de la industria: «la rotación automática existe por
calendario, por TTL o tras una fuga pública completa; nada la dispara por
fuga parcial dentro del tráfico de un agente».

**Regla:** las cifras de las láminas son resultados reales. Ningún número de
resultados se escribe hasta tenerlo medido.

## Pendientes

| Lámina | Qué falta | De dónde sale | Quién |
|---|---|---|---|
| 3 | Nombre del escenario de la demo | Decisión del equipo (`docs/PLAN.md`, «Escenario pendiente») | Equipo / líder |
| 9 | T1: falsas alarmas por llamada expuesta | Evaluación final (paso 14), `eval/metrics` | Análisis (matix3000) |
| 9 | T2: ataques prevenidos | Evaluación final sobre el set sellado (paso 14) | Análisis |
| 9 | T3: comparación con allowlist más detect-secrets | `eval/baselines` en la evaluación final | Servicios (VictoriaGuerriero) y Análisis |
| 9 | T4: efecto de la rotación en el goteo | Ablación del paso 14 | Análisis |
| 11 | Corridas en vivo con un LLM siguiendo la inyección | Paso de nivel 2 (`docs/PLAN.md`) | Equipo |
| 12 | Qué pedimos o qué sigue | Decisión del equipo | Equipo / líder |

## 1. Título · 10 s

Somos team-47, del track AI Security. Construimos un medidor de información
filtrada para agentes de IA.

## 2. El problema · 25 s

Un agente de código tiene acceso a archivos, a la terminal y a la red. Alguien
puede manipularlo para que saque un secreto en muchos pasos, cada uno inocente
por sí solo. Los filtros que miran cada llamada por separado no ven la suma.

## 3. El ejemplo · 20 s

El goteo: cuatro caracteres por salida, separados por decenas de llamadas
normales. Ninguna llamada parece un robo; juntas, se llevan la clave.
(PENDIENTE: contar el escenario cuando el equipo lo decida.)

## 4. La idea · 15 s

No adivinamos la intención del atacante. Medimos cuánto sabe, y hacemos que
robar despacio no sirva.

## 5. Cómo funciona · 25 s

Llevamos dos cuentas en cada llamada. Una: cuántos bits de cada secreto ya
salieron. Otra: cuánta evidencia de ataque hay. Cuando el atacante se acerca a
saber la clave, la rotamos.

## 6. La pinza · 15 s

Si el atacante filtra lento, la rotación anula lo que juntó. Si filtra rápido,
la evidencia lo delata y lo bloqueamos.

## 7. Demo · 60–90 s

Pantalla dividida, el mismo ataque dos veces. A la izquierda, sin protección:
los bits suben hasta el final y el atacante entra con la clave. A la derecha,
con el medidor: al llegar al umbral la clave rota, la curva cae y el atacante
recibe un 401. Abajo, el grafo de archivos muestra qué tocó cada llamada y el
camino que explica la rotación.

## 8. Qué es nuevo · 20 s

Trabajos de este año muestran que contar la fuga acumulada ve lo que los
detectores por turno no ven. Nosotros lo hacemos sin acceso al modelo, con
falsas alarmas medidas, y rotamos el secreto para que lo filtrado deje de
servir. En letra menor: hasta donde encontramos, es nuevo contar la fuga en
bits por secreto en los argumentos de las herramientas sin acceso al modelo,
rotar según lo medido, y combinar la rotación con una prueba secuencial. (No
afirmar ser los primeros: decir «hasta donde encontramos». Ojo: la mitad
«rápido, lo delata la evidencia» todavía no decide en el detector.)

## 9. Resultados · 25 s

Cuatro números, todos medidos: falsas alarmas por llamada expuesta, ataques
prevenidos, comparación con la mejor alternativa práctica y el efecto de la
rotación en el goteo. (PENDIENTE: leer las cifras reales de la evaluación final.)

## 10. Límites · 15 s

Lo que medimos es una cota inferior: decimos «al menos tantos bits». Una
transformación que los decodificadores no conocen no se ve; para eso están la
evidencia y la rotación.

## 11. ¿Dónde está la IA? · 15 s

La IA es el blanco y el vector: el ataque no existe sin un agente que obedece
texto no confiable. El monitor no es un LLM a propósito, porque un monitor LLM
se ataca con la misma inyección: un guardia que se convence con texto no es un
guardia. Y un atacante que suma un LLM no gana nada contra el medidor, porque
medimos información, no intención. (PENDIENTE: corridas en vivo con un LLM; no
decir que las mostramos hasta hacerlas.)

## 12. Usuario y cierre · 15 s

Es para equipos de plataforma o de seguridad de empresas que usan agentes de
código sobre repositorios con credenciales. (PENDIENTE: qué pedimos o qué
sigue.) Gracias.
