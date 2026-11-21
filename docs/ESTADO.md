# Estado del proyecto (para agentes)

Actualizado: sábado 21 de noviembre de 2026, 11:45 (H12,75). Lo mantiene el orquestador. Si empiezas una sesión, lee esto, `AGENTS.md` y tu issue. El resumen para personas está en `docs/INFORME_TURNOS.md`.

## En una frase

**Alicanto** (hasta el sábado a las 11:30 se llamó Cuentagotas) es un proxy entre un agente de IA y sus herramientas que mide cuánta de cada clave ya se filtró y la rota antes de que la fuga se complete. Está construido, evaluado y desplegado. No hay tareas abiertas.

## Qué hay en `main`

- Más de 700 tests en verde (`python -m pytest -q`).
- Demo principal, del enjambre e interactiva (`demo/viz/`), desplegadas en https://alicanto.vercel.app. El despliegue es a mano: `demo/DEPLOY.md`.
- Evaluación final corrida una sola vez sobre el set sellado: `results/test/`. Simulación del atacante adaptativo: `results/adaptive/`.
- Pitch con cifras: `pitch/`. Guía para conectar el proxy a un agente real: `docs/QUICKSTART.md`.
- Comando para corridas con un LLM real, listo y sin ejecutar: `docs/LLM_EN_VIVO.md`.

## Reglas vigentes

- **`engine/` y `models/` están congelados** (etiqueta `congelamiento`). Cualquier cambio lo autoriza el líder.
- **La evaluación final no se repite.** `python -m eval.final.run --split test` se niega a correr.
- **Lee `results/test/LECTURA.md` antes de escribir una cifra.** 180 de 180 ataques grabados prevenidos y 0 de 5.879 llamadas benignas bloqueadas, con tres límites que van siempre al lado: son ataques grabados (el adaptativo se midió aparte: 180 de 180, deteniendo las salidas tras tres rotaciones); costo de 39 rotaciones de más, en 34 de 90 sesiones benignas difíciles; y con el contador de bits solo se previenen 40 de 180.
- **Frase de novedad permitida:** «Hasta donde encontramos, nadie usa la fuga parcial medida de una credencial (en bits, sumada entre llamadas, codificaciones y agentes) para rotarla antes de que se complete.»
- **No decir:** «detiene el 100 %» a secas; que nadie junta fragmentos (existen Pipelock y AgentBrake); que somos los primeros; que los grafos «conectan pasos lejanos»; que se corrió un LLM real.
- **El enjambre:** la cuenta compartida cubre varios agentes en una misma máquina, por un archivo común (`LEDGER_PATH`); no varias máquinas.
- **La demo y la evaluación usan configuraciones distintas:** la demo corre sin modelo de evidencia y rota al 30 % de la clave; la evaluación usa `models/search/frozen.json`.
- **Nombre:** si encuentras «Cuentagotas» en un texto vigente, es un error; corrígelo. Excepción: el proyecto de Vercel se sigue llamando `cuentagotas` por dentro; la URL pública ya es https://alicanto.vercel.app.
- Las tareas de `redteam/` van en una sesión de agente que no haya leído `engine/`.
- Si cambias algo de `demo/viz`, dilo en tu reporte: hay que redesplegar.

## Pendiente (depende de personas)

Clave de API para las corridas con un LLM real; logotipo nuevo con el nombre Alicanto; revisar `README.md` y `project-description.md`; ensayar el pitch.
