# Alicanto como hook de Claude Code

El contador de bits de Alicanto revisa cada llamada a `Bash`, `WebFetch` y `Read` de una sesión de Claude Code antes de que se ejecute. Lleva la cuenta de cuántos bits de cada clave ya salieron hacia destinos no confiables y la rota en el gestor de secretos antes de que salga lo suficiente para reconstruirla. Si no puede rotar, niega la llamada.

## Instalación en tres pasos

1. **Dependencias.** En la copia de este repositorio:

   ```bash
   pip install -r requirements.txt
   ```

2. **Manifiesto de secretos.** Un JSON con las claves que se cuentan, en el formato de `demo/secrets_manifest.json`:

   ```json
   {"secrets": [{"secret_id": "API_KEY", "value": "…", "files": [".env"], "allowed_hosts": ["api.empresa.test"]}]}
   ```

   - `files`: rutas relativas al proyecto donde vive la clave.
   - `allowed_hosts`: destinos legítimos. Lo que va a esos hosts no cuenta como fuga.
   - Guarda el manifiesto fuera del proyecto y fuera de git.

3. **Hook.** Copia el bloque `hooks` de [settings.example.json](settings.example.json) en `.claude/settings.json` del proyecto, o en `~/.claude/settings.json`. Cambia las dos rutas.
   - Con `VAULT_URL=http://…` delante del comando, el hook rota en el gestor (`POST /v1/secrets/{id}/rotate`, la API de `services/vault`).
   - Con `ALICANTO_STATE_DIR=…` eliges dónde guarda su estado. Por defecto es `<proyecto>/.alicanto`; agrégalo a `.gitignore`.

Para probarlo sin Claude Code:

```bash
python -m integrations.claude_code.simulate        # sesión inventada: Read de .env, 10 WebFetch con trozos, curl final
echo '{"session_id":"s","cwd":".","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"ls"}}' \
  | SECRETS_MANIFEST=demo/secrets_manifest.json ALICANTO_STATE_DIR=/tmp/alicanto python -m integrations.claude_code.hook
```

El segundo comando sale con código 0 y no imprime nada, lo que significa permitir.

## Qué decide

| Llamada | Se cuenta como | Sumidero |
|---|---|---|
| `Read` | lectura del archivo; el hook lo lee, hasta 200.000 caracteres | no; nunca se niega |
| `WebFetch` | `http_request` GET; la URL y el prompt son lo que sale | sí, no confiable |
| `Bash` con red (`https?://`, `curl`, `wget`, `nc`, `ssh`, `scp`, `git push`…) | `http_request` hacia la primera URL del comando | sí; confiable solo si el host está en `allowed_hosts` |
| `Bash` sin red | lectura de los archivos del manifiesto que nombre | no |

- **Regla directa.** Un `Bash` con red que nombra un archivo del manifiesto (por ejemplo `curl -d @.env …`) se niega siempre.
- **Contador de bits.** Todo lo demás pasa por el detector, con sus parámetros por defecto: rota al 30 % de la clave.
  - Si la rotación se hizo, la llamada pasa. Lo que ya salió es de la versión anterior.
  - Si no hay gestor o la rotación falla, se niega con «N bits de X ya salieron: rota la clave».
- **Fallas.** Si el hook falla por dentro, niega los sumideros y permite el resto.
- **Estado entre llamadas.** Claude Code lanza un proceso por llamada, así que nada queda en memoria.
  - La cuenta por clave va en `ALICANTO_STATE_DIR/ledger.json`, con el mismo cerrojo y la misma sincronización que `LEDGER_PATH` del proxy en vivo.
  - El estado de cada sesión va en `sesiones/`.
  - Un test comprueba que 15 llamadas en un proceso y en 15 procesos dan las mismas decisiones y los mismos bits.
- **Registro.** Cada llamada queda en `hook.jsonl`:
  - con la decisión, el motivo y los bits por clave;
  - sin valores de claves;
  - con los primeros 80 caracteres del comando, que se omiten si contienen un trozo de una clave.

## Límites

- **No se probó dentro de una sesión real de Claude Code.** Se probó con `simulate.py` y los tests, que le pasan al hook el JSON del formato documentado de los hooks `PreToolUse`.
- **Solo mira las tres herramientas.**
  - `Edit`, `Write`, las herramientas MCP y los subagentes pasan sin contar.
  - Un `Bash` que escribe un archivo y otro que lo envía después solo se ve si el segundo comando lleva la URL.
- **El Bash se mira por su texto.**
  - Un comando que arma la URL en una variable, o que usa un programa que no está en la lista (por ejemplo `python -c` con `urllib`), cuenta como local.
  - El hook no ve lo que el comando lee, solo los archivos del manifiesto que nombra.
- **Usa el contador de bits, no el modelo de evidencia de la evaluación.** Las cifras de `results/test/` son del detector congelado sobre trazas grabadas, no de este hook.
- **Sin `VAULT_URL` no rota:** al llegar al umbral niega los envíos hasta que alguien rote la clave y reinicie el estado (borrando `ledger.json`).
- **Latencia.** Cada llamada arranca Python y carga el detector: unos 0,7 s por llamada en un portátil con Windows.
- **El manifiesto lleva los valores de las claves en texto.** Protégelo como protegerías el `.env`.
