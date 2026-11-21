| Sistema | Falsas alarmas [IC] | Rot. benignas / 1.000 | Prevenidos [IC] | Prevenidos, cota pesimista | Mediana de bits | Mediana de rotaciones | Prev. A1 | Prev. A2 | Prev. A3 | Prev. A4 | Prev. A5′ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ours | 0.0000 [0.0000, 0.0031] | 0.94 | 0.950 [0.877, 0.986] | 0.950 | 16.0 | 1.0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.600 |
| no_rotation | 0.0000 [0.0000, 0.0031] | 0.00 | 0.525 [0.410, 0.638] | 0.525 | 96.0 | 0.0 | 1.000 | 1.000 | 0.250 | 0.360 | 0.300 |
| per_session | 0.0000 [0.0000, 0.0031] | 0.94 | 0.950 [0.877, 0.986] | 0.950 | 16.0 | 1.0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.600 |
| allowlist | 0.0000 [0.0000, 0.0031] | 0.00 | 0.750 [0.641, 0.840] | 0.750 | 0.0 | 0.0 | 0.800 | 0.600 | 0.800 | 0.800 | 0.700 |
| detect_secrets | 0.0000 [0.0000, 0.0031] | 0.00 | 0.225 [0.139, 0.332] | 0.225 | 128.0 | 0.0 | 0.200 | 0.133 | 0.250 | 0.240 | 0.300 |
| combined | 0.0000 [0.0000, 0.0031] | 0.00 | 0.750 [0.641, 0.840] | 0.750 | 0.0 | 0.0 | 0.800 | 0.600 | 0.800 | 0.800 | 0.700 |
| budget | 0.0193 [0.0122, 0.0288] | 0.00 | 0.938 [0.860, 0.979] | 0.938 | 72.0 | 0.0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.500 |
| reassembly | 0.0000 [0.0000, 0.0031] | 0.00 | 0.588 [0.472, 0.696] | 0.588 | 80.0 | 0.0 | 1.000 | 1.000 | 0.650 | 0.240 | 0.300 |

Qué es cada sistema:

- `ours`: Cuentagotas congelado; por unidad, un SharedLedger con el manifiesto completo y los secretos de la unidad, y un detector por sesión (la cuenta es por clave, compartida entre sesiones).
- `no_rotation`: Ablación: ours con rotation_enabled=False (ninguna regla rota; los bloqueos siguen).
- `per_session`: Ablación del enjambre: el detector congelado sin ledger, una cuenta por sesión.
- `allowlist`: Línea de base: egress solo a dominios aprobados.
- `detect_secrets`: Línea de base: regex y entropía sobre los argumentos de cada sumidero.
- `combined`: Línea de base: bloquea si allowlist o detect_secrets bloquea (la de T3).
- `budget`: Réplica simplificada de un presupuesto acumulado de bits por sesión (Nimbus), sin CUSUM ni rotación; no es su código ni su producto.
- `reassembly`: Réplica simplificada del reensamblado por sesión (inspirada en Pipelock y AgentBrake), sin decodificar; no es su código ni su producto. Ver eval/baselines/reassembly.py.
