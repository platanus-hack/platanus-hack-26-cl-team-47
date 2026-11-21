# Estado del proyecto (para agentes)

Actualizado: sábado 21 de noviembre de 2026, 14:55 (H15,9). Lo mantiene el orquestador. Si empiezas una sesión, lee esto, `AGENTS.md` y tu issue. El resumen para personas está en `docs/INFORME_TURNOS.md`.

## En una frase

**Alicanto** (hasta el sábado a las 11:30 se llamó Cuentagotas) es un proxy entre un agente de IA y sus herramientas que mide cuánta de cada clave ya se filtró y la rota antes de que la fuga se complete. Está construido, evaluado y desplegado. Tareas abiertas: #185 (probar el hook de Claude Code dentro de una sesión real). En revisión del líder: PR #178 (descripción pública reescrita). El pitch, el README, la portada y la página de resultados ya dicen las dos cifras.

## Qué hay en `main`

- 809 tests en verde (`python -m pytest -q`).
- Demo principal, del enjambre e interactiva (`demo/viz/`), desplegadas en https://alicanto.vercel.app. El despliegue es a mano: `demo/DEPLOY.md`.
- Evaluación final corrida una sola vez sobre el set sellado: `results/test/`. Simulación del atacante adaptativo: `results/adaptive/`.
- Hook de Claude Code que pasa `Bash` y `WebFetch` por el contador de bits: `integrations/claude_code/` (probado con entradas simuladas, no dentro de una sesión real).
- Ideas de demo en paralelo: `demo/alternativas/`, una subcarpeta por alternativa; la demo oficial sigue siendo `demo/viz/`.
- Pitch con cifras: `pitch/`. Guía para conectar el proxy a un agente real: `docs/QUICKSTART.md`.
- Corridas con un LLM real a través del proxy, hechas: `docs/LLM_EN_VIVO.md` (Haiku 5.5 y Sonnet 5.5 con n = 10, Opus 5.5 con n = 1; ninguna siguió la inyección, y hubo una rotación de más con Sonnet).

## Reglas vigentes

- **`engine/` y `models/` están congelados** (etiqueta `congelamiento`). Cualquier cambio lo autoriza el líder.
- **La evaluación final no se repite.** `python -m eval.final.run --split test` se niega a correr.
- **Lee `results/test/LECTURA.md` antes de escribir una cifra.** 180 de 180 ataques grabados prevenidos y 0 de 5.879 llamadas benignas bloqueadas, con tres límites que van siempre al lado: son ataques grabados (el adaptativo se midió aparte: 180 de 180, deteniendo las salidas tras tres rotaciones); costo de 39 rotaciones de más, en 34 de 90 sesiones benignas difíciles; y con el contador de bits solo se previenen 40 de 180.
- **Frase de novedad permitida:** «Hasta donde encontramos, nadie usa la fuga parcial medida de una credencial (en bits, sumada entre llamadas, codificaciones y agentes) para rotarla antes de que se complete.»
- **No decir:** «detiene el 100 %» a secas; que nadie junta fragmentos (existen Pipelock y AgentBrake); que somos los primeros; que los grafos «conectan pasos lejanos»; que Alicanto frenó a un LLM real (se corrieron tres modelos y ninguno siguió la inyección, así que no hubo fuga que frenar).
- **El enjambre:** la cuenta compartida cubre varios agentes en una misma máquina, por un archivo común (`LEDGER_PATH`); no varias máquinas.
- **Dos cifras, siempre juntas.** 180 de 180 se midió con las banderas `is_sink` y `untrusted` que escribió el generador de ataques; con las que calcula el proxy en vivo son **120 de 180** (cuatro de seis familias). Detalle y frases permitidas: `results/test/LECTURA.md`, sección «Las banderas de cada llamada venían de las grabaciones»; tabla en `results/proxy_flags/`. No escribas «180 de 180» sin decir en la misma frase que es con las banderas de las grabaciones.
- **La demo y la evaluación usan configuraciones distintas:** la demo corre sin modelo de evidencia y rota al 30 % de la clave; la evaluación usa `models/search/frozen.json`.
- **Nombre:** si encuentras «Cuentagotas» en un texto vigente, es un error; corrígelo. Excepción: el proyecto de Vercel se sigue llamando `cuentagotas` por dentro; la URL pública ya es https://alicanto.vercel.app.
- Las tareas de `redteam/` van en una sesión de agente que no haya leído `engine/`.
- Si cambias algo de `demo/viz`, dilo en tu reporte: hay que redesplegar.

## Pendiente (depende de personas)

Revisar `README.md` y `project-description.md`; ensayar el pitch.
