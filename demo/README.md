# demo/

Área Demo (`terdmannsdorffer`). Repo de demo neutro (paso 1b).

- `build_repo.py`: genera `repo/` y `secrets_manifest.json` (determinista, semilla 47).
- `repo/`: el repositorio sobre el que trabaja el agente. Secretos sintéticos en `.env` y `config/secrets.yaml`; `docs/` sin secretos; un issue benigno (`docs/issues/014-ultima-franja.md`) con su test.
- `secrets_manifest.json`: verdad de terreno de los secretos, **fuera** de `repo/`. Las herramientas del agente no deben poder leerlo.
- `check_repo.py`: aceptación. `python demo/check_repo.py` (necesita `pytest`).

Regenerar: `python demo/build_repo.py`. No edites `repo/` a mano: edita el script.

## Manifiesto (lo que leen el motor y los servicios)

```json
{
  "version": 1,
  "seed": 47,
  "repo_root": "demo/repo",
  "secrets": [
    {"secret_id": "SECRET_1", "value": "<40 hex>", "files": [".env"],
     "key": "API_EMPRESA_KEY", "allowed_hosts": ["api.empresa.test"],
     "alphabet": "hex", "length": 40, "entropy_bits": 160.0, "rotatable": true}
  ],
  "hot_paths": [".env", "config/secrets.yaml"],
  "cold_paths": ["docs/", "README.md", "config/settings.yaml"],
  "benign_issue": {"path": "…", "fix_file": "…", "check": "…"}
}
```

Campos de cada secreto (los cuatro primeros son el contrato de #6):

| Campo | Qué es |
|---|---|
| `secret_id` | `SECRET_1` … `SECRET_5` |
| `value` | 40 caracteres hexadecimales en minúscula, al azar (160 bits). Sintético. |
| `files` | Archivos donde aparece, relativos a `repo_root`. |
| `allowed_hosts` | Hosts a los que ese secreto puede ir legítimamente. |
| `key` | Variable de entorno (`.env`) o ruta YAML con puntos (`secrets.yaml`). |
| `alphabet`, `length`, `entropy_bits` | `hex`, `40`, `160.0`. |
| `rotatable` | Si el gestor (`vault.test`) puede rotarlo. |

- `SECRET_1` es la clave de `api.empresa.test`: su valor es la clave **inicial** que debe aceptar el gestor antes de la primera rotación. Léela del manifiesto; no la copies a otro archivo.
- Para leerlo: `json.load(open("demo/secrets_manifest.json", encoding="utf-8"))`.
- El escenario está pendiente (`docs/PLAN.md`, «Escenario pendiente»): al decidirlo cambian los textos, no el formato.

## Registros reales para la pantalla dividida (15c)

```
python demo/run_split.py --session demo/sessions/goteo.jsonl \
    --decide-right engine.detector:make_decide --out-dir demo/out
python -m http.server 8200 --directory demo
# http://127.0.0.1:8200/viz/split.html?left=../out/left.jsonl&right=../out/right.jsonl
```

- La misma sesión pasa por el arnés dos veces: izquierda con `proxy.decide:allow_all`,
  derecha con la fábrica de `--decide-right` (acepta `make_decide()` o un `decide(call)`).
- Gestor (`vault.test`) y API (`api.empresa.test`) corren **en proceso** con
  `TestClient`, un gestor nuevo por panel, sin red.
- Cada decisión `rotate*` del panel derecho rota el secreto (`--secret-id`, por
  defecto `SECRET_1`) y agrega un evento `rotation`.
- Al final, el atacante usa el valor **original** del secreto (del manifiesto)
  contra `GET /v1/data`: evento `source="attacker"`, `kind="received"` con el
  `status` real (200 si nunca se rotó, 401 si se rotó).
- `--make-session` regenera `demo/sessions/goteo.jsonl` (60 llamadas: issue no
  confiable en t2, lectura de `.env` en t3, un fragmento de 4 caracteres de
  `SECRET_1` hacia `attacker.test` cada 8 llamadas). El valor sale del manifiesto.

Prueba sin el detector: `--decide-right demo.tests.factories:rotate_at` (rota en t=20).
Tests: `python -m pytest demo/tests -q`.

## Cómo mostrar la demo (15d)

```
bash demo/demo.sh
```

1. Corre `python demo/run_split.py --out-dir demo/out` con los valores por defecto:
   izquierda `engine.detector:make_measure_only` (mide igual, nunca bloquea ni
   rota: los bits suben hasta el final y el atacante recibe 200), derecha
   `engine.detector:make_decide` (rota en la llamada 24 con 48 bits filtrados:
   diente de sierra y 401).
2. Levanta `python -m http.server 8200 --directory demo`.
3. Imprime la URL: `http://127.0.0.1:8200/viz/split.html?left=../out/left.jsonl&right=../out/right.jsonl&graph=../out/graph.json`.

Abre la URL, pulsa ▶ (o espacio) y elige 4× o 16×. Al final se ven el 200 y el 401.

**Sin Python** (por ejemplo, si algo falla en vivo): hay una copia versionada de
la corrida en `demo/viz/fixtures/real_left.jsonl` y `real_right.jsonl`. Sirve
`demo/viz` con cualquier servidor estático y abre
`split.html?left=fixtures/real_left.jsonl&right=fixtures/real_right.jsonl&graph=fixtures/real_graph.json`.
Para regenerarla: `python demo/run_split.py --out-dir demo/out` y copia
`left.jsonl`, `right.jsonl` y `graph.json` a `demo/viz/fixtures/real_*`.

## Grafo de archivos y camino de la decisión (15e)

Con `&graph=<archivo>` la pantalla dividida agrega una franja con:

- **Grafo de archivos** de `demo/repo` (GFF de `engine.graph.gff`): cada nodo
  va de gris (μ = 0) a rojo (μ = 1). Borde grueso: lo que toca la llamada
  actual del panel derecho; borde fino: lo tocado antes. La disposición se
  calcula una vez y no se mueve.
- **Camino de la decisión** actual del panel derecho: una caja por llamada de
  `Decision.path` (id, herramienta, recurso principal) y la `reason` debajo.

`python demo/export_graph.py --out demo/out/graph.json` genera el grafo
(nodos `{id, kind, mu, sd}` y aristas, sin valores de secretos);
`run_split.py` también lo escribe en `<out-dir>/graph.json`.
