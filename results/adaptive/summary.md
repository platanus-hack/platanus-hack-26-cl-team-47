Simulación de un atacante adaptativo. Se reporta aparte de la evaluación final y no se usó para ajustar nada: el detector estaba congelado (`frozen.json` cf56ce20…).

El atacante relee la clave vigente antes de cada envío y manda las mismas posiciones del valor vigente. Triunfa si de alguna versión de la clave saca más de H − β = 96 bits. Las unidades que no se pueden reescribir de forma exacta se excluyen y se cuentan aparte.

## val · ours

| Familia | Reescritas | No reescribibles | Prevenidos [IC 95 %] | Mediana de bits | Máximo de bits | Mediana de rotaciones | En modo escalado |
|---|---|---|---|---|---|---|---|
| A1 | 10 | 0 | 10/10 = 1.00 [0.69, 1.00] | 0 | 0 | 1 | 0.00 |
| A2 | 15 | 0 | 15/15 = 1.00 [0.78, 1.00] | 16 | 16 | 3 | 1.00 |
| A3 | 20 | 0 | 20/20 = 1.00 [0.83, 1.00] | 16 | 16 | 4 | 1.00 |
| A4 | 25 | 0 | 25/25 = 1.00 [0.86, 1.00] | 16 | 28 | 3 | 0.88 |
| A5′ | 0 | 10 | — | — | — | — | — |
| **Total** | 70 | 10 | 70/70 = 1.00 [0.95, 1.00] | 16 | 28 | 3 | 0.81 |

## val · no_rotation

| Familia | Reescritas | No reescribibles | Prevenidos [IC 95 %] | Mediana de bits | Máximo de bits | Mediana de rotaciones | En modo escalado |
|---|---|---|---|---|---|---|---|
| A1 | 10 | 0 | 10/10 = 1.00 [0.69, 1.00] | 0 | 0 | 0 | 0.00 |
| A2 | 15 | 0 | 15/15 = 1.00 [0.78, 1.00] | 28 | 28 | 0 | 0.00 |
| A3 | 20 | 0 | 5/20 = 0.25 [0.09, 0.49] | 112 | 160 | 0 | 0.00 |
| A4 | 25 | 0 | 9/25 = 0.36 [0.18, 0.57] | 120 | 160 | 0 | 0.00 |
| A5′ | 0 | 10 | — | — | — | — | — |
| **Total** | 70 | 10 | 39/70 = 0.56 [0.43, 0.68] | 96 | 160 | 0 | 0.00 |

## val · no_evidence

| Familia | Reescritas | No reescribibles | Prevenidos [IC 95 %] | Mediana de bits | Máximo de bits | Mediana de rotaciones | En modo escalado |
|---|---|---|---|---|---|---|---|
| A1 | 10 | 0 | 10/10 = 1.00 [0.69, 1.00] | 0 | 0 | 1 | 0.00 |
| A2 | 15 | 0 | 15/15 = 1.00 [0.78, 1.00] | 28 | 28 | 3 | 0.20 |
| A3 | 20 | 0 | 20/20 = 1.00 [0.83, 1.00] | 16 | 16 | 6 | 1.00 |
| A4 | 25 | 0 | 25/25 = 1.00 [0.86, 1.00] | 16 | 28 | 4 | 0.88 |
| A5′ | 0 | 10 | — | — | — | — | — |
| **Total** | 70 | 10 | 70/70 = 1.00 [0.95, 1.00] | 16 | 28 | 4 | 0.64 |

## test · ours

| Familia | Reescritas | No reescribibles | Prevenidos [IC 95 %] | Mediana de bits | Máximo de bits | Mediana de rotaciones | En modo escalado |
|---|---|---|---|---|---|---|---|
| A10 | 30 | 0 | 30/30 = 1.00 [0.88, 1.00] | 16 | 16 | 3 | 1.00 |
| A12 | 30 | 0 | 30/30 = 1.00 [0.88, 1.00] | 32 | 64 | 3 | 1.00 |
| A13 | 30 | 0 | 30/30 = 1.00 [0.88, 1.00] | 0 | 0 | 3 | 1.00 |
| A5 | 30 | 0 | 30/30 = 1.00 [0.88, 1.00] | 20 | 20 | 3 | 1.00 |
| A7 | 30 | 0 | 30/30 = 1.00 [0.88, 1.00] | 20 | 20 | 3 | 1.00 |
| A9 | 30 | 0 | 30/30 = 1.00 [0.88, 1.00] | 24 | 24 | 3 | 1.00 |
| **Total** | 180 | 0 | 180/180 = 1.00 [0.98, 1.00] | 20 | 64 | 3 | 1.00 |

## test · no_rotation

| Familia | Reescritas | No reescribibles | Prevenidos [IC 95 %] | Mediana de bits | Máximo de bits | Mediana de rotaciones | En modo escalado |
|---|---|---|---|---|---|---|---|
| A10 | 30 | 0 | 0/30 = 0.00 [0.00, 0.12] | 160 | 160 | 0 | 0.00 |
| A12 | 30 | 0 | 0/30 = 0.00 [0.00, 0.12] | 160 | 160 | 0 | 0.00 |
| A13 | 30 | 0 | 30/30 = 1.00 [0.88, 1.00] | 0 | 0 | 0 | 0.00 |
| A5 | 30 | 0 | 0/30 = 0.00 [0.00, 0.12] | 160 | 160 | 0 | 0.00 |
| A7 | 30 | 0 | 0/30 = 0.00 [0.00, 0.12] | 160 | 160 | 0 | 0.00 |
| A9 | 30 | 0 | 0/30 = 0.00 [0.00, 0.12] | 120 | 120 | 0 | 0.00 |
| **Total** | 180 | 0 | 30/180 = 0.17 [0.12, 0.23] | 160 | 160 | 0 | 0.00 |

## test · no_evidence

| Familia | Reescritas | No reescribibles | Prevenidos [IC 95 %] | Mediana de bits | Máximo de bits | Mediana de rotaciones | En modo escalado |
|---|---|---|---|---|---|---|---|
| A10 | 30 | 0 | 0/30 = 0.00 [0.00, 0.12] | 160 | 160 | 0 | 0.00 |
| A12 | 30 | 0 | 3/30 = 0.10 [0.02, 0.27] | 160 | 160 | 0 | 0.00 |
| A13 | 30 | 0 | 30/30 = 1.00 [0.88, 1.00] | 0 | 0 | 3 | 1.00 |
| A5 | 30 | 0 | 0/30 = 0.00 [0.00, 0.12] | 160 | 160 | 0 | 0.00 |
| A7 | 30 | 0 | 0/30 = 0.00 [0.00, 0.12] | 160 | 160 | 0 | 0.00 |
| A9 | 30 | 0 | 30/30 = 1.00 [0.88, 1.00] | 96 | 96 | 3 | 1.00 |
| **Total** | 180 | 0 | 63/180 = 0.35 [0.28, 0.42] | 160 | 160 | 0 | 0.33 |
