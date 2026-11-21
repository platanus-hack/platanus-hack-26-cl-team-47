# Informe de turnos

Para quien entra a un turno y necesita saber en cinco minutos qué pasó, cómo está el proyecto y qué le toca. Se actualiza en cada rotación del equipo.

**Cómo actualizarlo:** al cerrar un turno, agrega una entrada nueva arriba de la sección «Turnos», con la hora, y corrige «Estado actual» y «Pendientes de personas». No borres las entradas anteriores. El detalle técnico para los agentes está en `docs/ESTADO.md`; este archivo es para las personas.

---

## Estado actual

Actualizado: sábado 21 de noviembre de 2026, 09:30 (hora 10,5 de 34).

**El proyecto.** Cuentagotas es un proxy entre un agente de IA y sus herramientas. Mide cuántos bits de cada clave ya se filtraron, aunque salgan de a cuatro caracteres o codificados, y rota la clave antes de que la fuga se complete. Competimos en el track AI Security.

**Qué funciona hoy, comprobado:**
- La demo principal: el mismo ataque termina en 200 sin protección y en 401 con Cuentagotas.
- La demo del enjambre: cinco agentes se reparten la fuga; con una cuenta por agente nadie la ve (200), con la cuenta global la clave rota (401).
- La demo interactiva: el público elige cómo se disfraza el fragmento (tal cual, base64 o al revés).
- El ataque en vivo con todos los servicios reales en local.
- Unos 660 tests automáticos en verde, 65 tareas cerradas, sin PR abiertos.

**Resultado en validación** (no es la cifra final y no va en las láminas):

| Sistema | Ataques prevenidos | Falsas alarmas |
|---|---|---|
| Cuentagotas | 95 % | 0 |
| Cuentagotas sin rotación | 52,5 % | 0 |
| Lista de destinos permitidos más detect-secrets | 75 % | 0 |
| Reensamblado por sesión (réplica de herramientas tipo Pipelock) | 58,8 % | 0 |
| Presupuesto de bits (réplica) | 93,8 % | 1,9 % |

Nuestro peor número: 60 % contra una codificación inventada que el motor no sabe leer.

**En curso ahora:**
- La búsqueda de umbrales que define la configuración congelada, corriendo en la máquina del orquestador.
- Después de eso, el orquestador abre el set de prueba sellado y corre la evaluación final una sola vez. De ahí salen las cifras del pitch.

**Dónde verlo:**
- Demo en local: `python -m http.server 8200 --directory demo/viz` y abrir `http://127.0.0.1:8200/`.
- Láminas: `pitch/index.html`. Guion: `pitch/GUION.md`. Preguntas del jurado: `pitch/PREGUNTAS.md`.
- Descripción pública: `project-description.md`.

## Quién está con qué

| Persona | Estado | Tarea |
|---|---|---|
| José Carlos (`JCBasulto`) | Activo | #139: comando para correr un LLM real a través del proxy, listo para enchufar la clave de API. Es además el único que toca el detector y la evaluación |
| Victoria (`VictoriaGuerriero`) | Activa | #138: enjambre en vivo y guía de inicio. #142: pitch para 3 minutos con corte |
| Tomás (`Terdmannsdorffer`) | Sin tokens | No recibe tareas |
| Matías (`matix3000`) | Sin tokens | No recibe tareas |
| Juan Pedro (`jplira2`), líder | Activo | Corre el orquestador y la sesión del equipo rojo |

Si alguien recupera tokens o se queda sin ellos, avísalo en el board: el orquestador reparte según eso.

## Pendientes de personas

Ningún agente puede hacer esto. Ordenado por importancia.

1. **Deploy en Vercel** y poner la URL en `platanus-hack-project.jsonc`. En el tour fue requisito tener la app desplegada, y hoy ese campo está vacío. Pasos en `demo/DEPLOY.md`. En camino, lo lleva Juan Pedro.
2. **Clave de API para correr un LLM real** a través del proxy. Hoy todas las corridas son guiones sin LLM, y las bases excluyen «ciberseguridad tradicional donde la IA no es el blanco». Es el mayor riesgo de encaje con el track. La entrega Juan Pedro.
3. **Hablar con un posible comprador** (alguien de TI de una clínica o de una healthtech) y llevar su frase a la lámina final. Es lo que más sube el criterio de impacto.
4. **Preguntar a la organización:** hora exacta de corte del repositorio, cómo se pasa a la final, y si en Santiago hay premio del público o de sponsor.
5. **Revisar `README.md` y `project-description.md`.** Son borradores escritos por agentes; las reglas del equipo piden que una persona los reescriba o los apruebe.
6. **Ensayar el pitch con cronómetro.** En las finales del tour fueron 3 minutos de demo con corte y 2 de preguntas.
7. **Confirmar la lámina final:** a quién le vendemos y qué pedimos. Hay un borrador (responsables de seguridad de prestadores de salud; dos equipos para un piloto).

## Cosas que hay que saber antes de hablar del proyecto

- **Frase de novedad permitida:** «Hasta donde encontramos, nadie usa la fuga parcial medida de una credencial (en bits, sumada entre llamadas, codificaciones y agentes) para rotarla antes de que se complete.»
- **No decir:** que nadie junta fragmentos entre llamadas (existen Pipelock y AgentBrake), que somos los primeros, ni que detectamos esteganografía.
- **Qué es real y qué es simulado:** el proxy, el motor, el gestor de secretos y el servidor del atacante son reales y corren en local. Las claves son sintéticas, el hospital es ficticio y el agente de la demo es un guion, no un LLM.
- **La demo y la evaluación usan configuraciones distintas.** La demo rota cuando se filtró el 30 % de la clave y corre sin el modelo de evidencia. La evaluación usa la configuración congelada.
- **El enjambre** funciona en la demo y en los tests. Conectarlo al proxy en vivo es la tarea #138, en curso.
- **Agenda del domingo sin confirmar:** planificar con el cierre más temprano (08:30).

## Reglas de trabajo vigentes

- Las tareas llegan como issues con la etiqueta `tarea` y una mención en el board. Cada agente las toma en su sesión actual, sin reiniciar.
- El set de prueba está sellado en la rama `11-set-sellado`. Nadie la abre: lo hace el orquestador para la evaluación final.
- El detector (`engine/`) queda congelado desde la evaluación final. Cualquier cambio posterior lo autoriza el líder.
- Quien haya leído el código del detector no escribe ataques: esas tareas van en una sesión de agente nueva.
- Las cifras de las láminas salen de la evaluación final, nunca de validación.

---

## Turnos

### Sábado 21, 02:00 a 09:30

Escrito por el orquestador. Lo anterior a las 03:45 está reconstruido del historial del board.

**02:00 a 04:00. Se cerró el producto base.**
- Quedaron en `main` el proxy, el motor de bits, el detector, los grafos, el gestor de secretos con rotación, la API protegida y el servidor del atacante.
- Primera demo real de punta a punta, con el 200 y el 401.
- Se corrigió un error del motor que encontraron las pruebas automáticas.
- Tomás se quedó sin tokens.

**04:00 a 06:00. Escenario, datos y nombre.**
- Se eligió el escenario: el Hospital Regional Tres Cóndores, ficticio.
- Se generaron los ataques de entrenamiento y de validación (80 y 80), en sesiones de agente que no habían visto el detector.
- Se rediseñó la demo: tema oscuro, medidor grande de bits, sello 200/401. Se arregló que se montara en pantallas chicas.
- Nombre confirmado (Cuentagotas), logo instalado y primera versión de la descripción pública.
- Se reiniciaron una vez las sesiones de los agentes para ahorrar tokens.

**06:00 a 08:00. Enjambre y rigor de la evaluación.**
- Cuenta global por clave entre varios agentes, con su demo.
- Demo interactiva con tres opciones de codificación.
- Set de prueba sellado: 180 ataques de familias nuevas más 90 sesiones benignas difíciles, con hash publicado en `redteam/SELLO.md`.
- Se encontró y corrigió un hueco real: el motor no veía fragmentos de cuatro caracteres en base64.
- Se corrigió la métrica de «ataque prevenido», que contaba como filtrada clave que ya había rotado.
- Matías se quedó sin tokens; su área (detector y evaluación) pasó a José Carlos.

**08:00 a 09:30. Investigación, auditoría y pitch.**
- Tres investigaciones: estado del arte, auditoría del código contra lo que afirmamos, y cómo se evalúa en las finales del tour.
- Dos afirmaciones nuestras eran falsas y se corrigieron en la descripción y el pitch: ya existen herramientas que juntan fragmentos entre llamadas.
- La auditoría encontró que la evaluación se perdía la mayoría de las rotaciones (al contarlas bien, validación subió de 90 % a 95 %) y un hueco de seguridad en la herramienta `git` del proxy. Los dos corregidos.
- Pitch rearmado: abre con la pregunta del propio track, lámina del enjambre, tabla comparativa con competidores y trece preguntas del jurado respondidas.
- `README.md` con una sección para quien evalúa (afirmación, archivo y comando), porque en el tour los jueces leyeron el repositorio con un modelo de lenguaje.
- Quedó en `main` el comando único de la evaluación final, probado en validación.

**Decisiones del líder en este turno:** escenario de hospitales; nombre Cuentagotas; el enjambre es objetivo del proyecto; adelantar el congelamiento y la evaluación final; las sesiones de los agentes no se reinician salvo que él lo indique.
