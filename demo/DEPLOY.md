# Desplegar la demo como sitio estático

La demo es un sitio estático: `demo/viz/` (HTML, CSS, JS y d3 local, sin paso de
compilación). La portada es `home.html`; sin parámetros, `split.html` abre la
demo real versionada (`fixtures/real_*`).

## Probar en local

```
python -m http.server 8200 --directory demo/viz
```

- `http://127.0.0.1:8200/home.html`: portada.
- `http://127.0.0.1:8200/split.html`: pantalla dividida con la corrida real y el grafo.
- `http://127.0.0.1:8200/index.html`: un registro (el panel derecho).

Todas las rutas son relativas: funciona igual en la raíz de un dominio o en una subcarpeta.

## Desplegar en Vercel (lo hace el líder)

Vercel no se conecta a repos de la organización (`AGENTS.md`, sección 5), así
que se despliega desde el repo espejo **`jplira2/platanus-hack-26-cl-team-47`**.

1. Asegúrate de que el espejo tenga lo último de `main` (si `origin` empuja a los
   dos repos, basta con `git push`).
2. En Vercel: *Add New → Project → Import Git Repository* y elige
   `jplira2/platanus-hack-26-cl-team-47`.
3. *Framework Preset*: **Other**. No cambies nada más: `vercel.json` en la raíz ya
   fija `outputDirectory: demo/viz`, sin comando de build ni de instalación, y
   redirige `/` a `/home.html`.
4. *Deploy*. Al terminar, abre la URL que da Vercel (algo como
   `https://<proyecto>.vercel.app`): debe mostrar la portada, y «Ver la demo»
   debe abrir la pantalla dividida con el 200 y el 401 al final.

(Esto era el plan. El despliegue quedó a mano por línea de comandos; ver «Cómo quedó desplegado» más abajo.)

## Después del despliegue

La URL pública va en el campo `deploy-url` de `platanus-hack-project.jsonc`
(archivo de la plantilla: lo edita una persona del equipo, no un agente), por ejemplo:

```
"deploy-url": "https://<proyecto>.vercel.app"
```

## Actualizar la corrida que se muestra

```
python demo/run_split.py --out-dir demo/out
cp demo/out/left.jsonl  demo/viz/fixtures/real_left.jsonl
cp demo/out/right.jsonl demo/viz/fixtures/real_right.jsonl
cp demo/out/graph.json  demo/viz/fixtures/real_graph.json
```

Los tests (`python -m pytest demo/tests demo/viz/tests -q`) comprueban que los
fixtures coinciden con una corrida nueva.

## Cómo quedó desplegado (sábado 21 de noviembre, 10:40)

- URL pública: https://alicanto.vercel.app. Es un dominio agregado al proyecto de Vercel, que internamente se sigue llamando `cuentagotas` (el primer nombre del producto), en el equipo `cuenta-gotas1` (plan Hobby), cuenta `jplira2`. La dirección anterior, `cuentagotas-gamma.vercel.app`, sigue funcionando y apunta al mismo sitio.
- Se despliega **a mano desde la línea de comandos**, no por la integración con GitHub:

```
npx vercel deploy --prod --yes --scope cuenta-gotas1
```

  desde la raíz del repo, en una máquina con la sesión de Vercel iniciada (`npx vercel login`). La carpeta `.vercel/` y el archivo `.env.local` que crea la herramienta son locales y están en `.gitignore`: no se versionan.
- **Por qué no la integración con GitHub:** se probó y Vercel bloqueó los despliegues con el motivo «no se pudo asociar el autor del commit a una cuenta de Vercel». En el plan Hobby, cada commit debe ser de un autor cuya cuenta de GitHub esté vinculada a Vercel, y aquí los commits son de cinco personas y de sus agentes. Con el repositorio conectado, además, tampoco funcionaba el despliegue manual; por eso se desconectó.
- Comprobación después de cada despliegue: `/`, `/home.html`, `/split.html`, `/split.html?demo=enjambre`, `/split.html?demo=elige`, `/report.html`, `/results.html` y `/pitch/index.html` responden 200 (la raíz redirige a la portada y `/pitch` a `/pitch/index.html`). En `/pitch/index.html`, el enlace «Demo» debe abrir `/split.html`.

## Las láminas en el sitio (tarea 15n)

`vercel.json` publica solo `demo/viz`, así que las láminas entran con un paso de build que copia
los tres archivos de `pitch/` al sitio, sin copiarlos dentro del repo:

```
"buildCommand": "mkdir -p demo/viz/pitch && cp pitch/index.html pitch/slides.js pitch/style.css demo/viz/pitch/"
```

- `demo/viz/pitch/` está en `.gitignore`: si corres el build en local, no lo versiones.
- Las láminas enlazan la demo con `../demo/viz/split.html`. En el sitio eso es `/demo/viz/split.html`,
  y la redirección `/demo/viz/:path*` → `/:path*` lo lleva a `/split.html`. En local, desde la raíz del
  repo (`python -m http.server 8200`), el mismo enlace funciona sin redirección.
- Si las láminas empiezan a usar otro archivo (una imagen, una fuente), agrégalo a la copia del
  `buildCommand` y al test `test_vercel_json_publica_las_laminas`.
- Abiertas con doble clic (`file://`), las láminas cambian sus enlaces a la demo por
  `https://alicanto.vercel.app/...`. La demo, abierta así, explica que necesita un servidor.

Para simularlo en local antes de desplegar:

```
rm -rf /tmp/sitio && cp -r demo/viz /tmp/sitio && mkdir -p /tmp/sitio/pitch
cp pitch/index.html pitch/slides.js pitch/style.css /tmp/sitio/pitch/
python -m http.server 8200 --directory /tmp/sitio   # abre http://127.0.0.1:8200/pitch/index.html
```
