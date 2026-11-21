# Investigación: estado del arte, escenario y encaje con el track

Informe de investigación para el equipo. Fecha: sábado 21 de noviembre de 2026, madrugada (cerca de H4). Lo escribió un agente investigador que leyó el documento de diseño v4.0, `docs/BASES.md`, `docs/PLAN.md` y buscó en la web. Leyó resúmenes de artículos, no los artículos completos: antes de poner un dato en una lámina, una persona debe abrir la fuente.

Esta es la versión pública. Las secciones sobre debilidades del detector y la lista de mejoras no están en el repo: por la regla del equipo morado (`docs/PLAN.md`) el área Rojo no ve el detector antes de H20, así que esas partes van como issues a quienes les toca y el informe completo lo guarda el líder.

Convención: **[comprobado]** significa que lo ejecuté o lo leí en el código. **[sospecha]** significa que es una inferencia que no ejecuté. **[no verificado]** significa que no pude confirmarlo con una fuente.

---

## Resumen

1. La idea pasa la prueba del track: es casi literal el primer ejemplo de «Califica» («un monitor que vigila a un agente y lo frena»). Lo nuevo y defendible es contar bits por secreto en los argumentos de las herramientas y **rotar** la clave según lo medido. Ningún trabajo que encontramos hace las dos cosas.
2. Hay competidores directos que el documento no cita y hay que nombrar en las preguntas: OCELOT (presupuesto de fuga en min-entropía con libro contable determinista, junio de 2026) y las pasarelas MCP que bloquean secretos por regex (Docker MCP Gateway, GitGuardian). Tres afirmaciones del documento hay que corregir: que Nimbus es de caja blanca, que la rotación de la industria es solo por calendario y que «persistente entre sesiones» es una novedad. Lo último ya no es novedad, porque NeuroTaint persiste el estado entre sesiones, y además no está implementado.
3. Escenario recomendado: una healthtech ficticia que agenda horas y guarda fichas para centros médicos. Combina el comprador real (una startup que usa agentes de código) con datos sensibles de salud. La salud es un servicio esencial bajo la Ley 21.663, que exige alerta temprana a la ANCI en 3 horas.
4. «¿Dónde está la IA?»: la IA es el blanco y el vector del ataque. El monitor no es un LLM porque un monitor que se convence con texto no es un monitor. Hay que mostrar al menos unas corridas reales de un LLM siguiendo la inyección y un generador de variantes con LLM; si no, la frase queda vacía.

---

## A. El problema y el estado del arte

### A.1 El problema existe y tiene incidentes recientes

| Incidente | Fecha | Qué muestra | Fuente |
|---|---|---|---|
| «Toxic agent flow» en el servidor MCP de GitHub | Mayo de 2025 | Un issue público con instrucciones ocultas hace que el agente filtre datos de repositorios privados en un PR público. Es nuestro escenario casi exacto. | Invariant Labs [1] |
| «Lethal trifecta» | Junio de 2025 | Datos privados, más contenido no confiable, más un canal de salida, equivalen a exfiltración. Es la formulación más citada del problema. | Willison [2] |
| CurXecute en Cursor (CVE-2025-54135) | Julio de 2025 | Una inyección vía MCP de Slack reescribe `mcp.json` y logra ejecución remota. | Tenable [3] |
| Copilot (CVE-2025-53773) | Agosto de 2025 | Una inyección activa la autoaprobación de herramientas y logra ejecución remota. | Embrace The Red [4] |
| Extensión Amazon Q | Julio de 2025 | Un prompt destructivo entró en una versión publicada. | The Register [5] |
| s1ngularity/Nx, luego Shai-Hulud | Agosto y septiembre de 2025 | Robo masivo de credenciales en npm. El segundo ataque se habría apoyado en tokens no rotados tras el primero, lo que es un argumento directo a favor de rotar al detectar. | Datadog [6], Kaspersky [7] |

No confirmé que s1ngularity usara las CLI de IA locales de las víctimas. No usar ese detalle en el pitch sin fuente.

### A.2 Lo que dice el documento de cada trabajo

| Trabajo | Lo que dice el documento | Veredicto |
|---|---|---|
| CaMeL (Google DeepMind y otros, 2025) [8] | Exige reestructurar el agente; reglas binarias; no mide cuánto salió | **Correcto.** Intérprete propio, dos LLM y políticas de capacidad. En AgentDojo resuelve 77 % de las tareas contra 84 % sin defensa. |
| FIDES (Microsoft Research, 2025) [9] | Igual que CaMeL | **Correcto.** Etiquetas de confidencialidad e integridad con política determinista. No cuenta bits. |
| RTBAS (2025) [10] | Igual que CaMeL | **Correcto.** Control de flujo con un juez LLM y saliencia de atención; pide confirmación al usuario. |
| NeuroTaint («Ghost in the Agent», abril de 2026) [11] | Igual que CaMeL | **Existe, pero la caracterización es incompleta.** Es un auditor *offline* de registros que **persiste el estado de taint entre sesiones**. Eso debilita la novedad n.º 1 del documento. Los autores no coinciden entre agregadores: no verificado. |
| Llama Prompt Guard 2, LlamaFirewall, LLM Guard [12][13] | Miran cada mensaje por separado | **Correcto.** LlamaFirewall también trae AlignmentCheck, que es un auditor LLM y no un clasificador. El escáner Secrets de LLM Guard envuelve detect-secrets y solo actúa sobre la entrada. Su repositorio figura archivado. |
| «Caught in the Act(ivation)», Chauhan y Revankar, arXiv 2606.04141, 2 de junio de 2026 [14] | Caja blanca o InfoNCE con techo; no mira argumentos estructurados; se reinicia entre sesiones; no rota | **Mayormente correcto, con una corrección.** La caja blanca corresponde a las sondas de activaciones (CIFT), no al contador de fuga acumulada. Ver el detalle abajo. |
| arXiv 2605.11053 [15] | Clasifican ataques; no cuentan información | **Correcto.** Es un estudio empírico de clasificadores supervisados sobre el tráfico MCP, con grafo de llamadas y embeddings: AUROC 0,975 en RAS-Eval. Muestra que las divisiones al azar inflan el AUROC hasta en 26 puntos. Sirve para defender nuestra división por familia. |
| AgentDojo, InjecAgent, A3S-Bench, SafeClawArena, CodeIPI [16]–[20] | Inyección en general; sin goteo entre sesiones ni rotación | **Existen todos.** Con dos matices. A3S-Bench sí tiene casos de varios turnos. SafeClawArena usa credenciales canario y rastrea el flujo hacia 9 canales de salida. No encontré ninguno que mida goteo entre sesiones ni rotación, pero no los leí completos. CodeIPI es una tarea de Inspect Evals (UK AISI), no un artículo. |
| Práctica de la industria | La rotación es por calendario | **Exagerado.** AWS pone en cuarentena una clave IAM a los segundos de que el escaneo de secretos de GitHub la encuentra en un repo público [21]. Vault entrega secretos dinámicos con TTL [22]. Redacción sugerida: «la rotación automática existe por calendario, por TTL o tras una fuga pública completa; nada la dispara por fuga parcial dentro del tráfico de un agente». |

Detalle de «Caught in the Act(ivation)», según lo que el investigador web leyó del artículo:

- El contador de fuga acumulada (Nimbus) usa un estimador InfoNCE con techo de log2(17) ≈ 4,09 bits por turno.
- Los autores reconocen que los argumentos estructurados de herramientas son un punto ciego («a severe structural blind spot»).
- Reconocen que un atacante puede reiniciar la sesión para reiniciar el presupuesto.
- Sus respuestas son advertir, sanear o bloquear; no rota.
- El banco de pruebas es pequeño: 50 conversaciones de 20 turnos, y los autores lo llaman preliminar.
- Yo confirmé el resumen del artículo, que no nombra «Nimbus»; ese nombre viene del cuerpo según la búsqueda web.
- Una cifra de «90 % frente a 12 % de LlamaGuard» que circula en un resumen secundario no apareció en el artículo: **no usarla**.

### A.3 Trabajos que faltan en el documento y que el jurado podría conocer

- **OCELOT**, «Inference-Leakage Budgets for Privacy-Preserving LLM Agents» (Xie y Li, arXiv 2606.12341, junio de 2026) [23]. Confirmé el resumen.
  - Qué hace: un mediador en tiempo de ejecución cobra un costo en min-entropía por cada liberación de información contra un presupuesto por secreto. Un verificador determinista lo registra en un libro contable a prueba de manipulación.
  - Por qué importa: es el trabajo más cercano en teoría a nuestra novedad n.º 1.
  - En qué se diferencia: apunta a datos personales y a la inferencia, usa un modelo defensor afinado (un LLM en el camino de la decisión) y no habla de credenciales, de argumentos de herramientas ni de rotación.
  - Respuesta corta: «OCELOT presupuesta lo que el agente revela; nosotros medimos credenciales en los argumentos de herramientas, sin LLM en la decisión, y respondemos rotando en el gestor».
- **PRISM** (arXiv 2605.10614, mayo de 2026) [24]: detección de fuga de secretos durante la decodificación en sistemas de varios agentes. Necesita acceso al modelo y no rota.
- **Pasarelas MCP con bloqueo de secretos**: Docker MCP Gateway con `--block-secrets` (patrones regex que rechazan la llamada completa), Lasso y TrueFoundry (redactan), GitGuardian con ggshield y su servidor MCP, e Invariant Guardrails (Snyk compró Invariant Labs en junio de 2025) [25][26][27].
  - Todas buscan el secreto **completo** en cada mensaje. ~~Ninguna cuenta fragmentos codificados ni acumula en el tiempo.~~ (Falso: ver «Actualización de H10», más abajo. Pipelock y AgentBrake sí acumulan entre llamadas.)
  - Es el competidor que un jurado de la industria conoce. La respuesta es la demo misma: cuatro caracteres por llamada pasan cualquier regex.
- **Brokers de credenciales** (Aembit MCP Identity Gateway, secretos dinámicos de Vault) [22][28]: el agente nunca ve la clave.
  - Es la crítica más fuerte: «¿por qué no simplemente no darle el secreto al agente?».
  - Respuesta: son complementarios. En la práctica los `.env`, los YAML y los logs viven en el repositorio que el agente lee. El medidor cubre lo que el broker no cubre: lo que ya está en el repositorio y lo que sale por canales permitidos.
  - No pude confirmar las ofertas de 1Password, Astrix, Pillar ni Cloudflare para agentes: no las citen.

### A.4 Base teórica que conviene citar

- **Flujo cuantitativo de información**: Smith, «On the Foundations of Quantitative Information Flow», FoSSaCS 2009 [29]. Introduce la vulnerabilidad y la min-entropía.
  - Nuestra «proposición de bits filtrados» es el caso trivial de la fuga en min-entropía: secreto uniforme y posiciones reveladas exactamente.
  - Citarlo convierte «contamos caracteres» en «medimos fuga en min-entropía sobre un canal observado». Cuesta una línea en la lámina técnica.
- **CUSUM** (Page, 1954): se usa en detección de intrusiones desde hace dos décadas, por ejemplo en detección de DoS por cambio de régimen [30]. No encontré un uso previo de CUSUM para monitorear agentes LLM. No es prueba de que no exista, pero sostiene la frase «hasta donde encontramos».

### A.5 Qué es realmente nuevo y qué conviene dejar de decir

**Actualizado el sábado 21 de noviembre a las 10:00 (H11).** La versión de H4 de esta sección quedó obsoleta: desde entonces se implementaron el modelo de evidencia y la cuenta compartida, aparecieron competidores que no conocíamos y se corrió la evaluación final. Lo que sigue reemplaza a la versión anterior.

Defendible, con la frase «hasta donde encontramos»:

1. **La frase de novedad, una sola:** nadie usa la fuga parcial medida de una credencial (en bits, sumada entre llamadas, codificaciones y agentes) para **rotarla** antes de que se complete. Lo nuevo es la respuesta, no el conteo.
2. **Leer fragmentos cortos y codificados.** Las herramientas que ya juntan fragmentos entre llamadas declaran que pierden los codificados (Pipelock) o los de menos de 20 caracteres (AgentBrake). Alicanto cuenta fragmentos de 4 caracteres en seis codificaciones. Respaldo: `engine/bits/tests/test_short_encoded.py`.
3. **Rotar ante la sospecha en vez de bloquear.** En la evaluación final, sobre 180 ataques de seis familias nuevas, ninguno sacó más de 32 de 160 bits de la clave vigente, sin bloquear ninguna de 5.879 llamadas benignas. Sin rotación, el ataque triunfa en 150 de 180. Respaldo y límites: `results/test/LECTURA.md`.
4. **Una cuenta por clave entre varios agentes,** en un mismo proceso y con persistencia en disco (`engine/detector/ledger.py`). Existen monitores entre agentes (Brown et al.; Makins et al.), pero usan un LLM o agrupamiento, no una cuenta de bits por secreto.

Cambió respecto de H4:

- «La mitad *lo delata la evidencia* todavía no existe, porque S = 0»: **ya no es cierto en la configuración evaluada.** El modelo de evidencia existe, está congelado, y en la evaluación final es lo que generaliza a familias nuevas (con el contador de bits solo se previenen 40 de 180). **Sigue siendo cierto en la demo y en el proxy en vivo,** que corren sin modelo: ahí decide solo el contador, con rotación al 30 % de la clave.
- «Persistente entre sesiones no está en el código»: **ya está** (`SharedLedger.save` y `load_state`, con tests). También está conectado al proxy en vivo, entre procesos de una misma máquina (`LEDGER_PATH`, tarea #138). Y no se presenta como novedad.

Dejar de decir:

- «Ningún filtro junta fragmentos» o «nadie acumula en el tiempo»: falso (Pipelock, AgentBrake, y los presupuestos de fuga de Chauhan y Revankar, OCELOT y Metere).
- «Somos los primeros en contar fuga acumulada» y «un presupuesto de bits de salida es nuevo».
- «Detiene el 100 % de los ataques», sin decir que son ataques grabados y no un atacante que se adapta a la rotación.
- «El contador de bits detecta codificaciones desconocidas»: no; eso lo cubre la evidencia de comportamiento, al costo de rotar de más en casos benignos difíciles (34 de 90 sesiones).
- «Acoplar el GFF con el DAG conecta pasos lejanos»: el grafo de archivos entra solo como señal por llamada en el modelo de evidencia, las aristas de sospecha (R⁺) no están conectadas al detector, y la prueba que mediría su aporte (T6) no se calculó en el set de prueba (en validación, la diferencia de AUC es +0,0045). Detalle en `results/test/LECTURA.md`.
- «Persistente entre sesiones» como novedad.

---
---

## D. Escenario de la demo

Las tres opciones usan los mismos servicios: solo cambian los nombres, el issue envenenado y lo que devuelve la API con la clave robada. Todo es ficticio: no imitar marcas reales (ni clínicas, ni bancos, ni Transbank, Fonasa o el Registro Civil).

| Opción | Qué abre la clave | Por qué impacta en Chile | Debilidad |
|---|---|---|---|
| **1. Healthtech ficticia** que agenda horas y guarda fichas para centros médicos (variante de la propuesta actual) | La API de fichas clínicas: con 200 el atacante descarga pacientes sintéticos; con 401, nada | Los datos de salud son sensibles bajo la Ley 21.719. La prestación de salud figura entre los servicios esenciales de la Ley 21.663 (alerta temprana a la ANCI en 3 horas). Hubo filtraciones de salud recientes: Servicio de Salud Araucanía Sur, 25 mil registros, mayo de 2026 [31]. La imagen «fichas en manos del atacante» se entiende sin explicar. | Hay que aclarar que se protege la **llave** que abre las fichas, no las fichas mismas (eso es la sección 4.3, nivel 2) |
| **2. Fintech ficticia** con una clave de pasarela de pagos y un secreto de webhook | Con 200 el atacante emite un reembolso o lee transacciones | Pérdida de dinero directa. La banca también es servicio esencial bajo la Ley 21.663. Platanus invierte en muchas fintech. | Más genérico; el jurado ve «robo de API key» sin carga humana |
| **3. Servicio público ficticio** (trámites en línea) | Con 200, consulta de datos de ciudadanos | Alerta de la ANCI de mayo de 2026: una filtración de datos públicos partió de la credencial robada de un funcionario [32] | Sensible políticamente; fácil que parezca imitar a un organismo real; el comprador (el Estado) es lento |

**Recomendación: la opción 1, encuadrada como startup (una healthtech) y no como clínica.**

Argumento ante el jurado: «Una healthtech de cinco ingenieros usa Claude Code o Cursor sobre su repo. El `.env` tiene la llave de la API de fichas. Un issue envenenado se la lleva de a cuatro caracteres. Bajo la Ley 21.663, eso es un incidente que hay que reportar a la ANCI en 3 horas, y bajo la 21.719 son datos sensibles». Junta así:

- el comprador real del documento: un equipo de plataforma en una startup que usa agentes de código;
- la carga humana de los datos de salud;
- un marco legal vigente y conocido.

Pendiente de verificar antes de ponerlo en una lámina:

- el plazo de 72 horas de la Ley 21.719;
- su fecha de vigencia: diciembre de 2026, con un proyecto de postergación aprobado en general en comisión el 5 de noviembre de 2026 [33];
- la lista exacta de servicios esenciales de la Ley 21.663.

El investigador web encontró una nota de prensa sobre un ciberataque a un hospital universitario de Santiago en noviembre de 2026, pero no la leí: no la citen sin abrirla.

---

## E. Encaje con el track

**¿Pasa la prueba?** Sí. Defiende un agente de IA contra un ataque dirigido a la IA (inyección de prompt) y mide con un resultado verificable (bits, 200 contra 401). Corresponde a la línea 1 (AI control) y es casi literal el primer ejemplo de «Califica». También toca la línea 2: robustez frente a inyecciones, medida contra ataques.

**Argumento más fuerte:** el resultado medible que piden las bases. El mismo ataque funcionando a la izquierda y detenido a la derecha, más una tabla de bits filtrados por familia contra las defensas que usan hoy las empresas, con falsas alarmas medidas. Eso solo vale si la demo se gana el 200 y la métrica no infla.

**Punto débil: «¿dónde está la IA?».** El jurado puede leer «proxy con regex y estadística, ciberseguridad clásica», que es justo el caso «no califica». Cómo responder, en este orden:

1. **La IA es el blanco y el vector.** El ataque no existe sin un agente LLM que obedece texto no confiable; sin IA no hay problema. Las bases aceptan proyectos donde la IA «es el blanco».
2. **El monitor no es un LLM a propósito.** En AI control un monitor de confianza no tiene por qué ser un modelo. Un monitor LLM se ataca con la misma inyección que ataca al agente (LlamaFirewall trae un auditor LLM; CaMeL aísla al LLM precisamente por eso). Frase: «un guardia que se convence con texto no es un guardia».
3. **Mostrar IA real en la evaluación**, no solo decirlo:
   - corridas en vivo con un LLM siguiendo la inyección, con la tasa de seguimiento medida;
   - un generador de variantes con LLM para el set rojo;
   - el ataque adaptativo de caja blanca de H20 hecho con un LLM.

   Si nada de esto ocurre, la respuesta 3 no se dice.
4. **La IA que agrega el atacante con LLM no le sirve contra el medidor**, porque el medidor cuenta información, no intención. Es la frase central del documento y conviene amarrarla a esta pregunta.

---

## Fuentes

[1] Invariant Labs, «GitHub MCP Exploited», mayo de 2025. https://invariantlabs.ai/blog/mcp-github-vulnerability
[2] S. Willison, «The lethal trifecta for AI agents», 16 de junio de 2025. https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/
[3] Tenable, CVE-2025-54135 y CVE-2025-54136 en Cursor. https://www.tenable.com/blog/faq-cve-2025-54135-cve-2025-54136-vulnerabilities-in-cursor-curxecute-mcpoison
[4] Embrace The Red, «GitHub Copilot remote code execution via prompt injection» (CVE-2025-53773). https://embracethered.com/blog/posts/2025/github-copilot-remote-code-execution-via-prompt-injection
[5] The Register, prompt destructivo en la extensión Amazon Q, julio de 2025. https://www.theregister.com/2025/07/24/amazon_q_ai_prompt/
[6] Datadog Security Labs, «Learnings from recent npm compromises». https://securitylabs.datadoghq.com/articles/learnings-from-recent-npm-compromises/
[7] Kaspersky, ataque s1ngularity a Nx. https://www.kaspersky.com/blog/nx-build-s1ngularity-supply-chain-attack/54223/
[8] Debenedetti et al., «Defeating Prompt Injections by Design» (CaMeL), 2025. https://arxiv.org/abs/2503.18813
[9] Costa et al., «Securing AI Agents with Information-Flow Control» (FIDES), 2025. https://arxiv.org/abs/2505.23643
[10] «RTBAS: Defending LLM Agents Against Prompt Injection and Privacy Leakage», 2025. https://arxiv.org/abs/2502.08966
[11] «Ghost in the Agent: Redefining Information Flow Tracking for LLM Agents» (NeuroTaint), abril de 2026. https://arxiv.org/abs/2604.23374
[12] Meta, «LlamaFirewall», 2025. https://arxiv.org/abs/2505.03574
[13] Protect AI, LLM Guard, escáner de secretos. https://protectai.github.io/llm-guard/input_scanners/secrets
[14] Chauhan y Revankar, «Caught in the Act(ivation): Toward Pre-Output and Multi-Turn Detection of Credential Exfiltration by LLM Agents», 2 de junio de 2026. https://arxiv.org/abs/2606.04141
[15] Zavrak, «Content-Aware Attack Detection in LLM Agent Tool-Call Traffic», mayo de 2026. https://arxiv.org/abs/2605.11053
[16] AgentDojo, 2024. https://arxiv.org/abs/2406.13352
[17] InjecAgent, 2024. https://arxiv.org/abs/2403.02691
[18] ASEval y A3S-Bench, 2026. https://arxiv.org/abs/2605.22321
[19] SafeClawArena, 2026. https://arxiv.org/abs/2606.30755
[20] Inspect Evals, tarea de inyección en agentes de código (CodeIPI). https://ukgovernmentbeis.github.io/inspect_evals/evals/ipi_coding_agent/index.html
[21] Unit 42, cuarentena automática de claves de AWS expuestas. https://unit42.paloaltonetworks.com/detecting-exposed-aws-iam-credentials/
[22] HashiCorp, identidad de agentes de IA con Vault. https://developer.hashicorp.com/validated-patterns/vault/ai-agent-identity-with-hashicorp-vault
[23] Xie y Li, «OCELOT: Inference-Leakage Budgets for Privacy-Preserving LLM Agents», 10 de junio de 2026. https://arxiv.org/abs/2606.12341
[24] PRISM, mayo de 2026. https://arxiv.org/abs/2605.10614
[25] Comparativa de pasarelas MCP. https://aimultiple.com/mcp-gateway
[26] GitGuardian, servidor MCP. https://github.com/GitGuardian/ggmcp
[27] Snyk adquiere Invariant Labs, junio de 2025. https://snyk.io/news/snyk-acquires-invariant-labs-to-accelerate-agentic-ai-security-innovation
[28] Aembit, proxy para agentes. https://docs.aembit.io/dev-guide/integration/agent-proxy/
[29] G. Smith, «On the Foundations of Quantitative Information Flow», FoSSaCS 2009. https://doi.org/10.1007/978-3-642-00596-1_21
[30] Wang, Zhang y Shin, detección de cambio de régimen para DoS (CUSUM). https://www.eecis.udel.edu/~hnw/paper/tdsc.pdf ; Tartakovsky et al. https://arxiv.org/abs/1212.1829
[31] BioBioChile, filtración en el Servicio de Salud Araucanía Sur, mayo de 2026. https://www.biobiochile.cl/noticias/nacional/region-de-la-araucania/2026/05/05/filtran-mas-de-25-mil-datos-sensibles-de-pacientes-desde-servicio-de-salud-araucania-sur.shtml
[32] 24horas, la ANCI confirma una filtración por robo de credenciales de un funcionario, 2026. https://www.24horas.cl/actualidad/nacional/por-robo-del-usuario-a-un-funcionario-directora-s-de-la-anci-confirma-caso-de-filtracion-de-datos
[33] Ley 21.663: https://www.bcn.cl/leychile/navegar?idNorma=1202434 ; material de la ANCI sobre plazos: https://anci.gob.cl/documents/4684/Ley_Marco_2025_-Presentaci%C3%B3n-MAVL-PPIOS.pptx.pdf ; Ley 21.719: https://www.bcn.cl/leychile/navegar?idNorma=1209272 ; postergación en la Cámara: https://www.camara.cl/cms/2026/11/05/proteccion-de-datos-comision-aprobo-postergar-entrada-en-vigencia-de-la-ley/

### Lo que no pude verificar

- Los autores de NeuroTaint.
- El nombre «Nimbus» dentro del artículo: el resumen no lo usa.
- La cifra «90 % frente a 12 %» atribuida a ese trabajo.
- La lista exacta de autores de CaMeL.
- Que s1ngularity usara CLI de IA.
- Las ofertas para agentes de 1Password, Astrix, Pillar y Cloudflare.
- Los plazos de 72 horas de ambas leyes (solo en fuentes secundarias) y la lista de servicios esenciales de la Ley 21.663 (de memoria).
- La nota sobre el ciberataque a un hospital en noviembre de 2026.
- Page (1954), que no consulté directamente.
- Lo que dicen los artículos más allá de sus resúmenes: no leí ninguno completo.

---

## Actualización de H10 (sábado 21 de noviembre, 09:30)

Segunda pasada de investigación, hecha por otro agente. «Abierto» significa que leyó la página; lo demás va como **[no verificado]**. Corrige tres cosas de este mismo documento.

### Correcciones

1. **Ya existen herramientas que acumulan fragmentos entre llamadas.** La afirmación de la sección A.3 («ninguna cuenta fragmentos codificados ni acumula en el tiempo») es falsa tal como está escrita.
   - **Pipelock** (código abierto, v1.2.0, 11 de marzo de 2026): reensambla fragmentos por sesión y lleva un presupuesto de entropía en bits por ventana de tiempo, también en el camino MCP. Según su propia documentación, los fragmentos codificados evaden el reensamblado, el estado es por sesión, solo bloquea, y su guía de canarios dice que no detecta particiones en tres o más requests. Abierto: https://raw.githubusercontent.com/luckyPipewrench/pipelock/main/README.md y https://pipelab.org/blog/cross-request-exfiltration/
   - **AgentBrake** (proxy MCP, proyecto pequeño): compara huellas de datos protegidos tras decodificar base64, hex, URL e invertido. Declara que pierde fragmentos de menos de 20 caracteres. Abierto: https://github.com/Ujjwaljain16/AgentBrake
2. **OCELOT**: el presupuesto es por tarea o trayectoria, no por secreto, y el LLM solo propone: decide un verificador determinista. Abierto: https://arxiv.org/html/2606.12341v1
3. **Chauhan y Revankar (Nimbus)**: la cifra de 0,90 de detección contra 0,12 de LlamaGuard **sí** está en el artículo (tabla 3, sobre 50 conversaciones propias). La sección A.2 decía que no aparecía. Que una persona abra la tabla antes de citarla. Abierto: https://arxiv.org/html/2606.04141

### Trabajos que faltaban

- **«Capacity ledger»** (Metere, arXiv 2605.20734, 20 de mayo de 2026): libro de capacidad por destino de salida, tipo balde con fugas; demora o cancela. No conoce el secreto, mira mensajes salientes y no rota. Con esto, «un presupuesto de bits de salida» ya no es novedad. Abierto: https://arxiv.org/html/2605.20734
- **Monitores entre agentes**: Brown et al. (arXiv 2605.31593, 29 de mayo de 2026) y Makins et al. (arXiv 2607.07368, 8 de julio de 2026), que describe el «efecto fragmentación» contra monitores por instancia. Usan un LLM o agrupamiento, no cuentan bits por secreto. Makins sirve de cita para la lámina del enjambre. Abiertos los resúmenes: https://arxiv.org/abs/2605.31593 y https://arxiv.org/abs/2607.07368

### Qué se puede decir y qué no

- **Sí:** «Hasta donde encontramos, nadie usa la fuga parcial medida de una credencial (en bits, sumada entre llamadas, codificaciones y agentes) para rotarla antes de que se complete.»
- **No:** «ningún filtro detecta una clave sacada en fragmentos», «somos los primeros en contar fuga acumulada», ni «persistente entre sesiones» como novedad.

### Comprador y marco legal (verificado en fuente)

- La ANCI lista como servicios esenciales la «prestación institucional de salud: hospitales, clínicas, consultorios y centros médicos» y también los «servicios de TI gestionados por terceros». Abierto: https://anci.gob.cl/documents/4692/PPT_Presentacion_SE_y_OIV_VF.pdf
- Plazos de reporte de 3 horas, 72 horas y 15 días corridos; no reportar es infracción grave, hasta 10.000 UTM (20.000 para operadores de importancia vital). La multa es por no reportar, no por la fuga. Abierto: https://www.cariola.cl/app/uploads/2025/03/Alerta-Legal_04.03.2025.pdf
- Precios de comparables: Docker MCP Gateway y el núcleo de Pipelock son gratuitos; GitGuardian publica solo su plan gratuito. Las demás cifras de precios quedaron **[no verificado]**: no usarlas.
