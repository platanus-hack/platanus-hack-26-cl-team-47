# redteam — plantillas de ataque de entrenamiento (tarea 5a)

Generador determinista de sesiones de ataque y de casos benignos difíciles en el
contrato `ToolCall`. Solo datos sintéticos: hosts `.test`, claves al azar. No ejecuta
nada contra servicios ni abre `engine/`.

## Comando

```
python -m redteam.generate --split val --n 80 --seed 1 --out redteam/val
```

## Familias

- **A1** exfiltración directa: un único envío con el secreto completo.
- **A2** crescendo: 4 a 6 envíos de tamaño creciente hasta completar el secreto.
- **A3** goteo en claro: 5 a 10 envíos de 4 caracteres, separados por decenas de llamadas.
- **A4** goteo codificado: base64, hex, URL, ROT13, invertido o separado.
- **A5′** sustitución propia de la sesión (no decodificable sin la tabla).
- **B1** deploy legítimo: lee `.env` y manda la clave a su destino permitido (benigno).
- **B2** depurar: lee `.env` y `config/secrets.yaml`, sin sumidero (benigno).

## Cantidades (`--n 80`)

| Familia | Sesiones |
|---|---|
| A1 | 10 |
| A2 | 15 |
| A3 | 20 |
| A4 | 25 |
| A5′ | 10 |
| B1 | 10 |
| B2 | 10 |
| **Total ataque** | 80 |
| **Total benigno difícil** | 20 |

## Salidas

- `sessions/<session_id>.jsonl`: un `ToolCall` por línea.
- `labels.jsonl`: una línea por envío de ataque.
- `secrets.jsonl`: el secreto sintético de cada sesión.
- `manifest.json`: semilla, reparto y sha256 de cada archivo.
