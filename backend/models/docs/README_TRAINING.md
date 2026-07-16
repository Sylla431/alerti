# Guide d'Entraînement Simplifié

## Structure du package `models/`

```
models/
  predictors/   # classes LSTM / CNN / Hybrid
  trainers/     # scripts d'entraînement
  artifacts/    # poids .h5 et scalers .pkl
  docs/         # cette documentation
```

## Entraînement rapide (débutants)

```bash
# Depuis la racine du projet
source venv/bin/activate
cd backend
python -m models.trainers.model_trainer
# (équivalent rétrocompatible : python -m models.model_trainer)
```

**Temps estimé** : 15-20 minutes

## Ce qui va se passer

1. Génération de données d'entraînement synthétiques
2. Entraînement du modèle LSTM (5-10 min)
3. Entraînement du modèle CNN (10-15 min)
4. Entraînement du modèle Hybrid (2-3 min)
5. Sauvegarde automatique des modèles

## Fichiers créés

Après l'entraînement, vous aurez :

- `backend/models/artifacts/lstm_model.h5`
- `backend/models/artifacts/cnn_model.h5`
- `backend/models/artifacts/fusion_model.h5`
- `backend/models/artifacts/lstm_scaler.pkl`

## Variantes Bamako

```bash
# Données pluie + features étendues (29 features)
python -m models.trainers.model_trainer_bamako

# Variante pluie-seule (5 features, risque régional)
python data/prepare_bamako_rainfall_only.py
python -m models.trainers.model_trainer_bamako_rainfall
```

## Personnaliser l'entraînement

Éditez `trainers/model_trainer.py` pour changer `n_samples`, `epochs`, `batch_size`.

## Dépannage

**Erreur de mémoire** : réduisez `n_samples` ou `batch_size`  
**Trop long** : réduisez `epochs` ou `n_samples`  
**Modèle pas bon** : normal avec données synthétiques — utilisez de vraies données pour améliorer
