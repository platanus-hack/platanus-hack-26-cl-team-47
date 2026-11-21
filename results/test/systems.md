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

Qué es cada sistema:

- `ours`: Cuentagotas congelado; por unidad, un SharedLedger con el manifiesto completo y los secretos de la unidad, y un detector por sesión (la cuenta es por clave, compartida entre sesiones).
- `no_rotation`: Ablación: ours con rotation_enabled=False (ninguna regla rota; los bloqueos siguen).
- `per_session`: Ablación del enjambre: el detector congelado sin ledger, una cuenta por sesión.
- `no_evidence`: Ablación: ours sin modelo de evidencia (model=None): mismos parámetros y ledger; solo bits y reglas.
- `allowlist`: Línea de base: egress solo a dominios aprobados.
- `detect_secrets`: Línea de base: regex y entropía sobre los argumentos de cada sumidero.
- `combined`: Línea de base: bloquea si allowlist o detect_secrets bloquea (la de T3).
- `budget`: Réplica simplificada de un presupuesto acumulado de bits por sesión (Nimbus), sin CUSUM ni rotación; no es su código ni su producto.
- `reassembly`: Réplica simplificada del reensamblado por sesión (inspirada en Pipelock y AgentBrake), sin decodificar; no es su código ni su producto. Ver eval/baselines/reassembly.py.
