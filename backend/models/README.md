# Models package

```
models/
├── predictors/   # LSTM / CNN / Hybrid (code)
├── trainers/     # scripts d'entraînement
├── artifacts/    # poids .h5 + scalers .pkl
├── docs/         # guides d'entraînement
└── *.py          # shims rétrocompatibles (from models.lstm_model_bamako …)
```

Voir [docs/README_TRAINING.md](docs/README_TRAINING.md).

## Imports recommandés

```python
from models.predictors.lstm_model_bamako import LSTMPredictorBamako
from models.predictors.hybrid_model import HybridFloodPredictor
```

## Entraînement

```bash
cd backend
python -m models.trainers.model_trainer_bamako
python -m models.trainers.model_trainer_bamako_rainfall
```
