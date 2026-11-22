# Informe final y explicación técnica, en LaTeX

`informe.pdf` es el informe final del equipo (`docs/INFORME_FINAL.md`) con una explicación técnica completa: cómo funciona cada pieza, cómo se midió y qué resultado dio, con las fórmulas y los parámetros tal como están en el código.

Lo preparó el agente del líder con lo que está en el repositorio. Una persona del equipo lo revisa antes de entregarlo.

## Qué trae

| Parte | Contenido |
|---|---|
| I. El informe | La copia de `docs/INFORME_FINAL.md`, sin cambiarle cifras ni salvedades |
| II. Cómo funciona por dentro | Planteamiento y notación, arquitectura, contador de bits, grafos, evidencia de comportamiento, regla de decisión, cuenta compartida, banco de pruebas e integraciones |
| III. Cómo se midió | Datos, protocolo de los equipos rojo, azul y morado, resultados por familia, mediciones posteriores, demos y límites |
| IV. Apéndices | Parámetros, el modelo ajustado, la tabla completa de fragmentos cortos, formatos de archivo, mapa del repositorio, cómo repetir cada cifra y referencias |

## Cómo compilar

Desde esta carpeta, con cualquier TeX Live reciente:

```
pdflatex informe && pdflatex informe && pdflatex informe
```

También sirve `latexmk -pdf informe`. En Overleaf: subir la carpeta completa (con `datos/` y `figuras/`), dejar `informe.tex` como documento principal y usar pdfLaTeX, que es el compilador por defecto. No necesita `shell-escape` ni conexión.

## De dónde salen las cifras

Las tablas y figuras con datos están en `datos/` y no se escriben a mano. Las genera `hacer_datos.py` desde `results/`, `models/`, `redteam/` y las corridas grabadas de la demo.

```
python docs/informe/hacer_datos.py            # reescribe datos/ (unos 15 segundos)
python docs/informe/hacer_datos.py --check    # regenera en memoria y compara con lo guardado
python docs/informe/comprobar.py              # cifras de la prosa, reglas de redacción y LaTeX
```

Los tres se corren desde la raíz del repositorio, con las dependencias de `requirements.txt`.

- **`hacer_datos.py`** vuelve a correr el detector congelado sobre el set de prueba con las marcas del proxy, por el mismo camino de código que `python -m eval.final.proxy_flags`, guardando además el detalle llamada a llamada (evidencia, regla de cada rotación, tiempo por decisión). Comprueba que reproduce los totales publicados: 120 de 180, cero bloqueos y 5,46 rotaciones por cada 1.000 llamadas normales. No ajusta nada.
- **`comprobar.py`** revisa que las cifras escritas en el texto sean las de `datos/cifras.json`, que «180 de 180» no aparezca sin decir que es con las marcas de las grabaciones, y que el LaTeX no traiga lo que rompe pdfLaTeX.
- **La latencia** (`datos/latencia.tex`) se mide en cada corrida y cambia de una máquina a otra: `--check` no la compara.

## Archivos

| Archivo | Qué es |
|---|---|
| `informe.tex` | Documento principal: solo la estructura |
| `preambulo.tex` | Paquetes, tipografía, colores y macros |
| `secciones/` | El texto, un archivo por sección |
| `figuras/` | Figuras dibujadas a mano en TikZ y el logo de la portada |
| `datos/` | Tablas y figuras generadas, y `cifras.json` con todas las cifras |
| `hacer_datos.py`, `comprobar.py` | Los dos scripts de arriba |

## Lo que este documento agrega a lo que ya estaba en el repositorio

Al escribirlo se midió el detalle por familia que `results/proxy_flags/` no guarda, y aparecieron dos cosas que no estaban dichas en otro lado. Las dos están en el texto, con sus datos:

- **La configuración congelada no está en la frontera de Pareto de validación.** Con `lambda_rot` 0,1 hubo una rotación de más en validación; 144 combinaciones con las mismas cifras no tuvieron ninguna. El criterio de elección no mira las rotaciones una vez que están bajo la meta y, entre empatadas, se queda con la primera de la grilla (sección «El ajuste y la búsqueda»).
- **Cuatro de las 39 rotaciones de más del set de prueba son coincidencias de cuatro caracteres por azar** con otra clave del mismo archivo, que con el umbral del 10 % bastan para rotar (sección «El costo en el tráfico normal»).

Nada se cambió ni se volvió a medir sobre el set de prueba con otra configuración: sería ajustar mirando la prueba.
