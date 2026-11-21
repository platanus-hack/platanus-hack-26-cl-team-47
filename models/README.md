# models/

Modelos de evidencia ajustados con `python -m eval.fit` (paso 8b).

| Archivo | Qué es |
|---|---|
| `model.json` | `FeatureModel.to_dict()`: por feature, los bordes de las cajas y log(p̂₁/p̂₀) por caja, más `n_bins`, `B` y `alpha`. Lo carga `engine.detector:make_decide_with_model`. |
| `model.report.json` | Informe del ajuste: `n_benign_calls`, `n_attack_calls`, `d0` (deriva: el negativo de la media de ℓ en las benignas), `v` (varianza de ℓ en las benignas), `clip_fraction` (fracción de benignas con \|ℓ\| = B) y `mean_llr_attack`. |

Reglas:

- El `model.json` que se versiona se ajusta con el set de entrenamiento del equipo rojo (#9) y el fondo benigno de `data/benign/sessions`. **No se versionan modelos ajustados con ataques provisionales.**
- Comando:
  ```
  python -m eval.fit --benign data/benign/sessions --attack <sesiones de ataque> \
      --labels <labels.jsonl> --secrets <secrets.jsonl> --out models/model.json
  ```
- La configuración se congela con su hash en H20 (paso 13). Cada cambio queda anotado en la bitácora del detector.
