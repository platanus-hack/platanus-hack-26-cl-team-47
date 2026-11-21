# Pitch y demo en 3 minutos (borrador)

Borrador para que lo reescriba, con su voz, quien va a presentar. Son 3 minutos en total, pitch y demo juntos; el reloj corre desde la primera palabra. La recomendación del evento es 45 segundos de pitch y el resto de demo.

Todo corre desde una sola página. La demo muestra el código funcionando de tres maneras: una corrida grabada del motor (el ataque), una corrida hecha en el momento con lo que elige el público, y al final cómo se probó: el set de prueba sellado, cuyo sello se vuelve a calcular ahí mismo, y las cifras de la evaluación.

## Cómo se abre

Desde la raíz del repositorio, con el entorno de Python del proyecto:

```
python demo/alternativas/03-enjambre-juanpedro/servidor.py
```

y en el navegador, a pantalla completa:

```
http://127.0.0.1:8300/alternativas/03-enjambre-juanpedro/enjambre.html?pitch=1
```

El servidor queda imprimiendo en su terminal cada corrida en vivo y el sello recalculado. Abajo a la derecha, la página muestra el reloj: cuenta hacia atrás desde 3:00 y se pone dorado cuando quedan 20 segundos.

## La línea de tiempo

Tiempos medidos en un ensayo a velocidad real, con el texto de abajo dicho a 150 palabras por minuto. El ensayo terminó en 2:53.

| Reloj | Qué hay en pantalla | Quién avanza | Palabras |
|---|---|---|---|
| 0:00 a 0:40 | Tarjeta de apertura: Alicanto y su frase | Espacio al decir la primera palabra | 100 |
| 0:40 a 1:23 | El ataque: los 20 asistentes, la nota plantada, la clave que se arma, el 200 y la ficha | Espacio; después corre solo | 101 |
| 1:23 a 1:47 | «¿Qué pasa con Alicanto?» y el panel «Ustedes son el atacante» | El público responde; tú tecleas | 48 |
| 1:47 a 1:51 | La consola: lo que imprime el motor, corriendo en ese momento | Enter; después corre solo | |
| 1:51 a 2:21 | Con Alicanto, con el ataque que eligieron: la cuenta, la rotación, el 401 | Corre solo | 69 |
| 2:21 a 2:53 | Cómo lo probamos: equipo rojo, azul y morado, 120 de 180, sus límites y el pedido | Espacio; después corre sola | 81 |

Son 399 palabras: 2 minutos 40 de voz. El resto son las respuestas del público y la consola. Quedan 7 segundos de margen: si quien presenta habla más lento que eso, hay que cortar texto, no apurar la pantalla.

## Qué decir

### 1. Pitch · 0:00 a 0:40

Pulsa espacio al empezar a hablar: parte el reloj y la tarjeta se queda.

> Somos Alicanto. Hoy un equipo trabaja con decenas de agentes de código a la vez, y esos agentes leen de todo: issues, páginas, documentación que escribe cualquiera. Basta una nota plantada para que un agente saque una clave. No es teoría: en 2025, CamoLeak sacó secretos de repositorios privados a través de Copilot Chat, carácter por carácter. Casi todos los guardias miran cada llamada, o cada agente, por separado, y bloquean. Nosotros contamos cuánta clave ya salió, sumando entre todos los agentes, y la cambiamos antes de que sirva. Quien sigue al alicanto por codicia termina con las manos vacías.

### 2. El ataque · 0:40 a 1:23

Pulsa espacio. Corre solo: habla encima, sin apurarte, que la pantalla lleva el ritmo.

> Una clínica ficticia. Su equipo de TI trabaja con veinte asistentes de código. A uno le piden arreglar un error de la agenda. Abre el issue, y adentro viene una nota que el equipo no escribió: pide la clave de las fichas, de a cuatro letras. El atacante no trae agentes: usa los de la clínica. Diez leen la clave, que es parte de su trabajo, y cada uno manda un pedazo. Cada asistente tiene su propio monitor, y ninguno ve más de dieciséis bits de ciento sesenta. El atacante arma la clave completa, y la API le entrega una ficha.

### 3. El público elige · 1:23 a 1:51

La tarjeta y el panel aparecen solos. Mira al jurado.

> ¿Qué pasa con Alicanto? Ustedes son el atacante. ¿Entre cuántos asistentes reparten la clave: uno, dos, cinco o diez?

Teclea lo que digan: `1`, `2`, `5` o `0` para diez.

> ¿Cómo esconden cada pedazo: tal cual, en base64 o al revés?

Teclea `T`, `B` o `R`.

> Díganme un número cualquiera.

Teclea el número y pulsa Enter.

> Esto que ven es el motor del repositorio, corriendo ahora con lo que eligieron.

La consola muestra el comando y lo que imprimió el motor. Según lo que hayan elegido, di una de estas dos frases mientras se lee:

- **Si eligieron 5 o 10:** «Con un monitor por agente, su ataque pasa: el atacante recibe 200.»
- **Si eligieron 1 o 2:** «Con tan pocos asistentes, hasta un monitor por agente lo frena. Por eso el atacante reparte. Miren qué hace Alicanto con lo mismo.»

### 4. Con Alicanto, en vivo · 1:51 a 2:21

Corre solo, con el ataque que eligieron. El título lo dice: «Con Alicanto, en vivo».

> Todo lo que sale pasa por Alicanto, que lleva una sola cuenta por clave, no por agente. Sale un pedazo, sale otro. Al tercero la cuenta llega a su límite. Alicanto no bloquea a nadie: le pide al gestor de secretos que cambie la clave. Lo que el atacante juntó es de la clave vieja. Sigue juntando, prueba, y recibe 401. Cero fichas, y los veinte asistentes siguieron trabajando.

Si eligieron base64 o al revés, agrega al pasar: «La escondieron, y da lo mismo: contamos información, no formato».

### 5. Cómo lo probamos · 2:21 a 2:53

Cuando aparezca el 401 en grande, pulsa espacio. La escena corre sola, y cada frase tiene su momento en pantalla.

> ¿Y funciona? Lo probamos con equipo rojo, azul y morado. El rojo escribió 180 ataques de familias nuevas sin ver el detector, y los selló.

En pantalla: los tres equipos, con el rojo encendido, y debajo el set entero bajo su precinto: una fila por familia, una casilla por ataque o por sesión normal. A los 9 segundos se encienden el azul y el morado.

> El azul congeló el detector antes de abrirlos. Se midió una sola vez.

A los 14 segundos se va el precinto y las casillas se llenan: claras las que frenó, en oro las que no. La cifra sube hasta 120.

> Como lo ve el proxy en vivo, frenó 120, sin bloquear ninguna llamada normal.

A los 20 segundos aparece el costo: las sesiones normales en que rotó de más, en gris.

> Rotó de más en 34 de 90 casos difíciles, y las dos familias que se escapan están publicadas.

A los 27 segundos aparece el pedido y lo demás se atenúa.

> Buscamos dos equipos con agentes de código para un piloto. Gracias.

Si vas adelantado, el espacio pasa al paso siguiente, y sigue sola desde ahí; no pasa del pedido. La flecha izquierda vuelve un paso y la deja en tus manos.

### Para las preguntas

Con la escena abierta, la flecha derecha muestra un paso más: la misma medición con otros guardias. Alicanto 120; una regla simple, 90; una lista de destinos con escáner de secretos, 30. Las dos réplicas son versiones simplificadas hechas por nosotros, no los productos.

Respuestas cortas, con su fuente:

- **¿Quién es el equipo rojo?** Una sesión de agente aparte, que tenía prohibido abrir el código del detector. No es otro grupo de personas. Es una regla de trabajo: desde fuera no se puede comprobar. El sello y el congelamiento, sí (`redteam/SELLO.md`).
- **¿Por qué 120 y no 180?** Con las marcas que traían las grabaciones son 180. El proxy en vivo calcula esas marcas de otra forma, y con las suyas son 120. Decimos la del proxy (`results/test/LECTURA.md`).
- **¿Cuáles se escapan?** La clave enviada a su propio destino permitido, y la escondida en commits de git. En la segunda, el proxy en vivo bloquea el push, pero el set cuenta la fuga en cada commit.
- **¿Qué son las 34?** Sesiones normales en que cambió una clave sin necesidad. 30 son de una misma familia: sesiones que leen contenido ajeno lleno de claves de ejemplo. No bloqueó ninguna llamada.
- **¿Se puede repetir?** Sí: `python -m eval.final.proxy_flags --out /tmp/pf`, unos tres minutos. La repetimos el sábado a las 19:20 y dio las mismas cifras.
- **¿Son 180 casos independientes?** No: son 30 réplicas de seis plantillas. Se lee «cuatro de seis familias».

## Teclas

| Tecla | Qué hace |
|---|---|
| Espacio | Parte el reloj; después parte la demo; al final abre «Cómo lo probamos». En medio, pausa y sigue |
| `1` `2` `5` `0` | En el panel: entre cuántos asistentes (el `0` es diez) |
| `T` `B` `R` | En el panel: tal cual, base64, al revés |
| Números y Enter | En el panel: el número del público, y correr |
| Flechas y Enter | En el panel: otra forma de elegir. Fuera del panel: un cuadro adelante o atrás |
| Retroceso | En el panel: borra o vuelve a la pregunta anterior |
| `S` | Salta las llamadas normales hasta lo próximo que importa. Para cuando el reloj aprieta |
| `E` | Abre «Cómo lo probamos» desde cualquier momento. Adentro: espacio y flechas cambian de paso; Escape la cierra |
| Escape | En el panel: no corre nada y sigue la corrida grabada |
| `R` | Vuelve al principio |

## Si algo falla

- **El público no contesta.** Elige tú en voz alta: «Diez, en base64, y el número de hoy: veintidós». Si vas tarde, pulsa Enter tres veces: corre con diez asistentes, tal cual y un número sacado del reloj.
- **El servidor no está corriendo.** El panel lo dice («No hay servidor en vivo en este computador») y sigue la corrida grabada. Dilo tal cual: «Esta es la corrida grabada». No digas que corrió en vivo. La escena final muestra igual las cifras y el sello publicado; solo falta la línea «recalculado recién aquí».
- **Vas tarde.** Cuando quedan menos de 50 segundos y todavía no aparece el 401, pulsa `S` un par de veces: salta a la rotación y al resultado. Si quedan menos de 35, pulsa `E`: abre «Cómo lo probamos» de inmediato.
- **Se cae el navegador.** Recarga la página y pulsa espacio dos veces. Si no hay tiempo, usa la demo oficial y su video de respaldo (`demo/README.md`).
- **Preguntan por un pedazo más chico que 4 letras.** Es un límite conocido y publicado: el contador no lee pedazos de menos de 4. Está en `pitch/PREGUNTAS.md`.

## Qué es real y qué no, para decirlo si preguntan

- **Real, en vivo:** la corrida de la mitad. El motor del repositorio procesa las 88 llamadas con lo que eligió el público, y lo que se ve después sale de esa corrida. El comando está en la consola y se puede repetir a mano.
- **Real, en vivo:** el sello del set de prueba. Al abrir «Cómo lo probamos», el servidor vuelve a calcular el sha256 de los 335 archivos del set y la página lo compara con el que se publicó a las 07:10. Si no coincidiera, la página lo diría.
- **Real, grabado:** el ataque del principio. Es una corrida del mismo motor, guardada en el repositorio.
- **Real, medido antes:** las cifras de «Cómo lo probamos». La página no las calcula: las lee de `evaluacion.json`, que `hacer_evaluacion.py` copia de `results/` y de `redteam/SELLO.md`. Un test regenera ese archivo y lo compara.
- **Guion:** el agente. No es un modelo: es una secuencia fija de llamadas. Tres modelos reales pasaron por el proxy en 21 corridas y ninguno siguió la nota plantada.
- **Maqueta:** la pantalla de la clínica, la tarea que se escribe y la ficha.

## Qué no decir

- Que Alicanto frenó a un modelo real: no hubo fuga que frenar.
- Que un enjambre ya robó una clave así: no hay un caso real; es la hipótesis de la demo.
- Cifras de la evaluación para el enjambre de la demo: ese ataque no está en el set sellado. La familia repartida del set (A7) son tres agentes.
- «Detiene todo»: son 120 de 180, con ataques grabados.
- «180 de 180» sin decir en la misma frase que es con las marcas de las grabaciones.
- Que el equipo rojo fue otro grupo de personas, o que se puede comprobar desde fuera que no vio el detector.

## Antes de salir a escena

1. El servidor corriendo, y en su terminal la línea «Motor listo».
2. La página abierta con `?pitch=1`, a pantalla completa, en el proyector de verdad.
3. Una pasada entera con reloj: debe terminar antes de 2:55.
4. En esa pasada, al llegar a «Cómo lo probamos», la terminal del servidor imprime «sello del set de prueba, recalculado: … coincide con el publicado».
5. El video de respaldo de la demo oficial a mano.
6. Nadie corre tests ni agentes en ese computador durante el pitch.
