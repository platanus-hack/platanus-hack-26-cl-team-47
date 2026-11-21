# contracts

Contratos congelados en la tarea 1a. Nadie los cambia sin avisar en el board y sin visto bueno del líder.

```python
from contracts import ToolCall, Decision, Event, write_event, read_events, load_hosts
```

| Modelo | Campos |
|---|---|
| `ToolCall` | `id, t (≥1), tool, args, output, resources, is_sink, untrusted, session_id, label (benign/attack/None)` |
| `Decision` | `action (allow/block/rotate+allow/rotate+block), S, R_plus, leak {secret_id: {bits, fraction∈[0,1]}}, path, reason, latency_ms`. `decision.allowed` es `True` si la acción termina en `allow`. |
| `Event` | `ts (epoch s), session_id, source (proxy/agent/attacker), kind, call_id, data` |

Los modelos rechazan campos extra. `kind` se valida contra `source`:

| source | kind |
|---|---|
| proxy | `tool_call` (data = ToolCall), `decision` (data = Decision), `rotation` (data = {secret_id, version}) |
| agent | `message`, `tool_use`, `tool_result` |
| attacker | `received` |

## Registro

`write_event(e)` agrega una línea JSON a `$LOG_DIR/<source>.jsonl` (por defecto `logs/`). `read_events(path)` devuelve `list[Event]`.

## Hosts

`contracts/hosts.json` (o `load_hosts()`): `vault.test` 8101, `api.empresa.test` 8102, `attacker.test` 8103, `github.test` 8104, `web.test` 8105, todos en `127.0.0.1`.

Ejemplos válidos en `contracts/examples/`. Tests: `python -m pytest contracts/tests -q`.
