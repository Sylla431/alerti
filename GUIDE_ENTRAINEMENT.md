# 🎓 Guide d'Entraînement des Modèles IA - Pour Débutants

## 📚 Comprendre les Modèles

Votre système utilise **3 modèles** :

1. **LSTM** : Prédit les inondations basé sur les données météo (précipitations, température, etc.)
2. **CNN** : Détecte les inondations sur les images satellites
3. **Hybrid** : Combine les deux modèles pour une meilleure précision

## 🚀 Méthode Simple : Entraînement avec Données Synthétiques

### Étape 1 : Activer l'environnement virtuel

```bash
cd /Users/macpro/IdeaProjects/alerti
source venv/bin/activate
```

### Étape 2 : Lancer l'entraînement automatique

```bash
cd backend
python -m models.model_trainer
```

**C'est tout !** Le script va :
- ✅ Générer automatiquement des données d'entraînement (1000 exemples pour LSTM, 500 pour CNN)
- ✅ Entraîner les 3 modèles
- ✅ Sauvegarder les modèles dans `backend/models/`

### Étape 3 : Vérifier les résultats

Les modèles entraînés seront sauvegardés dans :
- `backend/models/lstm_model.h5`
- `backend/models/cnn_model.h5`
- `backend/models/fusion_model.h5`

## 📊 Ce qui se passe pendant l'entraînement

### Pour le modèle LSTM :
- **Données d'entrée** : 30 jours de données météo (précipitations, température, humidité, etc.)
- **Données de sortie** : Probabilité d'inondation (0 à 1)
- **Durée** : ~5-10 minutes
- **Époques** : 50 (le modèle apprend 50 fois sur les mêmes données)

### Pour le modèle CNN :
- **Données d'entrée** : Images satellites (256x256 pixels)
- **Données de sortie** : Masque des zones inondées
- **Durée** : ~10-15 minutes
- **Époques** : 30

### Pour le modèle Hybrid :
- **Données d'entrée** : Prédictions combinées LSTM + CNN
- **Durée** : ~2-3 minutes
- **Époques** : 50

## 🎯 Paramètres à Ajuster (Optionnel)

Si vous voulez améliorer les modèles, vous pouvez modifier `backend/models/model_trainer.py` :

```python
# Plus de données = meilleure précision (mais plus long)
X_train, y_train = generate_synthetic_training_data_lstm(n_samples=2000)  # Au lieu de 1000

# Plus d'époques = meilleur apprentissage (mais plus long)
history = lstm_model.train(..., epochs=100)  # Au lieu de 50
```

## 📈 Améliorer avec de Vraies Données (Avancé)

### Option 1 : Utiliser des données historiques réelles

1. **Télécharger des données CHIRPS** (précipitations historiques)
2. **Télécharger des images Sentinel** (images satellites)
3. **Créer un fichier CSV** avec :
   - Colonnes : date, précipitations, température, humidité, inondation (0 ou 1)
   - Lignes : un exemple par jour

### Option 2 : Utiliser des données publiques

- **CHIRPS** : https://data.chc.ucsb.edu/products/CHIRPS-2.0/
- **Sentinel Hub** : https://www.sentinel-hub.com/
- **Digital Earth Africa** : https://www.digitalearthafrica.org/

## ⚠️ Problèmes Courants

### Erreur : "Out of memory"
**Solution** : Réduire le nombre d'exemples ou la taille des images
```python
n_samples=500  # Au lieu de 1000
```

### Erreur : "Model not improving"
**Solution** : Normal au début ! Les données synthétiques sont limitées. Avec de vraies données, ça s'améliorera.

### L'entraînement est trop long
**Solution** : Réduire les époques
```python
epochs=20  # Au lieu de 50
```

## 🎓 Concepts Importants pour Débutants

### Qu'est-ce qu'une "époque" (epoch) ?
Une époque = le modèle voit toutes les données d'entraînement **une fois**. Plus d'époques = plus d'apprentissage, mais attention au surapprentissage !

### Qu'est-ce qu'un "batch" ?
Un batch = nombre d'exemples traités en même temps. Plus grand = plus rapide mais nécessite plus de mémoire.

### Qu'est-ce que la "validation" ?
Les données de validation servent à vérifier que le modèle généralise bien (ne mémorise pas juste les données d'entraînement).

## 📝 Résumé Rapide

```bash
# 1. Activer l'environnement
source venv/bin/activate

# 2. Lancer l'entraînement
cd backend
python -m models.model_trainer

# 3. Attendre la fin (10-20 minutes)
# 4. Les modèles sont prêts !
```

## 🔄 Ré-entraîner les Modèles

Si vous voulez ré-entraîner avec de nouvelles données :

```bash
# Supprimer les anciens modèles (optionnel)
rm backend/models/*.h5

# Relancer l'entraînement
python -m models.model_trainer
```

## 💡 Astuce pour Débutants

**Commencez simple** :
1. Utilisez d'abord les données synthétiques (déjà configurées)
2. Testez les prédictions
3. Si ça fonctionne, vous pourrez améliorer avec de vraies données plus tard

Les modèles fonctionnent déjà avec des données simulées, donc vous pouvez commencer à utiliser le système tout de suite !
