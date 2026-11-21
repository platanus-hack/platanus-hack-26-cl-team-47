# models/

Modelos de evidencia ajustados con `python -m eval.fit` (paso 8b).

| Archivo | Qué es |
|---|---|
| `model.json` | `FeatureModel.to_dict()`: por feature, los bordes de las cajas y log(p̂₁/p̂₀) por caja, más `n_bins`, `B` y `alpha`. Lo carga `engine.detector:make_decide_with_model`. |
| `model.report.json` | Informe del ajuste: `n_benign_calls`, `n_attack_calls`, `d0` (deriva: el negativo de la media de ℓ en las benignas), `v` (varianza de ℓ en las benignas), `clip_fraction` (fracción de benignas con \|ℓ\| = B) y `mean_llr_attack`. |

| `search/rows.json` | Una fila por combinación de la grilla de `python -m eval.search` (750 por defecto): `b`, `b_rot`, `lambda_rot`, `T` y las métricas de validación (`false_alarm_rate`, `benign_rotations_per_1000`, `prevented_rate`, `median_max_bits_true`). |
| `search/pareto.json` | Las filas no dominadas en falsas alarmas, rotaciones benignas y mediana de bits (las tres se minimizan). |
| `search/frozen.json` | La configuración elegida (Neyman–Pearson: falsas alarmas ≤ 1e-3 y rotaciones benignas ≤ 5 por 1.000; entre esas, menor mediana de bits) con el SHA-256 del modelo, el de las carpetas de datos, la fecha y un `hash` de todo eso. Solo existe si alguna combinación cumple las metas. |

Búsqueda (solo usa las sesiones de validación):

```
python -m eval.search --benign data/benign/sessions --attack <sesiones de ataque> \
    [--labels <labels.jsonl>] [--secrets <secrets.jsonl>] --model models/model.json --out models/search
```

Reglas:

- El `model.json` que se versiona se ajusta con el set de entrenamiento del equipo rojo (#9) y el fondo benigno de `data/benign/sessions`. **No se versionan modelos ajustados con ataques provisionales.**
- Comando:
  ```
  python -m eval.fit --benign data/benign/sessions --attack <sesiones de ataque> \
      --labels <labels.jsonl> --secrets <secrets.jsonl> --out models/model.json
  ```
- La configuración se congela con su hash en H20 (paso 13). Cada cambio queda anotado en la bitácora del detector.
