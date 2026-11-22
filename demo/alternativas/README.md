# Alternativas de demo

Carpeta para probar ideas de demo en paralelo y compararlas entre nosotros. Cualquier persona o agente del equipo puede subir una. **El domingo 22 el líder eligió la alternativa 03** (`03-enjambre-juanpedro/`): es la demo del pitch y la que publica https://alicanto.vercel.app, con su tablero de pruebas. `demo/viz/` queda en el repositorio como la demo anterior. Las demás alternativas son exploraciones y no se despliegan.

## Cómo subir una alternativa

1. Crea tu propia subcarpeta: `demo/alternativas/<NN>-<nombre-corto>-<quien>/`. `NN` es el siguiente número libre de dos cifras; `quien` es tu nombre o tu login. Por ejemplo: `03-informe-en-vivo-matias/`.
2. Copia `00-plantilla/README.md` a tu carpeta y complétalo. Sin ese archivo la alternativa no se revisa.
3. Trabaja **solo dentro de tu subcarpeta**. No edites las de otros, ni `demo/viz/`, ni este archivo. Si necesitas algo de `demo/viz/` (estilos, grabaciones, scripts), cópialo a tu carpeta o enlázalo con una ruta relativa; no lo cambies en su lugar.
4. Súbela en un PR que toque únicamente tu subcarpeta, con el título `alternativa NN: <nombre>`. No necesita issue ni tarea. El orquestador lo mergea sin más revisión que comprobar que solo toca tu carpeta y que la suite sigue en verde.
5. Avisa en el board en una línea: qué muestra y cómo abrirla.

## Cómo verlas

Desde la raíz del repositorio:

```
python -m http.server 8300 --directory demo
```

y abre `http://127.0.0.1:8300/alternativas/`. El servidor muestra la lista de carpetas; cada una dice en su `README.md` qué archivo abrir. Se sirve la carpeta `demo` completa para que las rutas relativas hacia `../../viz/` funcionen.

## Reglas

- **Solo datos sintéticos.** Las mismas reglas del banco de pruebas: claves inventadas, servidores locales con nombres `.test`, nada sale a internet.
- **Nada inventado.** Si una alternativa muestra una cifra, el README dice de qué corrida o archivo sale. Una maqueta con números de ejemplo lo dice en grande en la propia pantalla.
- **Qué es real y qué es maqueta**, dicho en el README de cada alternativa.
- **Liviana.** Sin videos ni binarios de más de 2 MB; si hace falta un video, déjalo fuera del repositorio y pon dónde está.
- **Autocontenida.** Debe abrirse con el comando de arriba, sin instalar nada más. Si necesita un paso extra, va en su README.
- No se borra ninguna alternativa: las que no se elijan quedan como registro.

## Cómo se elige

El líder las mira y decide. Para compararlas con el mismo criterio, cada README responde las mismas preguntas (ver la plantilla): qué ve el jurado en los primeros 10 segundos, qué criterio de la rúbrica empuja y cuánto falta para que esté lista.
