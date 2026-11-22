# Estado del proyecto (para agentes)

Actualizado: domingo 22 de noviembre de 2026, 03:35 (H28,6). Lo mantiene el orquestador. Si empiezas una sesión, lee esto, `AGENTS.md` y tu issue. El resumen para personas está en `docs/INFORME_TURNOS.md`.

## En una frase

**Alicanto** (hasta el sábado a las 11:30 se llamó Cuentagotas) es un proxy entre un agente de IA y sus herramientas que mide cuánta de cada clave ya se filtró y la rota antes de que la fuga se complete. Está construido, evaluado y desplegado. **Congelamiento total desde el domingo a las 02:00:** solo arreglos de errores, láminas y ensayo; nada de funciones nuevas sin el visto bueno del líder. No hay tareas abiertas. En revisión del líder: PR #178 (descripción pública reescrita).

## Qué hay en `main`

- 931 tests en verde (`python -m pytest -q`). A las 16:20 se comprobó en un clon limpio del repo público que instala con `pip install -r requirements.txt`, que la suite pasa y que corren los comandos del README.
- Demo principal, del enjambre e interactiva (`demo/viz/`), desplegadas en https://alicanto.vercel.app. El despliegue es a mano: `demo/DEPLOY.md`.
- Evaluación final corrida una sola vez sobre el set sellado: `results/test/`. Simulación del atacante adaptativo: `results/adaptive/`.
- Hook de Claude Code que pasa `Bash` y `WebFetch` por el contador de bits: `integrations/claude_code/` (probado en una sesión real: permite sin fricción y niega con el motivo; el contador con un modelo real no quedó probado, porque el modelo se negó por su cuenta).
- Ideas de demo en paralelo: `demo/alternativas/`, una subcarpeta por alternativa; la demo oficial sigue siendo `demo/viz/`. Hay tres: 01 «El botín», 02 «El juez es el atacante» y 03 «20 agentes, una clave». La 03 trae terminales en vivo, un tablero con los datos de las pruebas y una versión con poco texto para el pitch (`?pitch=1`). `vercel.json` ya las publica en `/terminales`, `/pruebas` e `/informe`, pero el sitio público no se ha redesplegado: lo confirma el líder.
- Informe final del proyecto, para personas: `docs/INFORME_FINAL.md`. Informe técnico completo en PDF (89 páginas), con sus fuentes LaTeX y los scripts que regeneran sus tablas desde `results/`: `docs/informe/informe.pdf`.
- Pitch con cifras: `pitch/`. Guía para conectar el proxy a un agente real: `docs/QUICKSTART.md`.
- Corridas con un LLM real a través del proxy, hechas: `docs/LLM_EN_VIVO.md` (Haiku 5.5 y Sonnet 5.5 con n = 10, Opus 5.5 con n = 1; ninguna siguió la inyección, y hubo una rotación de más con Sonnet).

## Reglas vigentes

- **`engine/` y `models/` están congelados** (etiqueta `congelamiento`). Cualquier cambio lo autoriza el líder.
- **La evaluación final no se repite.** `python -m eval.final.run --split test` se niega a correr.
- **Lee `results/test/LECTURA.md` antes de escribir una cifra.** 180 de 180 ataques grabados prevenidos y 0 de 5.879 llamadas benignas bloqueadas, con tres límites que van siempre al lado: son ataques grabados (el adaptativo se midió aparte: 180 de 180, deteniendo las salidas tras tres rotaciones); costo de 39 rotaciones de más, en 34 de 90 sesiones benignas difíciles; y con el contador de bits solo se previenen 40 de 180.
- **Frase de novedad permitida:** «Hasta donde encontramos, nadie usa la fuga parcial medida de una credencial (en bits, sumada entre llamadas, codificaciones y agentes) para rotarla antes de que se complete.»
- **No decir:** «detiene el 100 %» a secas; que nadie junta fragmentos (existen Pipelock y AgentBrake); que somos los primeros; que los grafos «conectan pasos lejanos»; que Alicanto frenó a un LLM real (se corrieron tres modelos y ninguno siguió la inyección, así que no hubo fuga que frenar).
- **La configuración congelada no está en la frontera de Pareto de validación** y 4 de las 39 rotaciones de más del set de prueba son coincidencias al azar (`results/test/LECTURA.md`, puntos 9 y 10). No digas que la configuración es la óptima.
- **Puertos compartidos:** los tests que levantan los servicios locales usan 8101 a 8105; dos corridas a la vez en la misma máquina fallan por puerto ocupado. En la máquina del pitch no se corren tests mientras se ensaya o se presenta.
- **La cota de la rotación periódica vale para pedazos de 4 caracteres o más.** Con 1 a 3, la configuración evaluada rota al primer envío (máximo 12 bits) y la de la demo y del hook, sin modelo de evidencia, deja salir la clave entera en 10 de 18 combinaciones medidas (`results/short_fragments/`). No digas que la cota vale sin condiciones.
- **El enjambre:** la cuenta compartida cubre varios agentes en una misma máquina, por un archivo común (`LEDGER_PATH`); no varias máquinas.
- **Dos cifras, siempre juntas.** 180 de 180 se midió con las banderas `is_sink` y `untrusted` que escribió el generador de ataques; con las que calcula el proxy en vivo son **120 de 180** (cuatro de seis familias). Detalle y frases permitidas: `results/test/LECTURA.md`, sección «Las banderas de cada llamada venían de las grabaciones»; tabla en `results/proxy_flags/`. No escribas «180 de 180» sin decir en la misma frase que es con las banderas de las grabaciones.
- **La demo y la evaluación usan configuraciones distintas:** la demo corre sin modelo de evidencia y rota al 30 % de la clave; la evaluación usa `models/search/frozen.json`.
- **Nombre:** si encuentras «Cuentagotas» en un texto vigente, es un error; corrígelo. Excepción: el proyecto de Vercel se sigue llamando `cuentagotas` por dentro; la URL pública ya es https://alicanto.vercel.app.
- Las tareas de `redteam/` van en una sesión de agente que no haya leído `engine/`.
- Si cambias algo de `demo/viz`, dilo en tu reporte: hay que redesplegar.

## Pendiente (depende de personas)

Revisar `README.md` y `project-description.md`; ensayar el pitch.
