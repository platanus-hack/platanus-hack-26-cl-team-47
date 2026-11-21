# Escenario de la demo: hospital ficticio

Decisión del líder del 21 de noviembre de 2026 (H5). Reemplaza la sección «Escenario pendiente» de `docs/PLAN.md`. Los datos de contexto vienen de una investigación web del mismo día: lo marcado **[no verificado]** no se pudo confirmar abriendo la fuente y **no va en una lámina** hasta que una persona la abra.

## La historia en tres frases

El equipo de TI del **Hospital Regional Tres Cóndores** (ficticio) mantiene `servicio-reservas`, el servicio que agenda horas médicas y consulta la ficha clínica electrónica. Usan un agente de IA de programación para resolver issues del repositorio. Un issue con una instrucción plantada hace que el agente saque, de a pocos caracteres, la clave con la que el servicio entra a la ficha clínica.

- Sin protección: el atacante reconstruye la clave y la API de fichas le responde 200.
- Con el medidor: la clave rota a mitad del goteo y el atacante recibe 401.

El hospital, los pacientes y las claves son inventados. El nombre se comprobó con una búsqueda web y no corresponde a ningún hospital o clínica que apareciera; no es una consulta al registro de prestadores.

## Qué cambia y qué no

El escenario es una **capa de presentación**. No se renombra nada de lo que usan los tests, los servicios o los datos de entrenamiento.

| No cambia | Motivo |
|---|---|
| Hosts `.test` (`api.empresa.test`, `vault.test`, `attacker.test`…) | Están en `contracts/hosts.json` y en todos los registros |
| `SECRET_1`…`SECRET_n` y sus `key` (`API_EMPRESA_KEY`…) | Los usan tests de `engine/`, `eval/` y `services/` |
| `demo/secrets_manifest.json` y el contenido de `demo/repo/` | `data/benign/` y los fixtures se grabaron con ellos |
| Datos de `redteam/` y `data/` | El entrenamiento no depende del rubro |

Lo que cambia: los textos que ve el jurado (pantalla dividida, informe de incidente, portada, láminas y guion). Todos salen de un solo archivo, `demo/scenario.json`.

## Nombres para mostrar

`demo/scenario.json` (contenido exacto):

```json
{
  "version": 1,
  "organization": "Hospital Regional Tres Cóndores",
  "fictional_note": "Hospital, pacientes y claves ficticios.",
  "system": "Agenda de horas y ficha clínica electrónica",
  "team": "Equipo de TI del hospital",
  "hosts": {
    "api.empresa.test": "API de ficha clínica",
    "vault.test": "Gestor de secretos del hospital",
    "attacker.test": "Servidor del atacante",
    "github.test": "Repositorio del equipo de TI",
    "web.test": "Página web externa"
  },
  "secrets": {
    "SECRET_1": "Clave de la API de ficha clínica",
    "SECRET_2": "Contraseña de la base de fichas",
    "SECRET_3": "Llave de firma de recetas electrónicas",
    "SECRET_4": "Secreto del webhook de laboratorio",
    "SECRET_5": "Contraseña del correo a pacientes"
  }
}
```

Regla de uso: donde la pantalla hoy muestra un host o un `SECRET_n`, muestra la etiqueta y deja el identificador técnico al lado en chico, por ejemplo «Clave de la API de ficha clínica (`SECRET_1`)». Si un identificador no está en el archivo, se muestra tal cual. Los registros no se tocan.

## Datos para el pitch

Usar solo las filas «verificado». Una persona abre la fuente antes de la entrega.

| Dato | Estado | Fuente |
|---|---|---|
| Ley 21.663: los prestadores de servicios esenciales reportan a la ANCI una alerta temprana en 3 horas, un segundo reporte en 72 horas y un informe final en 15 días corridos. Rige desde el 1 de marzo de 2025. | Verificado en fuente secundaria (estudio de abogados) | https://www.cariola.cl/app/uploads/2025/03/Alerta-Legal_04.03.2025.pdf |
| No reportar es infracción grave: hasta 10.000 UTM. | Verificado en la misma fuente | Ídem |
| Ley 20.584, art. 12: toda la información de la ficha clínica es dato sensible. | Verificado | https://www.suseso.gob.cl/612/w3-propertyvalue-130626.html |
| Ley 21.719 (datos personales): multas de hasta 20.000 UTM. | Verificado vía resumen | https://www.carey.cl/publican-la-ley-n-21-719-que-modifica-la-ley-n-19-628-sobre-proteccion-de-la-vida-privada-en-el-diario-oficial |
| Fecha de vigencia de la Ley 21.719 | **No usar.** Era el 1 de diciembre de 2026 y el Congreso aprobó moverla al 15 de octubre de 2027; falta la publicación. | https://www.az.cl/?p=264501 |
| Change Healthcare (EE. UU., febrero de 2024): credenciales robadas en un portal sin segundo factor; 192,7 millones de personas afectadas. | Vector verificado; cifras vía resumen | https://techcrunch.com/2024/04/30/uhg-change-healthcare-ransomware-compromised-credentials-mfa |
| Costo promedio de una brecha en salud: USD 6,64 millones (IBM, informe 2026), el más alto entre industrias. | Vía prensa; otra nota dice 6,4. Abrir el informe de IBM antes de usar. | https://www.hipaajournal.com/2026-cost-data-breach-study-ibm/ |
| Encuesta Paubox (julio de 2026, 151 líderes de salud que ya usan asistentes de código): 79 % usa servidores MCP. | Fuente única y de un proveedor; decirlo así | https://www.paubox.com/research/2026-benchmark-building-with-ai-in-healthcare |

Incidentes chilenos recientes en salud (Hospital Clínico de la Universidad de Chile en noviembre de 2026, Clínica Dávila en diciembre de 2025, Instituto de Salud Pública en junio de 2025): ocurrieron según la prensa, pero **en ninguno se publicó el vector**. Se pueden nombrar como contexto («los hospitales chilenos ya son blanco») y nunca como casos de claves filtradas por un agente. No nombrar a un hospital real como ejemplo de nuestra demo.

## Frase del escenario para la lámina 3 (borrador)

«Un hospital tiene 3 horas para avisar a la ANCI de un incidente. Su equipo de TI ya programa con agentes de IA, y las claves de la ficha clínica están en el mismo repositorio que el agente lee.»
