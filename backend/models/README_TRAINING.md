# Guide d'Entraînement Simplifié

## 🎯 Entraînement Rapide (Recommandé pour Débutants)

### Commande Simple

```bash
# Depuis la racine du projet
source venv/bin/activate
cd backend
python -m models.model_trainer
```

**Temps estimé** : 15-20 minutes

## 📋 Ce qui va se passer

1. ✅ Génération de données d'entraînement synthétiques
2. ✅ Entraînement du modèle LSTM (5-10 min)
3. ✅ Entraînement du modèle CNN (10-15 min)
4. ✅ Entraînement du modèle Hybrid (2-3 min)
5. ✅ Sauvegarde automatique des modèles

## 📁 Fichiers Créés

Après l'entraînement, vous aurez :
- `backend/models/lstm_model.h5` - Modèle LSTM entraîné
- `backend/models/cnn_model.h5` - Modèle CNN entraîné
- `backend/models/fusion_model.h5` - Modèle de fusion
- `backend/models/lstm_scaler.pkl` - Normalisation des données

## ⚙️ Personnaliser l'Entraînement

Éditez `model_trainer.py` pour changer :

```python
# Nombre d'exemples (plus = meilleur mais plus long)
n_samples=2000  # Ligne 98

# Nombre d'époques (plus = meilleur apprentissage)
epochs=100  # Ligne 115

# Taille du batch (plus grand = plus rapide)
batch_size=64  # Ligne 116
```

## 🐛 Dépannage

**Erreur de mémoire** : Réduisez `n_samples` ou `batch_size`
**Trop long** : Réduisez `epochs` ou `n_samples`
**Modèle pas bon** : Normal avec données synthétiques ! Utilisez de vraies données pour améliorer.

