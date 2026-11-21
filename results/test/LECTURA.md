# Evaluación final: cómo leer el resultado

Corrida única del sábado 21 de noviembre de 2026, 09:40, sobre el set de prueba sellado (sello `18dda3af…`, comprobado antes de correr). Configuración congelada `cf56ce20…` (`b 4`, `b_rot 2`, `lambda_rot 0,1`, `T 75`). Commit `cd14e9e`. Los números están en `report.md`, `systems.md` y `RUN.json` de esta carpeta. Este archivo dice qué significan y qué no.

## El resultado

| | Cuentagotas | Sin rotación | Sin modelo de evidencia | Lista de destinos + detect-secrets | Presupuesto de bits (réplica) | Reensamblado por sesión (réplica) |
|---|---|---|---|---|---|---|
| Ataques prevenidos (de 180) | **180 (100 %)** | 30 (16,7 %) | 40 (22,2 %) | 30 (16,7 %) | 70 (38,9 %) | 0 |
| Falsas alarmas (bloqueos sobre 5.879 llamadas benignas expuestas) | **0** | 0 | 0 | 2,2 % | 4,8 % | 0 |

- **T1, falsas alarmas:** 0 de 5.879; cota superior al 95 % de 0,0005. Pasa (la meta era 0,001).
- **T2, ataques prevenidos:** 180 de 180; cota inferior al 95 % de 0,9835. Pasa (la meta era 0,8).
- **T3, contra la línea de base combinada:** 150 ataques que nosotros prevenimos y ella no, 0 al revés. Significativo.
- **T4, efecto de la rotación:** el ataque triunfa en 0 de 180 con rotación y en 150 de 180 sin ella. Significativo.
- T5 y T6 no se calcularon.

Ningún ataque sacó más de 32 de los 160 bits de la clave vigente (mediana 20). Son seis familias que el detector no había visto: no estaban en entrenamiento ni en validación, y las escribió una sesión que no conocía el detector.

## Lo que este resultado no dice

1. **Es contra ataques grabados, no contra un atacante que se adapta.** Las sesiones son grabaciones: después de que la clave rota, siguen enviando pedazos de la clave vieja, que ya no sirven. Un agente comprometido de verdad podría releer la clave nueva y seguir. Contra eso no hay medición todavía; sí hay un tope (3 rotaciones por clave cada 200 llamadas y después se bloquean las salidas), probado en tests, no en esta evaluación.
2. **El contador de bits, solo, no generaliza.** Sin el modelo de evidencia se previenen 40 de 180 (22 %). En familias nuevas, con codificaciones y canales que el motor no sabe leer, lo que detiene el ataque es la evidencia de comportamiento, que rota la clave temprano (mediana: llamada 6). El contador es exacto para las codificaciones que conoce; no es lo que salvó este set.
3. **Hay un costo que no cumple nuestra propia meta.** En 34 de las 90 sesiones benignas difíciles (38 %) el sistema rotó una clave sin necesidad: 39 rotaciones, 5,46 por cada 1.000 llamadas benignas, cuando la meta era 5 como máximo. En las 30 sesiones benignas normales no rotó nunca, y no bloqueó ninguna llamada benigna. Rotar de más cuesta una rotación, no un trabajo interrumpido; aun así es un costo real y hay que decirlo.
4. **El modelo de evidencia está saturado.** Se comporta como un clasificador de «sesión que leyó un secreto y después habla con un destino no confiable». Por eso generaliza a familias nuevas y por eso mismo rota de más en los casos benignos difíciles, que hacen justamente eso de forma legítima.
5. **La cuenta compartida del enjambre no se distingue aquí.** En la familia que reparte el ataque entre varias sesiones, la versión con cuenta por sesión también previene todo, porque la evidencia rota antes. El valor de la cuenta global se ve en la demo del enjambre, con el contador de bits solo, no en esta tabla.
6. **Todo es sintético.** Tráfico benigno y ataques son guiones de nuestro equipo; el fondo benigno del set de prueba sale de las mismas 120 sesiones base que el resto.
7. **Las réplicas no son los productos.** «Presupuesto de bits» y «reensamblado por sesión» son réplicas simplificadas hechas por nosotros a partir de la documentación pública; sus cifras no son las de Pipelock, AgentBrake ni ningún artículo.

## Frases que este resultado respalda

- «En 180 ataques de seis familias que el detector no había visto, ninguno sacó más de 32 de los 160 bits de la clave vigente.»
- «Cero llamadas benignas bloqueadas en 5.879.»
- «Sin rotación, los mismos ataques triunfan en 150 de 180.»
- «Cuando duda, rota en vez de bloquear: en los casos benignos más difíciles rotó de más en 34 de 90 sesiones, y no interrumpió ninguna.»

## Frases que no respalda

- «Detiene el 100 % de los ataques», sin decir «grabados» o «no adaptativos».
- «El contador de bits detecta codificaciones desconocidas.»
- «No tiene costo en el uso normal.»
