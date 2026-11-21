# Evaluación final: cómo leer el resultado

Corrida única del sábado 21 de noviembre de 2026, 09:40, sobre el set de prueba sellado (sello `18dda3af…`, comprobado antes de correr). Configuración congelada `cf56ce20…` (`b 4`, `b_rot 2`, `lambda_rot 0,1`, `T 75`). Commit `cd14e9e`. Los números están en `report.md`, `systems.md` y `RUN.json` de esta carpeta. Este archivo dice qué significan y qué no. Cuando se corrió la evaluación el producto se llamaba Cuentagotas; después se renombró a Alicanto y solo se cambió el nombre en los textos: ni el detector ni las cifras cambiaron.

## El resultado

| | Alicanto | Sin rotación | Sin modelo de evidencia | Lista de destinos + detect-secrets | Presupuesto de bits (réplica) | Reensamblado por sesión (réplica) |
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

1. **Es contra ataques grabados, no contra un atacante que se adapta.** Las sesiones son grabaciones: después de que la clave rota, siguen enviando pedazos de la clave vieja, que ya no sirven. Un agente comprometido de verdad podría releer la clave nueva y seguir. Esta evaluación no lo mide; se midió aparte después (ver «El atacante que se adapta», más abajo).
2. **El contador de bits, solo, no generaliza.** Sin el modelo de evidencia se previenen 40 de 180 (22 %). En familias nuevas, con codificaciones y canales que el motor no sabe leer, lo que detiene el ataque es la evidencia de comportamiento, que rota la clave temprano (mediana: llamada 6). El contador es exacto para las codificaciones que conoce; no es lo que salvó este set.
3. **Hay un costo que no cumple nuestra propia meta.** En 34 de las 90 sesiones benignas difíciles (38 %) el sistema rotó una clave sin necesidad: 39 rotaciones, 5,46 por cada 1.000 llamadas benignas, cuando la meta era 5 como máximo. En las 30 sesiones benignas normales no rotó nunca, y no bloqueó ninguna llamada benigna. Rotar de más cuesta una rotación, no un trabajo interrumpido; aun así es un costo real y hay que decirlo.
4. **El modelo de evidencia está saturado.** Se comporta como un clasificador de «sesión que leyó un secreto y después habla con un destino no confiable». Por eso generaliza a familias nuevas y por eso mismo rota de más en los casos benignos difíciles, que hacen justamente eso de forma legítima.
5. **La cuenta compartida del enjambre no se distingue aquí.** En la familia que reparte el ataque entre varias sesiones, la versión con cuenta por sesión también previene todo, porque la evidencia rota antes. El valor de la cuenta global se ve en la demo del enjambre, con el contador de bits solo, no en esta tabla.
6. **Todo es sintético.** Tráfico benigno y ataques son guiones de nuestro equipo; el fondo benigno del set de prueba sale de las mismas 120 sesiones base que el resto.
7. **Las réplicas no son los productos.** «Presupuesto de bits» y «reensamblado por sesión» son réplicas simplificadas hechas por nosotros a partir de la documentación pública; sus cifras no son las de Pipelock, AgentBrake ni ningún artículo.

## El atacante que se adapta (medido aparte, después)

El punto 1 de arriba se midió después, con el detector ya congelado, en una simulación que se reporta por separado: `results/adaptive/summary.md` (`python -m eval.final.adaptive`). El atacante simulado relee la clave nueva antes de cada envío, así que siempre manda pedazos de la clave vigente.

- **Set de prueba:** 180 de 180 ataques adaptativos no pasan de 96 bits de ninguna versión de la clave (máximo observado 64, mediana 20). Sin rotación, 30 de 180; sin el modelo de evidencia, 63 de 180.
- **Validación:** 70 de 70 (las 10 sesiones de la sustitución propia se excluyeron porque su tabla no se puede reconstruir).
- **Cómo lo frena, y a qué costo:** en el 100 % de los casos del set de prueba el sistema llega a su tope de tres rotaciones y pasa al modo escalado: bloquea toda salida de esa clave hacia destinos no permitidos y avisa a una persona. Contra un atacante persistente no rota indefinidamente: termina deteniendo las salidas. Es una detención con costo operativo, y el costo de ese modo sobre tráfico benigno no está medido.
- Es una simulación: el atacante es un guion que relee y reenvía, no un modelo que busca caminos nuevos.

## Qué aporta cada pieza (ablaciones en validación, hechas después)

Una investigación posterior midió, solo sobre validación y sin tocar el detector, qué hace cada componente. El set de prueba no se volvió a usar.

- **El grafo de archivos y el grafo de llamadas no «conectan pasos lejanos» en ninguna decisión.** La medida R⁺ y las aristas de sospecha están implementadas y probadas, pero ninguna regla las lee; la única regla que usa el grafo de llamadas no se disparó ni una vez en validación.
- **Sí sirven como señales por llamada dentro del modelo de evidencia.** Quitar las señales de los dos grafos no baja los ataques prevenidos, pero sube las rotaciones en sesiones benignas de 0,47 a 7,5 por cada 1.000 llamadas, por encima de la meta de 5. Un indicador binario simple («la llamada toca algún archivo conocido») da lo mismo que la sensibilidad calculada.
- **El modelo de evidencia equivale, en estos datos, a una regla simple:** «la sesión leyó un secreto y esta llamada envía algo a un destino no confiable». Esa regla sola da las mismas cifras que el modelo en validación. Explica por qué generaliza a familias nuevas y por qué rota de más en casos benignos difíciles.
- **Aporte medido del grafo de archivos al separar llamadas de ataque de benignas** (lo que pretendía la prueba T6, aquí sobre validación): la diferencia de AUC es +0,0045, con intervalo al 95 % de 0,0027 a 0,0065. Existe y es muy chica.
- **Conectar R⁺ no mejoraría nada medible con estos datos:** no marca ningún envío que la regla simple no marque. Validación no tiene sesiones benignas con contenido no confiable, así que tampoco puede medir su costo. Queda como trabajo futuro.

Qué se puede decir: «El modelo de evidencia usa señales del grafo de archivos y del grafo de llamadas como indicadores por llamada; en validación reducen las rotaciones en sesiones benignas. La propagación entre pasos lejanos está implementada y probada, pero no conectada a las decisiones, y nuestros datos no permiten medir su aporte.»

## La demo y la evaluación usan configuraciones distintas, a propósito

La demo corre el detector sin modelo de evidencia y rota cuando se filtró el 30 % de la clave. La evaluación usa la configuración congelada, que rota al 10 % y suma la evidencia. Se probó la demo con la configuración congelada: funciona y termina en 401, pero rota en el primer fragmento (llamada 8, con 16 bits en vez de 48), así que el medidor casi no sube y no se ve el goteo. En la demo del enjambre, además, los dos lados terminan en 401 y se pierde el contraste entre cuenta por agente y cuenta global. Por eso la demo se deja como está y se dice.

## Frases que este resultado respalda

- «En 180 ataques de seis familias que el detector no había visto, ninguno sacó más de 32 de los 160 bits de la clave vigente.»
- «Cero llamadas benignas bloqueadas en 5.879.»
- «Sin rotación, los mismos ataques triunfan en 150 de 180.»
- «Cuando duda, rota en vez de bloquear: en los casos benignos más difíciles rotó de más en 34 de 90 sesiones, y no interrumpió ninguna.»

## Frases que no respalda

- «Detiene el 100 % de los ataques», sin decir «grabados» o «no adaptativos».
- «El contador de bits detecta codificaciones desconocidas.»
- «No tiene costo en el uso normal.»
