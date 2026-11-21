# demo/viz: visor del registro de eventos

Página estática (HTML, CSS y JS planos, d3 v7 local) que reproduce un registro
de eventos de `contracts`: llamadas, decisiones, bits filtrados por secreto y
evidencia S. Es la mitad de la pantalla dividida de la demo.

## Abrir

```
python -m http.server 8200 --directory demo/viz
```

Luego `http://127.0.0.1:8200/?log=fixtures/sample.jsonl`, o el botón
«Abrir registro…» para elegir un `.jsonl` local (por ejemplo la salida de
`python -m eval.replay ... --out x.jsonl`). `&t=20` salta a la llamada 20.

Teclas: espacio reproduce o pausa; ← y → avanzan un paso.

## Entrada

Un `Event` por línea. El visor usa `tool_call` (data = ToolCall), `decision`
(data = Decision, unida por `call_id`) y `rotation` (data = `{secret_id, version}`).
Ignora cualquier otro `kind`.

`app.js` expone `buildFrames(events)` (pura): lista ordenada por `t` de
`{t, call, decision, rotations}`.

## Fixture

`python demo/viz/make_fixture.py` regenera `fixtures/sample.jsonl`
(determinista): 40 llamadas, goteo de `SECRET_1` y `SECRET_2`, dos rotaciones
y las cuatro acciones. Es sintético: no son resultados del detector.

## Tests

`python -m pytest demo/viz/tests -q`
