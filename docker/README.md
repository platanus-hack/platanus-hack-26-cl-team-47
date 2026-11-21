# Red aislada del banco de pruebas

`docker compose` con gestor (`vault.test`), API protegida (`api.empresa.test`), servidor del atacante (`attacker.test`) y un contenedor para el proxy, en una red interna sin salida a internet (documento v4.0, sección 5.1, nivel 1). Todo corre con una sola imagen (`docker/Dockerfile`, `python:3.12-slim`).

## Levantar

Desde la raíz del repo:

```bash
docker compose -f docker/compose.yml up -d --build
docker compose -f docker/compose.yml ps
```

| Servicio | Alias en la red `banco` | Puerto en el host |
|---|---|---|
| `vault` | `vault.test:8101` | ninguno |
| `api` | `api.empresa.test:8102` | `127.0.0.1:8102` |
| `attacker` | `attacker.test:8103` | `127.0.0.1:8103` |
| `proxy` | (sin alias) | ninguno |

Dentro de los contenedores, `contracts/hosts.json` se reemplaza por `docker/hosts.docker.json` (volumen de solo lectura), que apunta a los alias. `contracts.load_hosts()` no acepta una ruta por variable de entorno, por eso el montaje.

Los registros quedan en el volumen `logs` (`LOG_DIR=/logs`):

```bash
docker compose -f docker/compose.yml exec proxy ls /logs
```

### Por qué `api` y `attacker` están en dos redes

Docker no publica puertos de un contenedor que solo está en una red `internal: true`. Para poder mirar la API y el atacante desde el navegador de la demo, esos dos servicios están además en la red `publica`, y solo publican en `127.0.0.1`. El **proxy**, donde corren las herramientas del agente, y el **gestor** están solo en `banco`: no tienen ninguna ruta a internet.

## Comprobar que no hay salida a internet

```bash
# Debe fallar (sin red externa desde el proxy):
docker compose -f docker/compose.yml exec proxy python -c "import urllib.request; urllib.request.urlopen('https://example.com', timeout=5)"
# Debe responder (los servicios del banco sí se ven por sus alias):
docker compose -f docker/compose.yml exec proxy python -c "import urllib.request; print(urllib.request.urlopen('http://vault.test:8101/v1/secrets/SECRET_1').status)"
```

## Probar el 401/200 de la API contra el gestor

```bash
docker compose -f docker/compose.yml exec proxy python - <<'EOF'
import json, urllib.request, urllib.error
v = json.load(urllib.request.urlopen("http://vault.test:8101/v1/secrets/SECRET_1"))["value"]
def status(key):
    req = urllib.request.Request("http://api.empresa.test:8102/v1/data", headers={"Authorization": f"Bearer {key}"})
    try:
        return urllib.request.urlopen(req).status
    except urllib.error.HTTPError as e:
        return e.code
print("clave vigente:", status(v))
urllib.request.urlopen(urllib.request.Request("http://vault.test:8101/v1/secrets/SECRET_1/rotate", method="POST"))
print("clave vieja tras rotar:", status(v))
EOF
```

Esperado: `200` y después `401`.

## Correr el escenario con el proxy en vivo

El proxy corre dentro del contenedor (sin salida a internet) y habla MCP por stdio. El agente corre en el host, porque necesita llegar a su modelo:

```bash
python -m proxy.agent --task "<tarea>" \
  --mcp "docker compose -f docker/compose.yml exec -T proxy python -m proxy.server"
```

El contenedor `proxy` ya tiene `PROXY_MODE=live` y `AGENT_WORKSPACE=demo/repo`. Para grabar la sesión, agrega `-e PROXY_RECORD=1` después de `exec -T`.

## Bajar todo

```bash
docker compose -f docker/compose.yml down        # conserva el volumen de registros
docker compose -f docker/compose.yml down -v     # borra también los registros
```

## Tests

```bash
pip install -r docker/requirements.txt
python -m pytest docker/tests -q
```

Validan `compose.yml`, `hosts.docker.json` y `.dockerignore` sin necesitar Docker. Si `docker` está instalado, también corren `docker compose config`.
