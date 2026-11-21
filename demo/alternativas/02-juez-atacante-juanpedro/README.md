# 02. El juez es el atacante

- **Quién la hizo:** Juan Pedro y su Claude.
- **Estado:** funciona con una corrida real (las grabaciones de la demo oficial). Falta ponerla al alcance de un teléfono: ver «Qué falta».
- **Cómo abrirla:** `python -m http.server 8300 --directory demo` y luego `http://127.0.0.1:8300/alternativas/02-juez-atacante-juanpedro/atacante.html?h=1` (hospital 1) o `?h=2` (hospital 2). En un computador, achica la ventana o usa la vista de teléfono del navegador.

## Qué muestra

Una página para el teléfono de alguien del jurado. Esa persona hace de atacante: ve el issue que plantó, pulsa «Empezar a escuchar» y le va llegando la clave de la ficha clínica de a cuatro caracteres, con una vibración por pedazo. Cuando la tiene completa pulsa «Usar la clave». En el hospital 1 entra y ve una ficha; en el hospital 2 recibe 401 y recién ahí se entera de que la clave había cambiado en la llamada 24, cuando tenía 12 de 40 caracteres.

La página no dice cuál hospital tiene Alicanto hasta el cobro: el atacante tampoco lo sabría. La idea es entregar dos teléfonos (o dos códigos QR) a dos personas del jurado y que cobren a la vez.

## Los primeros 10 segundos

«Hoy el atacante eres tú», el texto escondido del issue y un botón grande. Quien la tiene en la mano entiende que le van a mandar una clave robada, sin que nadie le explique el proyecto.

Frase sugerida para quien presenta: «Ustedes dos son el atacante. Tienen la misma instrucción plantada en dos hospitales. Cuando tengan la clave completa, úsenla.»

## Qué criterio empuja

- **Impacto (20):** el jurado no mira un robo, lo hace. La diferencia entre los dos hospitales le pasa a esa persona en la mano.
- **Originalidad (15):** el resultado se descubre al cobrar, igual que le pasaría a un atacante real, en vez de mostrarse en un gráfico.
- **Ejecución (20):** es una página de una sola tarea, pensada para teléfono, con botones grandes.

## Qué es real y qué es maqueta

- **Real (sale de ejecutar el código del repositorio):** la página lee las mismas grabaciones de `demo/run_split.py` que usa la demo oficial y no calcula nada por su cuenta.
  - Hospital 1: `demo/viz/fixtures/real_left.jsonl` (sin protección). Hospital 2: `real_right.jsonl` (con Alicanto).
  - El texto del issue es la salida de la llamada 2 de la grabación.
  - Cada fragmento es el argumento `d=` de una llamada a `attacker.test` que el proxy dejó pasar, con su número de llamada.
  - El 200 y el 401 son el resultado del cobro grabado del servidor del atacante.
  - «Llamada 24» es la del evento `rotation`; «12 de 40 caracteres» son los fragmentos que habían salido hasta esa llamada.
- **Maqueta:**
  - **La ficha clínica** es un texto de ejemplo: la API del banco de pruebas responde solo `{"ok": true}`. La tarjeta lo dice en pantalla.
  - **La línea `curl`** es una forma de mostrar el cobro; la clave va abreviada.
  - **El ritmo:** los fragmentos llegan uno cada 1,1 segundos y no se muestran las llamadas normales del medio. En la grabación hay 8 llamadas entre fragmento y fragmento.
- **No está sincronizada con la pantalla del escenario:** cada teléfono reproduce la grabación por su cuenta desde que se pulsa el botón.

## Qué falta y cuánto cuesta

- **Que un teléfono pueda abrirla.** Hoy se sirve en local. Dos caminos:
  - Publicarla en el sitio (llevarla a `demo/viz/` y redesplegar), si el líder la elige. Media hora. No depende del wifi del lugar más que para cargar la página una vez.
  - Servirla desde el computador del pitch a la red local (`python -m http.server 8300 --bind 0.0.0.0 --directory demo` y abrir `http://<ip-del-computador>:8300/…`). Depende de que el wifi del evento deje verse a los equipos entre sí.
- **Dos códigos QR** (uno por hospital), impresos o en una lámina, cuando se sepa la dirección final. Media hora.
- **Sincronizarla con el escenario**, para que los teléfonos y la pantalla grande avancen juntos. Necesita un servidor que reparta el estado: 3 horas o más, y agrega riesgo. Sin eso funciona igual, cada teléfono a su ritmo.
- **Ensayo:** dura unos 15 segundos desde el botón hasta la clave completa. Hay que decidir en qué momento del pitch se entregan los teléfonos.

## Riesgos

- **Red:** si se sirve por la red local y el wifi falla, no carga. Respaldo: dos teléfonos del equipo con la página ya abierta, que se entregan en la mano.
- **Tiempo:** pasar teléfonos consume segundos del pitch de 3 minutos. Calza mejor en una ronda en mesa que en el escenario.
- **Que alguien cobre antes de tiempo:** el botón no se activa hasta tener la clave completa.
- **La vibración** solo funciona en Android; en iPhone no vibra y lo demás es igual.
- **Si las grabaciones se regeneran** y cambian, `test_atacante.py` lo avisa.

Tests: `python -m pytest demo/alternativas/02-juez-atacante-juanpedro -q` (con Playwright; viewport de 390×844).
