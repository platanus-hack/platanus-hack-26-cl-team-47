# Bases del track: AI Security

Platanus Hack 26, Santiago. Somos team-47 y competimos en el track **AI Security** ("Hacer más seguros los modelos de frontera").

Este archivo copia el brief de tracks de la organización ("Tracks Santiago 26"), tal como estaba el 21 de noviembre de 2026. Fuente: <https://claude.ai/artifact/UvauEetvmJ8BWKnMvrRRFU>. Si la organización lo cambia, manda la fuente.

El brief no trae premios, entregables ni plazos. Esos datos hay que buscarlos en los canales oficiales del evento.

## Qué pide el track

Construir herramientas concretas que hagan que los modelos más avanzados de IA sean más seguros: atacarlos para encontrar sus fallas, defenderlos o medir con rigor qué tan peligrosos pueden ser.

## La prueba

> El proyecto tiene que atacar, defender o medir un modelo o agente de IA, o usar IA para que el defensor gane. Si la IA es solo el tema de la app, no es de este track.

El equipo elige su track. El encaje no se revisa en la puerta: se castiga en la evaluación.

## La frontera

> La seguridad de la IA tiene que ser el producto, no una característica. Una demo fuerte muestra un resultado medible: el ataque funcionando y la defensa deteniéndolo, o una eval con números que antes no existían.

## Cinco líneas de trabajo

1. **AI control.** Herramientas que aumenten la visibilidad, el control y la seguridad al correr agentes potencialmente desalineados. Si un modelo está intentando causar daño, ¿cómo lo detectas o lo limitas? Referencias: The Case for AI Control, ControlArena.
2. **Guardrails y robustez adversarial.** Técnicas o herramientas que hagan a los modelos más robustos frente a la presión humana (jailbreaks, inyecciones). Vale la defensa, por ejemplo mejores clasificadores, o la ofensa: encontrar o evaluar nuevos tipos de ataque.
3. **Cyber evals.** Evaluaciones que midan con rigor el uplift que un modelo le da a un humano en tareas de alto riesgo, como la seguridad ofensiva. Referencias: Evals Playbook, Inspect Cyber, Cybench.
4. **Interpretabilidad pragmática.** Usar las herramientas que hoy permiten leer qué pasa dentro de un modelo (circuit tracing, activation NLAs) para resolver problemas reales de seguridad. Referencia: A Pragmatic Vision for Interpretability.
5. **Defensa (def/acc).** Herramientas con las que la IA fortalezca más al defensor que al atacante: descubrir y parchar vulnerabilidades de forma autónoma, endurecer sistemas críticos o detectar ataques asistidos por IA (phishing, deepfakes, operaciones de influencia). Referencias: d/acc, los 7 cyber reasoning systems finalistas del AIxCC de DARPA (open source).

## Califica

- Un monitor que vigila a un agente en un entorno tipo ControlArena y lo frena cuando intenta sabotear su tarea.
- Un clasificador de jailbreaks o inyecciones de prompt, medido contra ataques reales.
- Un generador automático de ataques que encuentra fallas nuevas en un modelo.
- Una eval reproducible que mide cuánto ayuda un modelo a resolver retos de seguridad ofensiva.
- Una sonda sobre las activaciones de un modelo que detecta engaño o intención dañina.
- Un sistema que encuentra y parcha vulnerabilidades solo, o que detecta phishing o deepfakes generados con IA.

## No califica

- Agregarle login o cifrado a una app de otro tema.
- Un chatbot que responde preguntas sobre seguridad.
- Ciberseguridad tradicional donde la IA no ataca, no defiende ni es el blanco.
- Un wrapper que solo llama a la API de moderación de un proveedor.
- Un benchmark de capacidades generales sin relación con riesgo.

## Casos frontera que nos tocan

| Idea | Va a | Por qué |
|---|---|---|
| Detector de phishing o deepfakes hechos con IA | AI Security | Def/acc: la IA le da ventaja al defensor. |
| Escáner de vulnerabilidades sin IA en ningún lado | Ningún track limpio | Es ciberseguridad clásica; el track pide que la IA ataque, defienda o sea el blanco. |

## Preguntas para partir

- Si el agente que corre en tu máquina quisiera hacer daño, ¿cómo te darías cuenta?
- ¿Qué ataque a un modelo funciona hoy y nadie ha medido bien?
- ¿Qué puedes leer dentro de un modelo que no se ve en su respuesta?
- ¿Qué trabajo de un equipo de seguridad podría hacer un agente esta noche?

## Cómo se evalúa

La rúbrica es la misma para los cinco tracks. El encaje con el track no es un criterio propio: se refleja sobre todo en Originalidad e Impacto.

| Criterio | Peso | Qué mira |
|---|---|---|
| Originalidad | 15 | Si sorprende o es la primera idea que se viene a la cabeza. |
| Ambición | 20 | Qué tan alto apuntaron para 36 horas. |
| Ejecución | 20 | Qué tan pulido y coherente quedó; si los flujos funcionan. |
| Aspecto técnico | 25 | Si hay trabajo de ingeniería real o se siente trivial. |
| Impacto | 20 | Si entrega valor significativo a alguien. |

## Los otros cuatro tracks

Sirven para saber dónde termina el nuestro.

| Track | Su prueba |
|---|---|
| Hardware | Tiene que haber un objeto sobre la mesa de los jueces. Si la demo completa cabe en una pantalla, no es de este track. |
| Physical World | La entrada es una señal física (cámara, GPS, audio, sensor) o la salida es una orden a algo físico. |
| Multiplayer | El producto tiene que mejorar cuando hay más de una persona usándolo. |
| Simulations | La simulación tiene que responder una pregunta del tipo "¿qué pasaría si…?". |
