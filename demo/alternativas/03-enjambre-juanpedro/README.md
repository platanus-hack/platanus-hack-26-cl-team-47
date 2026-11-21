# 03. 20 agentes, una clave

- **Quién la hizo:** Juan Pedro y su Claude.
- **Estado:** funciona con una corrida real de 20 agentes, grabada con el arnés del enjambre del repositorio, y con corridas hechas en el momento, con lo que elige el público.
- **Cómo abrirla:** `python -m http.server 8300 --directory demo` y luego `http://127.0.0.1:8300/alternativas/03-enjambre-juanpedro/enjambre.html`. Pulsa espacio para reproducir: corre entera, del mundo sin Alicanto al mundo con Alicanto, sin tocar nada más.
- **El pitch de 3 minutos, con la parte en vivo:** `python demo/alternativas/03-enjambre-juanpedro/servidor.py` (en vez del servidor de arriba) y luego `http://127.0.0.1:8300/alternativas/03-enjambre-juanpedro/enjambre.html?pitch=1`. El guion está en [GUION_3_MIN.md](GUION_3_MIN.md).

## Qué muestra

Es una simulación sobre una clínica inventada. La pantalla tiene tres zonas, de izquierda a derecha: el servidor del atacante, los 20 asistentes de código de la clínica, y la clínica (su equipo de TI, el repositorio con la clave, el gestor de secretos y la API de fichas).

1. **De dónde vienen los agentes.** Los 20 asistentes aparecen uno por uno y la clínica tiende una línea a cada uno: son suyos, los usa su equipo de TI sobre el mismo repositorio. El servidor del atacante dice que no tiene agentes propios y muestra un emblema con lo que busca: una llave que apunta a una ficha.
2. **Adentro de uno.** La cámara entra a una pantalla: la agenda médica del día, con un error en la última franja, y el asistente de código. La tarea se escribe letra por letra. El asistente abre el issue y aparece la nota plantada, marcada, con tres líneas que dicen qué busca: la clave de la API de fichas, de a 4 caracteres, hacia el servidor de quien la plantó.
3. **La cámara vuelve a salir.** El atacante no trae agentes: va a usar los 20 de la clínica.
4. **Sin Alicanto.** Diez asistentes leen la clave del repositorio (una ficha «clave» viaja de la clínica a cada uno). Después cada uno manda un pedazo de 4 caracteres, que viaja hasta su lugar en la clave del atacante. Cada asistente tiene su propio monitor, con una marca donde rotaría, y ninguno pasa de 16 de 160 bits. El atacante completa la clave, la prueba contra la API de la clínica y recibe una ficha. El resultado se agranda hasta llenar la pantalla: un 200 y la ficha completa que se lleva.
5. **Con Alicanto.** El resultado anterior se sostiene 5 segundos y la escena sigue sola: un corte a negro pregunta «¿Qué pasa con Alicanto?», con «Nuestra solución, frente a la misma nota plantada» debajo. Aparece una pieza nueva en la salida, entre los asistentes y el atacante, con una sola cuenta por clave. La rotación se cuenta en tres tiempos:
   - la cuenta llega a su límite, 48 de 160 bits, con el tercer pedazo;
   - Alicanto le pide al gestor de secretos de la clínica que cambie la clave (la orden viaja por arriba y el gestor muestra «versión 1, anulada» y «versión 2, vigente»);
   - lo que el atacante había juntado se vuelve ceniza.

   Los pedazos siguen saliendo, sin bloqueos, pero son de la clave vieja. El atacante prueba lo que juntó y la API responde 401. Quedan marcados los tres asistentes de los que salieron los pedazos antes de rotar, y el resultado se agranda igual que antes: un 401, la clave tachada y «0 fichas».

Abajo va siempre una frase que cuenta lo que pasa, como subtítulo.

Tres recursos ayudan a seguirla:

- **El emblema del atacante sigue la historia.** La llave se llena con cada pedazo que recibe. Si la clave rota, se apaga y queda tachada; si logra entrar, la ficha se ilumina.
- **En los momentos clave, lo demás se atenúa.** En la rotación quedan a la vista Alicanto y el gestor de secretos; en el cobro, el atacante y la API.
- **El resultado en grande se puede deshacer.** Flecha izquierda vuelve un cuadro y muestra el grafo completo, con el resultado chico.

Con todo a la vista, un clic en cualquier pantalla acerca la cámara a ese asistente y muestra sus llamadas; Escape vuelve. Teclas: espacio (reproducir o pausar), flechas (un paso), 1 y 2 (sin y con Alicanto), R (inicio).

Dura 64 segundos sin Alicanto (27 de ellos son el origen y el prólogo) y 46 con Alicanto: 1 minuto 50 en total. `?speed=1.3` lo deja en 1 minuto 25; las flechas permiten saltar cuadros. `?w=b` parte directo en el mundo con Alicanto.

## El pitch de 3 minutos: el público elige el ataque y el motor corre en vivo

Con `?pitch=1` la misma página lleva los 3 minutos completos, con un reloj que cuenta hacia atrás:

1. **Apertura.** Una tarjeta con el nombre y la frase, sobre la que se dice el pitch.
2. **El ataque.** La corrida grabada: los 20 asistentes, la nota plantada, la clave completa y la ficha.
3. **El público es el atacante.** La página pregunta entre cuántos asistentes reparten la clave (1, 2, 5 o 10), cómo esconden cada pedazo (tal cual, en base64 o al revés) y pide un número cualquiera.
4. **El motor corre en ese momento.** `servidor.py` arma la sesión con esos valores y la pasa por el motor del repositorio. La página muestra el comando y lo que imprimió, tal cual, y la terminal del servidor imprime lo mismo.
5. **Con Alicanto, con ese ataque.** Lo que se ve después sale de esa corrida, no de la grabada. En la rotación aparece la decisión real del motor: la acción, los bits y cuánto tardó.
6. **Cierre.** Una tarjeta con la cifra de la evaluación, sus límites y el pedido.

Qué cambia según lo que elija el público, comprobado corriendo las 12 combinaciones con dos números distintos:

| Reparten la clave entre | Un monitor por agente | Alicanto, cuenta por clave |
|---|---|---|
| 1 asistente | lo frena: 401 | lo frena en la llamada 48: 401 |
| 2 asistentes | lo frena, más tarde: 401 | lo frena en la llamada 48: 401 |
| 5 asistentes | no lo ve (32 de 160 bits como máximo): 200 | lo frena en la llamada 48: 401 |
| 10 asistentes | no lo ve (16 de 160 bits como máximo): 200 | lo frena en la llamada 48: 401 |

El disfraz no cambia ninguna fila, y el número solo cambia qué asistentes filtran y en qué orden. En las 24 corridas, 0 llamadas bloqueadas.

En un ensayo a velocidad real, con el texto del guion dicho a 150 palabras por minuto, el pitch completo terminó en 2 minutos 52.

Sin `servidor.py` la página igual funciona: el panel avisa que no hay servidor en vivo y sigue la corrida grabada. Fuera del pitch, la tecla `V` abre el panel del público en cualquier momento.

## Cómo se ve y por qué

- **Dos materiales:** lo claro es de la clínica (sus 20 pantallas, su repositorio, su gestor de secretos, su API) y lo oscuro es afuera. La pantalla de la clínica es una sola, repetida 20 veces a escala; no son miniaturas dibujadas aparte.
- **Un solo color con significado:** el oro es la clave viva y la ceniza es la clave muerta. La ficha robada es un pedazo blanco de la clínica en manos del atacante.
- **El sentido de lectura es el del robo:** la clave vive a la derecha, pasa por los asistentes y sale hacia la izquierda. Alicanto queda justo en esa salida.
- **Sin adornos:** sin degradados, brillos, sombras en reposo, etiquetas en mayúsculas chicas ni tarjetas redondeadas.
- **Movimiento con reglas:** la cámara tarda 1,4 segundos y después se queda quieta mientras la pantalla actúa. Lo que llega frena largo; lo que cruza la pantalla acelera y frena. Las cascadas no son parejas. Cada subtítulo cabe en dos líneas y queda en pantalla lo que toma leerlo (medio segundo más 0,3 por palabra). Las curvas y los tiempos salen de guías públicas de motion (HyperFrames, Emil Kowalski, impeccable, LottieFiles, BBC para subtítulos).

## Los primeros 10 segundos

Alguien del jurado ve tres cosas con nombre: un atacante a la izquierda, una clínica a la derecha y, entre los dos, veinte pantallas de la clínica. Entiende de quién son los agentes antes de que pase nada. A los 10 segundos la cámara ya está entrando a una de esas pantallas.

Frase sugerida para quien presenta: «Una clínica trabaja con veinte asistentes de código. Alguien de afuera planta una nota en un issue. No trae agentes: usa los de la clínica. Cada uno manda cuatro letras, ningún monitor ve nada raro y el atacante se lleva la clave completa. Ahora lo mismo con Alicanto en la salida: al tercer pedazo le pide a la clínica que cambie la clave, nadie queda bloqueado y lo robado ya no sirve.»

## Qué criterio empuja

- **Originalidad (15):** muestra el ataque repartido entre muchos agentes y la respuesta que distingue a Alicanto, que es rotar la clave en vez de bloquear a un agente.
- **Impacto (20):** parte de una pantalla cotidiana y termina en una consecuencia visible, la ficha abierta contra «manos vacías».
- **Ejecución (20):** se entiende sin explicación y se lee completa a 1024×768, 1280×720 y 1440×900.
- **Aspecto técnico (25):** la corrida es real y se reproduce con un comando; un test la vuelve a correr y compara.

## Qué es real y qué es maqueta

- **Real (sale de ejecutar el código del repositorio):**
  - `hacer_corrida.py` arma una sesión de 88 llamadas entre 20 agentes y la pasa dos veces por `run_swarm_panel` de `demo/run_split.py`, con los mismos parámetros del enjambre de la demo oficial (`SWARM_PARAMS`): una vez con un monitor por agente y otra con la cuenta global.
  - Salió así al primer intento, sin ajustar nada. Con un monitor por agente: 0 rotaciones y cobro 200. Con la cuenta global: una rotación en la llamada 48, 0 llamadas bloqueadas y cobro 401.
  - En pantalla, cada llamada de cada agente, cada pedazo, la rotación y el resultado del cobro salen de `grabaciones/por_agente.jsonl` y `grabaciones/global.jsonl`.
  - **La parte en vivo del pitch es una corrida de verdad.** `servidor.py` llama a `hacer_corrida.py` con lo que eligió el público; el motor procesa las 88 llamadas en unos 200 ms y la página dibuja esos eventos. El texto de la consola es lo que devolvió esa corrida, sin editar. Se puede repetir a mano: `python demo/alternativas/03-enjambre-juanpedro/hacer_corrida.py --reparten 5 --disfraz base64 --semilla 37`.
  - **La línea «motor»** de abajo a la derecha es la decisión grabada del motor en la llamada que rota (acción, bits y milisegundos), o los datos de la corrida en vivo.
- **Maqueta, y lo dice en pantalla:**
  - **La pantalla de la clínica** (módulos, cifras del día, agenda, pacientes, el error de la última franja): es decorado. Los pacientes son inventados.
  - **La tarea que se escribe** («Arregla el error de la última franja de la agenda. Es el issue 14»): la sesión es un guion, nadie escribió ese mensaje. Las llamadas que aparecen debajo sí son las grabadas de cada agente.
  - **Las tres líneas que explican la nota plantada** y los subtítulos: son texto nuestro. El texto de la nota sí es la salida grabada de la llamada 2.
  - **La columna de la clínica** (equipo de TI, repositorio, gestor de secretos, API): son rótulos nuestros sobre hechos de la corrida. La clave que muestra el repositorio es la del archivo `.env` grabado, abreviada; «versión 2» es la rotación grabada; el 200 y el 401 son el cobro grabado.
  - **La rotación en tres tiempos:** en la grabación es un solo evento, en la llamada 48. La página lo separa en tres cuadros para que se entienda; el reloj no avanza entre ellos.
  - **Las fichas que viajan** («clave», el pedazo, «cambia la clave») dibujan llamadas grabadas: la lectura de `.env`, el envío a `attacker.test` y la rotación.
  - **La ficha clínica del resultado** (nombre, diagnósticos, medicamentos, alergias): es inventada entera, y lo dice la propia ficha. La API del banco de pruebas responde solo `{"ok": true}`.
  - **El emblema del atacante y el corte a negro:** son gráfica y texto nuestros. El avance de la llave sí sale de los caracteres recibidos en la grabación.
  - **Las tarjetas del pitch:** la apertura es texto nuestro. Las cifras del cierre son las del guion oficial (`pitch/GUION.md`, bloque 5) y salen de `results/proxy_flags/systems.md` (120 de 180) y `results/test/LECTURA.md` (34 de 90).
- **El agente es un guion reproducible, no un modelo.** En las corridas con modelos reales del equipo, ninguno siguió la instrucción plantada.
- **Dos cosas que la página deriva:**
  - Los bits «en manos del atacante» son los caracteres recibidos por 4 bits (clave hexadecimal), que calza con los 160 bits del cobro grabado.
  - Desde la rotación, todos los caracteres se dan por muertos. Vale porque los diez agentes leyeron la clave antes de que rotara; un test lo comprueba.
- **De dónde sale cada cifra:**

| Cifra | De dónde sale |
|---|---|
| 20 agentes, 88 llamadas | `grabaciones/sesion.jsonl` |
| 16 de 160 bits («lo máximo que vio un monitor») | el máximo de `leak.SECRET_1.bits` en `por_agente.jsonl` |
| 160 bits, cobro 200 | el evento del atacante en `por_agente.jsonl` |
| Llamada 48, 48 bits («sumaba la cuenta global cuando rotó») | el evento `rotation` y su decisión en `global.jsonl` |
| 0 bloqueadas, cobro 401 | las decisiones y el evento del atacante en `global.jsonl` |
| Agentes 15, 04 y 13 | los pedazos que salieron hasta la llamada 48 en `global.jsonl` |

## Por qué son 10 los que filtran y no los 20

La clave tiene 40 caracteres y el motor cuenta pedazos de 4, así que hay 10 pedazos. Cada uno sale de un agente distinto; los otros 10 solo trabajan, y sirven para mostrar que a ninguno se le interrumpe.

## Límites que hay que decir

- **Los 20 agentes corren en una misma máquina.** La cuenta compartida cubre eso; coordinar varias máquinas es trabajo futuro.
- **El enjambre no está en la evaluación final.** No se le pueden pegar las cifras del set sellado.
- **Usa la configuración de la demo:** decide solo el contador de bits y rota al 30 % de la clave.
- **Con pedazos de menos de 4 caracteres el contador no los ve.** Por eso la demo usa pedazos de 4.

## Casos reales en que se apoya la simulación

No encontramos ningún caso real de una clave filtrada por pedazos entre varios agentes: esa combinación es la hipótesis de la demo. Lo que sí está documentado, por separado:

- **Un ataque partido en tareas que parecen inocentes.** Anthropic informó en noviembre de 2025 una campaña de espionaje contra unas 30 organizaciones en que el orquestador partía el ataque en tareas para subagentes, cada una de apariencia legítima vista por separado. Eran agentes del atacante, no de las víctimas. [Informe](https://www.anthropic.com/news/disrupting-AI-espionage)
- **Un agente que filtra una credencial por leer contenido plantado.** En febrero de 2026, el título de un issue manipuló al bot de IA que clasificaba issues en Cline; días después alguien publicó en npm una versión maliciosa con un token que seguía activo. [Snyk](https://snyk.io/blog/cline-supply-chain-attack-prompt-injection-github-actions)
- **Sacar datos de a poco para no gatillar alarmas.** Es una técnica catalogada (MITRE ATT&CK T1030, transferencia en trozos de tamaño fijo). [MITRE](https://attack.mitre.org/techniques/T1030/)
- **Salud en Chile.** Los prestadores de salud son servicio esencial bajo la Ley 21.663, con alerta temprana a la ANCI en un máximo de 3 horas. [ANCI](https://anci.gob.cl/documents/4692/PPT_Presentacion_SE_y_OIV_VF.pdf)

Antes de poner cualquiera de estos datos en una lámina, una persona debe abrir la fuente.

## La clínica es inventada

«Clínica Tres Cóndores» no existe y la pantalla no imita a ningún prestador real: no usa nombres, logos, colores ni disposición de ninguno. Solo sigue convenciones comunes de los portales chilenos (agenda médica, admisión, ficha clínica electrónica, órdenes y resultados, previsión Fonasa o Isapre, estados de la hora), para que se vea verosímil. El nombre sigue el del escenario de la demo oficial.

## Qué falta y cuánto cuesta

- **Elegirla y publicarla:** hoy se abre solo en local. Llevarla a `demo/viz/` y redesplegar, media hora.
- **Que una persona reescriba el guion y lo ensaye:** `GUION_3_MIN.md` es un borrador. Reemplazaría al guion oficial de `pitch/GUION.md`, que es de otra área: lo decide el líder. Una hora, con dos o tres pasadas con reloj en el proyector de verdad.
- **Que la API devuelva una ficha sintética de verdad**, para que la tarjeta deje de ser maqueta: 1 hora, en `services/api`.
- **Mostrar que la clínica sigue funcionando después de rotar** (una llamada legítima con la clave nueva): 1 a 2 horas, en `demo/run_split.py` o `services/`.

## Riesgos

- **Proyector:** probada a 1024×768, 1280×720 y 1440×900. Un test comprueba que nada se sale ni se corta y que ninguna zona pisa a otra (`test_enjambre.py`, con Playwright).
- **Teléfono:** no es su lugar. No se rompe ni se desplaza hacia el lado, pero las 20 pantallas quedan muy chicas.
- **Letra chica:** con todo a la vista, cada pantalla mide unos 85 píxeles de ancho a 1024×768. Se entiende por la forma (quién manda un pedazo) y por el subtítulo, no por leer cada una.
- **Rendimiento:** la cámara se anima cuadro a cuadro con 20 copias de la pantalla. En el computador donde se hizo, con el navegador sin ventana, cada cuadro tardó 16,7 ms al entrar y al salir (60 por segundo). Eso no garantiza lo mismo con un proyector conectado: hay que mirarla corriendo en el computador del pitch.
- **Duración:** 1 minuto 50 es largo para un pitch de 3 minutos. Hay que decidir entre acelerarla, saltar cuadros o acortar el prólogo.
- **Red:** no usa internet; necesita el servidor local.
- **La parte en vivo depende de `servidor.py`.** Si no está corriendo, la página lo dice en pantalla y sigue con la corrida grabada; quien presenta tiene que decirlo igual. El servidor escucha solo en este computador (127.0.0.1) y no acepta más valores que los que ofrece la página.
- **El público puede elegir 1 o 2 asistentes.** Ahí hasta un monitor por agente frena el ataque, y hay que tener lista la frase para ese caso (está en el guion).
- **El pitch va justo.** El ensayo dejó 8 segundos de margen. La tecla `S` salta las llamadas normales si el reloj aprieta.
- **Si el motor cambia** y la corrida deja de dar lo mismo, `test_la_corrida_se_reproduce_con_el_arnes_del_repositorio` falla y lo dice. Para regenerar: `python demo/alternativas/03-enjambre-juanpedro/hacer_corrida.py`.
- **Respaldo:** la demo oficial y sus videos.

Tests: `python -m pytest demo/alternativas/03-enjambre-juanpedro -q`.
