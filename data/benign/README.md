# Sesiones benignas propias

Generadas con el proxy real (`allow_all`) sobre `demo/repo`, sin LLM. Fondo benigno para estimar el
modelo y medir falsas alarmas (documento v4.0, sección 6.1). Un `ToolCall` por línea con su salida
real y `label: "benign"`; se cargan con `eval.replay.core.load_session`.

```
python -m proxy.benign --n 120 --seed 0 --out data/benign/sessions
```

- Semilla: 0
- Sesiones: 120 (entre 25 y 60 llamadas cada una)
- Llamadas: 4885
- Llamadas sumidero (`is_sink`): 41
- Carpeta: `data/benign/sessions`, archivos `benign-<semilla>-<índice>.jsonl`

| Tipo de guion | Sesiones |
|---|---|
| 1. Arreglar un bug (listar, leer código y tests, git status/diff/log) | 24 |
| 2. Leer documentación (docs/ y README.md) | 24 |
| 3. Revisar configuración no secreta (config/settings.yaml, pyproject.toml) | 24 |
| 4. Depurar con .env o config/secrets.yaml en medio de un arreglo (B2) | 24 |
| 5. Deploy legítimo: SECRET_1 como Bearer hacia api.empresa.test (B1) | 12 |
| 6. Trabajo con SHAs de git y UUIDs en argumentos y queries (B3) | 12 |

Notas:
- El gestor y la API protegida corren en proceso; nada sale a internet. Los secretos son los
  sintéticos del manifiesto y solo viajan a sus `allowed_hosts` (tipo 5).
- Cada corrida usa una copia temporal de `demo/repo` con git inicializado y commits deterministas,
  porque `demo/repo` no es un repositorio propio y el proxy aísla git del repo del equipo. Los recursos
  se graban relativos al workspace, iguales a los de `demo/repo`.
- Comprobación: `python -m eval.replay --sessions data/benign/sessions --decide engine.detector:make_decide --out /tmp/b.jsonl`
