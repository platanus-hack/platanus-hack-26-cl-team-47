# Cuentagotas

**Mide cuántos bits de cada clave ya filtró tu agente de IA, y la rota antes de que el atacante la complete.**

## El problema

Los agentes de IA que programan leen el repositorio completo, incluidos el `.env` y los archivos de configuración con claves. Un issue o una página web con una instrucción escondida puede convencer al agente de sacar una clave hacia afuera.

Las defensas actuales buscan el secreto **completo** en cada mensaje. Un atacante paciente lo saca de a cuatro caracteres por llamada, separados por decenas de llamadas normales, o codificado en base64. Cada mensaje por separado se ve inocente.

## Qué hace Cuentagotas

Es un proxy que se pone entre el agente y sus herramientas (lectura de archivos, HTTP, git, issues). No modifica el agente y no usa un LLM para decidir.

En cada llamada:

1. **Mide.** Cuenta cuántos bits de cada secreto ya salieron hacia afuera, sumando fragmentos a lo largo de toda la sesión, también si van codificados (base64, hexadecimal, URL, ROT13, invertidos o separados).
2. **Acumula evidencia.** Sigue de dónde viene cada dato (qué archivo se leyó, qué contenido no confiable influyó) y acumula evidencia de ataque con un detector de cambio de régimen (CUSUM).
3. **Actúa.** Permite, bloquea o **rota la clave** en el gestor de secretos. Lo que el atacante juntó de la clave vieja deja de servir.

## La demo

El mismo ataque corre dos veces contra el repositorio del servicio de agenda y ficha clínica de un hospital ficticio (hospital, pacientes y claves son inventados):

| | Sin protección | Con Cuentagotas |
|---|---|---|
| Qué pasa | El atacante junta la clave de a 4 caracteres | La clave rota a mitad del goteo |
| Bits de la clave vigente que obtiene | 160 de 160 | 0 de 160 |
| Respuesta de la API de fichas | **200** | **401** |

Los bits que obtuvo el atacante los cuenta el servidor del atacante, no el detector: son dos registros independientes.

## Cómo está hecho

- **Proxy MCP** en Python con seis herramientas; todas las llamadas del agente pasan por él y quedan en un registro de eventos.
- **Motor de bits**: decodificadores encadenados y conteo de posiciones del secreto reveladas, con pruebas por propiedades.
- **Grafos**: un grafo de archivos por sensibilidad y un grafo de llamadas que sigue el contenido de una llamada a otra y explica cada decisión.
- **Servicios simulados** con FastAPI: gestor de secretos con rotación, API protegida, servidor del atacante, y GitHub y web de prueba. Todo corre en una red aislada, con nombres `.test` y sin salida a internet.
- **Evaluación**: arnés de reproducción, líneas de base (lista de destinos permitidos y detect-secrets) y pruebas de hipótesis con intervalos.

## Límites, dicho con honestidad

- Mide una **cota inferior**: solo ve lo que pasa por el proxy y las codificaciones que sabe decodificar.
- La rotación limita el daño; no impide que el agente intente la fuga.
- Hoy la cuenta se lleva por sesión de un agente.

## Equipo

team-47 · Platanus Hack 26 · track AI Security
