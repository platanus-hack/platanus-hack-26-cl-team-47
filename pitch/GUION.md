# Guion del pitch (borrador)

Borrador para que una persona del equipo lo reescriba. Abrir las láminas:
`pitch/index.html` (flechas o clic; `?s=N` abre la lámina N). Tiempo total objetivo:
unos 3 minutos sin la demo, más la demo.

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
servir. (No decir «somos los primeros».)

## 9. Resultados · 25 s

Cuatro números, todos medidos: falsas alarmas por llamada expuesta, ataques
prevenidos, comparación con la mejor alternativa práctica y el efecto de la
rotación en el goteo. (PENDIENTE: leer las cifras reales de la evaluación final.)

## 10. Límites · 15 s

Lo que medimos es una cota inferior: decimos «al menos tantos bits». Una
transformación que los decodificadores no conocen no se ve; para eso están la
evidencia y la rotación.

## 11. ¿Dónde está la IA? · 15 s

AI Security es proteger sistemas de IA. El detector es determinista a
propósito: un guardrail hecho con un LLM se ataca con prompt injection; el
nuestro no se convence con texto.

## 12. Usuario y cierre · 15 s

Es para equipos de plataforma o de seguridad de empresas que usan agentes de
código sobre repositorios con credenciales. (PENDIENTE: qué pedimos o qué
sigue.) Gracias.
