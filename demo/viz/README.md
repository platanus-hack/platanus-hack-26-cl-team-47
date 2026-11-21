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

## Pantalla dividida (15b)

El mismo ataque en dos paneles sincronizados: «Sin protección» y «Con el medidor».

```
python -m http.server 8200 --directory demo/viz
```

`http://127.0.0.1:8200/split.html?left=fixtures/split_left.jsonl&right=fixtures/split_right.jsonl`
(`&t=end` salta al final).

- Un solo juego de controles mueve los dos paneles al mismo `t`. Las curvas de
  bits comparten escala para que se puedan comparar.
- Al llegar al final, cada panel muestra el intento del atacante: el último
  evento `source="attacker"`, `kind="received"` con `data.status` (200 en rojo,
  401 en verde, o «Sin intento del atacante»), y la fracción filtrada final de
  cada secreto.
- Cada `rotation` es una línea vertical en la curva y una fila destacada en la lista.
- `split.js` reutiliza `buildFrames` de `app.js` (carga ambos con `<script>`) y
  expone `finalStatus(events)` → `200`, `401` o `null`.

Los registros de ejemplo los genera `python demo/viz/make_split_fixture.py`
(determinista): 60 llamadas con un fragmento de 4 caracteres cada 8 hacia
`attacker.test`. Son sintéticos: no son resultados del detector.

Para usar registros reales, pasa la misma sesión por el arnés con dos
funciones de decisión y agrega el evento del atacante:

```
python -m eval.replay --sessions S --decide proxy.decide:allow_all --out izq.jsonl
python -m eval.replay --sessions S --decide <medidor>:<fabrica>   --out der.jsonl
```
