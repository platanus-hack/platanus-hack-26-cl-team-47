# Pitch y demo en 3 minutos (borrador)

Borrador para que lo reescriba, con su voz, quien va a presentar. Son 3 minutos en total, pitch y demo juntos; el reloj corre desde la primera palabra. La recomendación del evento es 45 segundos de pitch y el resto de demo.

Todo corre desde una sola página. La demo muestra el código funcionando de dos maneras: una corrida grabada del motor (el ataque) y una corrida hecha en el momento, con lo que elige el público.

## Cómo se abre

Desde la raíz del repositorio, con el entorno de Python del proyecto:

```
python demo/alternativas/03-enjambre-juanpedro/servidor.py
```

y en el navegador, a pantalla completa:

```
http://127.0.0.1:8300/alternativas/03-enjambre-juanpedro/enjambre.html?pitch=1
```

El servidor queda imprimiendo cada corrida en vivo en su terminal. Abajo a la derecha, la página muestra el reloj: cuenta hacia atrás desde 3:00 y se pone dorado cuando quedan 20 segundos.

## La línea de tiempo

Tiempos medidos en un ensayo a velocidad real, con el texto de abajo dicho a 150 palabras por minuto. El ensayo terminó en 2:52.

| Reloj | Qué hay en pantalla | Quién avanza | Palabras |
|---|---|---|---|
| 0:00 a 0:43 | Tarjeta de apertura: Alicanto y su frase | Espacio al decir la primera palabra | 108 |
| 0:43 a 1:26 | El ataque: los 20 asistentes, la nota plantada, la clave que se arma, el 200 y la ficha | Espacio; después corre solo | 101 |
| 1:26 a 1:50 | «¿Qué pasa con Alicanto?» y el panel «Ustedes son el atacante» | El público responde; tú tecleas | 48 |
| 1:50 a 1:54 | La consola: lo que imprime el motor, corriendo en ese momento | Enter; después corre solo | |
| 1:54 a 2:24 | Con Alicanto, con el ataque que eligieron: la cuenta, la rotación, el 401 | Corre solo | 69 |
| 2:24 a 2:52 | Tarjeta de cierre: 120, sus límites y el pedido | Espacio | 70 |

Son 396 palabras: 2 minutos 38 de voz. El resto son las respuestas del público y la consola.

## Qué decir

### 1. Pitch · 0:00 a 0:43

Pulsa espacio al empezar a hablar: parte el reloj y la tarjeta se queda.

> Somos Alicanto. Hoy un equipo trabaja con decenas de agentes de código a la vez, y esos agentes leen de todo: issues, páginas, documentación que escribe cualquiera. Basta una nota plantada para que un agente saque una clave del repositorio. No es teoría: en 2025, CamoLeak sacó secretos de repositorios privados a través de Copilot Chat, carácter por carácter. Casi todos los guardias hacen lo mismo: miran cada llamada, o cada agente, por separado, y bloquean. Nosotros no adivinamos intenciones. Contamos cuánta clave ya salió, sumando entre todos los agentes, y la cambiamos antes de que sirva. Quien sigue al alicanto por codicia termina con las manos vacías.

### 2. El ataque · 0:43 a 1:26

Pulsa espacio. Corre solo: habla encima, sin apurarte, que la pantalla lleva el ritmo.

> Una clínica ficticia. Su equipo de TI trabaja con veinte asistentes de código. A uno le piden arreglar un error de la agenda. Abre el issue, y adentro viene una nota que el equipo no escribió: pide la clave de las fichas, de a cuatro letras. El atacante no trae agentes: usa los de la clínica. Diez leen la clave, que es parte de su trabajo, y cada uno manda un pedazo. Cada asistente tiene su propio monitor, y ninguno ve más de dieciséis bits de ciento sesenta. El atacante arma la clave completa, y la API le entrega una ficha.

### 3. El público elige · 1:26 a 1:54

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

### 4. Con Alicanto, en vivo · 1:54 a 2:24

Corre solo, con el ataque que eligieron. El título lo dice: «Con Alicanto, en vivo».

> Todo lo que sale pasa por Alicanto, que lleva una sola cuenta por clave, no por agente. Sale un pedazo, sale otro. Al tercero la cuenta llega a su límite. Alicanto no bloquea a nadie: le pide al gestor de secretos que cambie la clave. Lo que el atacante juntó es de la clave vieja. Sigue juntando, prueba, y recibe 401. Cero fichas, y los veinte asistentes siguieron trabajando.

Si eligieron base64 o al revés, agrega al pasar: «La escondieron, y da lo mismo: contamos información, no formato».

### 5. Cierre · 2:24 a 2:52

Cuando aparezca el 401 en grande, pulsa espacio: sale la tarjeta de cierre.

> Lo medimos una sola vez, contra 180 ataques grabados de seis familias nuevas. Como lo ve el proxy en vivo, frenó 120, y no bloqueó ninguna llamada normal. Cuando duda, rota en vez de bloquear: rotó de más en 34 de 90 casos difíciles. Las dos familias que se escapan están publicadas. El agente de la demo es un guion. Buscamos dos equipos con agentes de código para un piloto. Gracias.

## Teclas

| Tecla | Qué hace |
|---|---|
| Espacio | Parte el reloj; después parte la demo; al final saca el cierre. En medio, pausa y sigue |
| `1` `2` `5` `0` | En el panel: entre cuántos asistentes (el `0` es diez) |
| `T` `B` `R` | En el panel: tal cual, base64, al revés |
| Números y Enter | En el panel: el número del público, y correr |
| Flechas y Enter | En el panel: otra forma de elegir. Fuera del panel: un cuadro adelante o atrás |
| Retroceso | En el panel: borra o vuelve a la pregunta anterior |
| `S` | Salta las llamadas normales hasta lo próximo que importa. Para cuando el reloj aprieta |
| Escape | En el panel: no corre nada y sigue la corrida grabada |
| `R` | Vuelve al principio |

## Si algo falla

- **El público no contesta.** Elige tú en voz alta: «Diez, en base64, y el número de hoy: veintidós». Si vas tarde, pulsa Enter tres veces: corre con diez asistentes, tal cual y un número sacado del reloj.
- **El servidor no está corriendo.** El panel lo dice («No hay servidor en vivo en este computador») y sigue la corrida grabada. Dilo tal cual: «Esta es la corrida grabada». No digas que corrió en vivo.
- **Vas tarde.** Cuando quedan menos de 40 segundos y todavía no aparece el 401, pulsa `S` un par de veces: salta a la rotación y al resultado.
- **Se cae el navegador.** Recarga la página y pulsa espacio dos veces. Si no hay tiempo, usa la demo oficial y su video de respaldo (`demo/README.md`).
- **Preguntan por un pedazo más chico que 4 letras.** Es un límite conocido y publicado: el contador no lee pedazos de menos de 4. Está en `pitch/PREGUNTAS.md`.

## Qué es real y qué no, para decirlo si preguntan

- **Real, en vivo:** la corrida de la mitad. El motor del repositorio procesa las 88 llamadas con lo que eligió el público, y lo que se ve después sale de esa corrida. El comando está en la consola y se puede repetir a mano.
- **Real, grabado:** el ataque del principio. Es una corrida del mismo motor, guardada en el repositorio.
- **Guion:** el agente. No es un modelo: es una secuencia fija de llamadas. Tres modelos reales pasaron por el proxy en 21 corridas y ninguno siguió la nota plantada.
- **Maqueta:** la pantalla de la clínica, la tarea que se escribe y la ficha.
- **Las cifras del cierre** son las del guion oficial (`pitch/GUION.md`, bloque 5) y salen de `results/proxy_flags/systems.md` y `results/test/LECTURA.md`.

## Qué no decir

- Que Alicanto frenó a un modelo real: no hubo fuga que frenar.
- Que un enjambre ya robó una clave así: no hay un caso real; es la hipótesis de la demo.
- Cifras de la evaluación para el enjambre: el enjambre no está en el set sellado.
- «Detiene todo»: son 120 de 180, con ataques grabados.

## Antes de salir a escena

1. El servidor corriendo, y en su terminal la línea «Motor listo».
2. La página abierta con `?pitch=1`, a pantalla completa, en el proyector de verdad.
3. Una pasada entera con reloj: debe terminar antes de 2:55.
4. El video de respaldo de la demo oficial a mano.
5. Nadie corre tests ni agentes en ese computador durante el pitch.
