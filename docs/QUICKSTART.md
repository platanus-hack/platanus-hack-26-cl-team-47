# Guía de inicio: Alicanto en tu agente de código

Alicanto es un servidor MCP. El agente le pide a Alicanto leer archivos, hacer peticiones HTTP, usar git o comentar en GitHub, y en cada llamada Alicanto mide cuántos bits de cada clave ya salieron; antes de que la fuga se complete, rota la clave en el gestor de secretos. Estos pasos se probaron tal cual (proyecto propio, manifiesto mínimo, dos agentes con la misma cuenta).

## 1. Requisitos

Python 3.11 o superior, y este repositorio clonado:

```bash
pip install -r requirements.txt
```

## 2. El manifiesto de secretos

Un archivo JSON con las claves que Alicanto protege. Necesita conocer sus **valores** porque mide coincidencias contra ellos: cuántos caracteres de cada clave ya aparecieron en lo que sale, en claro o codificados. El manifiesto nunca sale del proceso y nunca se escribe en los registros ni en la cuenta compartida.

```json
{
  "secrets": [
    {
      "secret_id": "PAGOS",
      "key": "PAGOS_API_KEY",
      "value": "<valor actual de la clave>",
      "files": [".env"],
      "allowed_hosts": ["api.pagos.example"]
    }
  ]
}
```

- `files`: dónde vive la clave dentro del repositorio del agente (leer ese archivo cuenta como exponerla).
- `allowed_hosts`: el destino legítimo de la clave; enviarla ahí no es una fuga.
- El gestor de secretos de este repositorio (`services/vault`) es el que rota; en producción va el tuyo, detrás de la misma interfaz (`POST /v1/secrets/{id}/rotate`, `GET /v1/secrets/{id}`).

## 3. Conectarlo al agente

En la configuración MCP del agente (por ejemplo `.mcp.json` en la raíz de tu proyecto):

```json
{
  "mcpServers": {
    "alicanto": {
      "command": "python",
      "args": ["-m", "proxy.server"],
      "env": {
        "PYTHONPATH": "/ruta/a/alicanto",
        "AGENT_WORKSPACE": "/ruta/al/repo",
        "SECRETS_MANIFEST": "/ruta/a/secretos.json",
        "PROXY_MODE": "live",
        "LEDGER_PATH": "/ruta/compartida/ledger.json"
      }
    }
  }
}
```

- `PYTHONPATH`: dónde clonaste este repositorio; así el servidor arranca desde cualquier carpeta.
- `AGENT_WORKSPACE`: el repositorio en el que trabaja el agente.
- `PROXY_MODE=live`: el detector decide y rota. Sin esta variable el proxy deja pasar todo (sirve para comparar).
- `PROXY_CONFIG=frozen` (opcional): el detector usa la configuración evaluada (`models/search/frozen.json` y su modelo, los de `results/test/`). Sin esta variable usa los parámetros por defecto, que deciden solo con el contador de bits.
- `LEDGER_PATH`: la **cuenta compartida**. Todos los agentes que apunten al mismo archivo suman en la misma cuenta por clave, y la cuenta sobrevive entre sesiones. Sin esta variable, cada proceso lleva su propia cuenta.

El servidor se anuncia como `alicanto` y expone seis herramientas: `read_file`, `list_dir`, `http_request`, `git`, `github_issue` y `github_comment`.

## 4. Probarlo con el banco local

En otra terminal, desde este repositorio, levanta el gestor de secretos, la API protegida y el servidor del atacante (todo local, `.test`):

```bash
python -m services.stack
```

Para ver el ataque completo sin un agente, con dos resultados (200 sin protección, 401 con Alicanto):

```bash
python -m services.scenarios goteo --out logs/goteo
```

Los registros quedan en `logs/`: `proxy.jsonl` (cada llamada y su decisión), `agent.jsonl` (lo que hizo el agente) y `attacker.jsonl` (lo que de verdad le llegó al atacante).

## Límites, con honestidad

- **El agente debe tener solo estas herramientas.** Si conserva su terminal o su lectura de archivos propia, se salta el proxy y Alicanto no ve nada. En agentes de código, desactiva sus herramientas integradas o córrelos sin ellas.
- **La cuenta compartida es un archivo local.** Sirve para varios agentes en la misma máquina (con un cerrojo de archivo); no coordina varias máquinas.
- **Si el cerrojo o el gestor no responden, falla cerrado:** bloquea las salidas hasta poder decidir con la cuenta.
- **Es una cota inferior:** una codificación que el motor no sabe leer no se ve por contenido; ahí actúan la evidencia de comportamiento y la rotación periódica. Cómo leer los resultados de la evaluación: `results/test/LECTURA.md`.

## Como hook de Claude Code

Si prefieres no cambiar las herramientas del agente, Alicanto también corre como hook `PreToolUse` de Claude Code: cuenta los bits que salen por `Bash`, `WebFetch` y `Read`, rota la clave en el gestor y, si no puede rotar, niega la llamada. Instalación en tres pasos: [integrations/claude_code/README.md](../integrations/claude_code/README.md).

Límite: ve lo que el modelo escribe en los comandos, no lo que un comando hace por dentro. Probado en una sesión real de Claude Code: corre en cada llamada, permite sin fricción y niega con el motivo; el contador de bits con un modelo real no quedó probado, porque el modelo se negó por su cuenta a enviar los trozos de la clave.
