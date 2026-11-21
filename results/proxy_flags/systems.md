# Evaluación con las banderas del proxy · set `test`

Análisis aparte, con el detector congelado. Ataques prevenidos en cada variante:

| Sistema | Grabadas | Banderas del proxy | Banderas del proxy e inspección del push |
|---|---|---|---|
| ours | 180 de 180 | 120 de 180 | 120 de 180 |
| no_rotation | 30 de 180 | 0 de 180 | 0 de 180 |
| per_session | 180 de 180 | 120 de 180 | 120 de 180 |
| no_evidence | 40 de 180 | 10 de 180 | 10 de 180 |
| allowlist | 30 de 180 | 30 de 180 | 30 de 180 |
| detect_secrets | 0 de 180 | 0 de 180 | 0 de 180 |
| combined | 30 de 180 | 30 de 180 | 30 de 180 |
| budget | 70 de 180 | 40 de 180 | 40 de 180 |
| reassembly | 0 de 180 | 0 de 180 | 0 de 180 |
| taint_rule | 180 de 180 | 90 de 180 | 90 de 180 |

## Grabadas (las banderas del generador)

| Sistema | Falsas alarmas [IC] | Rot. benignas / 1.000 | Prevenidos [IC] | Prevenidos, cota pesimista | Mediana de bits | Mediana de rotaciones | Prev. A10 | Prev. A12 | Prev. A13 | Prev. A5 | Prev. A7 | Prev. A9 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ours | 0.0000 [0.0000, 0.0006] | 5.46 | 1.000 [0.980, 1.000] | 1.000 | 20.0 | 1.0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| no_rotation | 0.0000 [0.0000, 0.0006] | 0.00 | 0.167 [0.115, 0.229] | 0.167 | 160.0 | 0.0 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| per_session | 0.0000 [0.0000, 0.0006] | 5.46 | 1.000 [0.980, 1.000] | 1.000 | 20.0 | 1.0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| no_evidence | 0.0000 [0.0000, 0.0006] | 0.56 | 0.222 [0.164, 0.290] | 0.217 | 160.0 | 0.0 | 0.033 | 0.300 | 1.000 | 0.000 | 0.000 | 0.000 |
| allowlist | 0.0000 [0.0000, 0.0006] | 0.00 | 0.167 [0.115, 0.229] | 0.167 | 160.0 | 0.0 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| detect_secrets | 0.0219 [0.0184, 0.0260] | 0.00 | 0.000 [0.000, 0.020] | 0.000 | 160.0 | 0.0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| combined | 0.0219 [0.0184, 0.0260] | 0.00 | 0.167 [0.115, 0.229] | 0.167 | 160.0 | 0.0 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| budget | 0.0481 [0.0428, 0.0539] | 0.00 | 0.389 [0.317, 0.464] | 0.389 | 160.0 | 0.0 | 0.067 | 0.267 | 1.000 | 0.000 | 0.000 | 1.000 |
| reassembly | 0.0000 [0.0000, 0.0006] | 0.00 | 0.000 [0.000, 0.020] | 0.000 | 160.0 | 0.0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| taint_rule | 0.0000 [0.0000, 0.0006] | 4.20 | 1.000 [0.980, 1.000] | 1.000 | 22.0 | 1.0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

Qué es cada sistema:

- `ours`: Alicanto congelado; por unidad, un SharedLedger con el manifiesto completo y los secretos de la unidad, y un detector por sesión (la cuenta es por clave, compartida entre sesiones).
- `no_rotation`: Ablación: ours con rotation_enabled=False (ninguna regla rota; los bloqueos siguen).
- `per_session`: Ablación del enjambre: el detector congelado sin ledger, una cuenta por sesión.
- `no_evidence`: Ablación: ours sin modelo de evidencia (model=None): mismos parámetros y ledger; solo bits y reglas.
- `allowlist`: Línea de base: egress solo a dominios aprobados.
- `detect_secrets`: Línea de base: regex y entropía sobre los argumentos de cada sumidero.
- `combined`: Línea de base: bloquea si allowlist o detect_secrets bloquea (la de T3).
- `budget`: Réplica simplificada de un presupuesto acumulado de bits por sesión (Nimbus), sin CUSUM ni rotación; no es su código ni su producto.
- `reassembly`: Réplica simplificada del reensamblado por sesión (inspirada en Pipelock y AgentBrake), sin decodificar; no es su código ni su producto. Ver eval/baselines/reassembly.py.
- `taint_rule`: Línea de base: regla simple, «leyó un secreto (su valor completo en una salida) y esta llamada sale hacia un destino no confiable»: rota lo leído; nunca bloquea.

## Banderas del proxy

| Sistema | Falsas alarmas [IC] | Rot. benignas / 1.000 | Prevenidos [IC] | Prevenidos, cota pesimista | Mediana de bits | Mediana de rotaciones | Prev. A10 | Prev. A12 | Prev. A13 | Prev. A5 | Prev. A7 | Prev. A9 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ours | 0.0000 [0.0000, 0.0006] | 5.46 | 0.667 [0.593, 0.735] | 0.667 | 20.0 | 1.0 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 |
| no_rotation | 0.0000 [0.0000, 0.0006] | 0.00 | 0.000 [0.000, 0.020] | 0.000 | 160.0 | 0.0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| per_session | 0.0000 [0.0000, 0.0006] | 5.46 | 0.667 [0.593, 0.735] | 0.667 | 20.0 | 1.0 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 |
| no_evidence | 0.0000 [0.0000, 0.0006] | 0.56 | 0.056 [0.027, 0.100] | 0.056 | 160.0 | 0.0 | 0.033 | 0.300 | 0.000 | 0.000 | 0.000 | 0.000 |
| allowlist | 0.0000 [0.0000, 0.0006] | 0.00 | 0.167 [0.115, 0.229] | 0.167 | 160.0 | 0.0 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| detect_secrets | 0.0219 [0.0184, 0.0260] | 0.00 | 0.000 [0.000, 0.020] | 0.000 | 160.0 | 0.0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| combined | 0.0219 [0.0184, 0.0260] | 0.00 | 0.167 [0.115, 0.229] | 0.167 | 160.0 | 0.0 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| budget | 0.0481 [0.0428, 0.0539] | 0.00 | 0.222 [0.164, 0.290] | 0.222 | 160.0 | 0.0 | 0.067 | 0.267 | 0.000 | 0.000 | 0.000 | 1.000 |
| reassembly | 0.0000 [0.0000, 0.0006] | 0.00 | 0.000 [0.000, 0.020] | 0.000 | 160.0 | 0.0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| taint_rule | 0.0000 [0.0000, 0.0006] | 4.20 | 0.500 [0.425, 0.575] | 0.500 | 76.0 | 0.5 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 |

Qué es cada sistema:

- `ours`: Alicanto congelado; por unidad, un SharedLedger con el manifiesto completo y los secretos de la unidad, y un detector por sesión (la cuenta es por clave, compartida entre sesiones).
- `no_rotation`: Ablación: ours con rotation_enabled=False (ninguna regla rota; los bloqueos siguen).
- `per_session`: Ablación del enjambre: el detector congelado sin ledger, una cuenta por sesión.
- `no_evidence`: Ablación: ours sin modelo de evidencia (model=None): mismos parámetros y ledger; solo bits y reglas.
- `allowlist`: Línea de base: egress solo a dominios aprobados.
- `detect_secrets`: Línea de base: regex y entropía sobre los argumentos de cada sumidero.
- `combined`: Línea de base: bloquea si allowlist o detect_secrets bloquea (la de T3).
- `budget`: Réplica simplificada de un presupuesto acumulado de bits por sesión (Nimbus), sin CUSUM ni rotación; no es su código ni su producto.
- `reassembly`: Réplica simplificada del reensamblado por sesión (inspirada en Pipelock y AgentBrake), sin decodificar; no es su código ni su producto. Ver eval/baselines/reassembly.py.
- `taint_rule`: Línea de base: regla simple, «leyó un secreto (su valor completo en una salida) y esta llamada sale hacia un destino no confiable»: rota lo leído; nunca bloquea.

## Banderas del proxy e inspección del push

| Sistema | Falsas alarmas [IC] | Rot. benignas / 1.000 | Prevenidos [IC] | Prevenidos, cota pesimista | Mediana de bits | Mediana de rotaciones | Prev. A10 | Prev. A12 | Prev. A13 | Prev. A5 | Prev. A7 | Prev. A9 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ours | 0.0000 [0.0000, 0.0006] | 5.46 | 0.667 [0.593, 0.735] | 0.667 | 20.0 | 1.0 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 |
| no_rotation | 0.0000 [0.0000, 0.0006] | 0.00 | 0.000 [0.000, 0.020] | 0.000 | 160.0 | 0.0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| per_session | 0.0000 [0.0000, 0.0006] | 5.46 | 0.667 [0.593, 0.735] | 0.667 | 20.0 | 1.0 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 |
| no_evidence | 0.0000 [0.0000, 0.0006] | 0.56 | 0.056 [0.027, 0.100] | 0.056 | 160.0 | 0.0 | 0.033 | 0.300 | 0.000 | 0.000 | 0.000 | 0.000 |
| allowlist | 0.0000 [0.0000, 0.0006] | 0.00 | 0.167 [0.115, 0.229] | 0.167 | 160.0 | 0.0 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| detect_secrets | 0.0219 [0.0184, 0.0260] | 0.00 | 0.000 [0.000, 0.020] | 0.000 | 160.0 | 0.0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| combined | 0.0219 [0.0184, 0.0260] | 0.00 | 0.167 [0.115, 0.229] | 0.167 | 160.0 | 0.0 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| budget | 0.0481 [0.0428, 0.0539] | 0.00 | 0.222 [0.164, 0.290] | 0.222 | 160.0 | 0.0 | 0.067 | 0.267 | 0.000 | 0.000 | 0.000 | 1.000 |
| reassembly | 0.0000 [0.0000, 0.0006] | 0.00 | 0.000 [0.000, 0.020] | 0.000 | 160.0 | 0.0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| taint_rule | 0.0000 [0.0000, 0.0006] | 4.20 | 0.500 [0.425, 0.575] | 0.500 | 76.0 | 0.5 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 |

Qué es cada sistema:

- `ours`: Alicanto congelado; por unidad, un SharedLedger con el manifiesto completo y los secretos de la unidad, y un detector por sesión (la cuenta es por clave, compartida entre sesiones).
- `no_rotation`: Ablación: ours con rotation_enabled=False (ninguna regla rota; los bloqueos siguen).
- `per_session`: Ablación del enjambre: el detector congelado sin ledger, una cuenta por sesión.
- `no_evidence`: Ablación: ours sin modelo de evidencia (model=None): mismos parámetros y ledger; solo bits y reglas.
- `allowlist`: Línea de base: egress solo a dominios aprobados.
- `detect_secrets`: Línea de base: regex y entropía sobre los argumentos de cada sumidero.
- `combined`: Línea de base: bloquea si allowlist o detect_secrets bloquea (la de T3).
- `budget`: Réplica simplificada de un presupuesto acumulado de bits por sesión (Nimbus), sin CUSUM ni rotación; no es su código ni su producto.
- `reassembly`: Réplica simplificada del reensamblado por sesión (inspirada en Pipelock y AgentBrake), sin decodificar; no es su código ni su producto. Ver eval/baselines/reassembly.py.
- `taint_rule`: Línea de base: regla simple, «leyó un secreto (su valor completo en una salida) y esta llamada sale hacia un destino no confiable»: rota lo leído; nunca bloquea.
