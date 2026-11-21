# Cuentagotas · team-47 · Platanus Hack 26: Santiago

<img src="./project-logo.png" alt="Logotipo de Cuentagotas" width="200" />

Track: 🛡️ AI Security

**Tu agente de IA puede regalar tus claves de a cuatro letras. Cuentagotas cuenta cada gota y cambia la cerradura antes de que la llave esté completa.**

## Equipo

- Tomas Erdmannsdorffer Muñoz ([@terdmannsdorffer](https://github.com/terdmannsdorffer))
- José Carlos Basulto ([@jcbasulto](https://github.com/jcbasulto))
- Juan Pedro Lira ([@jplira2](https://github.com/jplira2))
- Victoria Guerriero ([@VictoriaGuerriero](https://github.com/VictoriaGuerriero))
- Matías Morgado ([@matix3000](https://github.com/matix3000))

## Qué es

Un proxy entre un agente de IA y sus herramientas. En cada llamada mide cuántos bits de cada clave ya salieron hacia afuera, aunque salgan de a pocos caracteres o codificados, y rota la clave en el gestor de secretos antes de que la fuga se complete. No modifica el agente y no usa un LLM para decidir.

La descripción completa está en [project-description.md](project-description.md).

## Verlo funcionar

Requiere Python 3.11 o superior.

```bash
pip install -r contracts/requirements.txt -r engine/requirements.txt -r proxy/requirements.txt \
            -r services/requirements.txt -r eval/requirements.txt -r demo/requirements.txt
```

**La demo en el navegador** (sitio estático, sin instalar nada más):

```bash
python -m http.server 8200 --directory demo/viz
```

- `http://127.0.0.1:8200/home.html`: portada.
- `http://127.0.0.1:8200/split.html`: el mismo ataque dos veces. Sin protección el atacante arma la clave y recibe 200; con Cuentagotas la clave rota y recibe 401.
- `http://127.0.0.1:8200/split.html?demo=enjambre`: cinco agentes se reparten la fuga. Con una cuenta por agente nadie la ve; con la cuenta global, rota.

**El ataque en vivo**, con el gestor de secretos, la API protegida, el servidor del atacante y el proxy reales (todo local):

```bash
python -m services.scenarios goteo --out logs/goteo
```

**Regenerar la demo desde cero:**

```bash
python demo/run_split.py --out-dir demo/out            # goteo
python demo/run_split.py --swarm --out-dir demo/out    # enjambre
```

**Tests:**

```bash
python -m pytest -q
```

## Cómo está organizado

| Carpeta | Qué hay |
|---|---|
| `contracts/` | Los tipos compartidos: `ToolCall`, `Decision` y el registro de eventos |
| `proxy/` | Proxy MCP y sus seis herramientas |
| `engine/` | Motor de bits, grafos, evidencia acumulada, decisión y la cuenta global del enjambre |
| `services/` | Gestor de secretos con rotación, API protegida, servidor del atacante, GitHub y web simulados |
| `redteam/` | Ataques de entrenamiento y validación, generados de forma determinista |
| `eval/` | Arnés de reproducción, líneas de base, búsqueda de umbrales y pruebas de hipótesis |
| `demo/` | Repositorio de demostración y visualización |
| `pitch/` | Láminas, guion y preguntas del jurado |
| `docker/` | Red aislada con todos los servicios, sin salida a internet |

## Reglas del banco de pruebas

Solo secretos sintéticos y servidores simulados con nombres `.test`. Las herramientas del agente no tienen salida a internet. El hospital de la demo, sus pacientes y sus claves son ficticios.

## Límites

- Se mide una cota inferior: lo que pasa por el proxy, en las codificaciones que el motor sabe leer.
- Rotar limita el daño; no impide que el agente lo intente.
- La cuenta compartida del enjambre cubre un solo proceso y se conserva entre sesiones; coordinar varias máquinas queda como trabajo futuro.
