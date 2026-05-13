# 📊 Guide de Collecte et Préparation des Données Réelles

Ce guide explique comment télécharger et préparer des données réelles pour entraîner les modèles de prédiction d'inondation.

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Étape 1 : Télécharger les données CHIRPS](#étape-1--télécharger-les-données-chirps)
4. [Étape 2 : Obtenir les images satellites](#étape-2--obtenir-les-images-satellites)
5. [Étape 3 : Préparer les données d'entraînement](#étape-3--préparer-les-données-dentraînement)
6. [Étape 4 : Entraîner les modèles](#étape-4--entraîner-les-modèles)
7. [Sources de données alternatives](#sources-de-données-alternatives)
8. [Problèmes courants](#problèmes-courants)

---

## 🎯 Vue d'ensemble

Le système nécessite **2 types de données** :

1. **Données météorologiques** (précipitations, température, humidité, etc.)
2. **Images satellites** (pour détecter les zones inondées)

### Structure des Dossiers

```
backend/
├── data/
│   ├── raw/                          # Données brutes téléchargées
│   │   ├── chirps/                   # Fichiers TIFF CHIRPS
│   │   └── sentinel/                 # Images Sentinel
│   ├── training/                     # Données préparées pour l'entraînement
│   │   ├── lstm/                     # Séquences pour LSTM
│   │   │   ├── X_train.npy
│   │   │   ├── y_train.npy
│   │   │   ├── X_val.npy
│   │   │   └── y_val.npy
│   │   └── cnn/                      # Images pour CNN
│   ├── chirps_mali_2020.csv         # CSV extraits
│   ├── chirps_mali_2021.csv
│   └── mali_weather_complete.csv    # Dataset final
│   ├── download_chirps.py            # Script téléchargement CHIRPS
│   ├── download_sentinel.py          # Script téléchargement Sentinel
│   └── prepare_training_data.py      # Script préparation données
└── models/
    └── model_trainer_real.py         # Script entraînement avec vraies données
```

---

## 🛠️ Prérequis

### 1. Installer les Dépendances

```bash
cd /Users/macpro/IdeaProjects/alerti
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Installer GDAL (Optionnel mais Recommandé)

**macOS** :
```bash
brew install gdal
pip install gdal==$(gdal-config --version)
```

**Ubuntu/Debian** :
```bash
sudo apt-get install gdal-bin libgdal-dev
pip install gdal
```

**Windows** :
- Téléchargez le wheel depuis https://www.lfd.uci.edu/~gohlke/pythonlibs/
- `pip install GDAL‑xxx‑cpxxx‑win_amd64.whl`

⚠️ **Note** : Si GDAL pose problème, vous pouvez utiliser `rasterio` seul (déjà dans requirements.txt).

---

## 📥 Étape 1 : Télécharger les Données CHIRPS

### Qu'est-ce que CHIRPS ?

**CHIRPS** (Climate Hazards Group InfraRed Precipitation with Station data) :
- 📍 **Couverture** : Afrique entière
- 📏 **Résolution** : 5 km
- ⏰ **Fréquence** : Quotidienne (depuis 1981)
- 💰 **Prix** : Gratuit
- 🔗 **Source** : https://data.chc.ucsb.edu/products/CHIRPS-2.0/

### Téléchargement Automatique

```bash
cd backend/data
python download_chirps.py
```

**Ce script va** :
1. Télécharger les fichiers TIFF quotidiens pour 2020-2024
2. Extraire les précipitations pour les 8 villes du Mali
3. Créer des CSV prêts à l'emploi

⏱️ **Durée** : ~30-60 minutes par année (dépend de votre connexion)

📦 **Taille** : ~100 MB par année

### Téléchargement Manuel (Alternative)

Si le script échoue, téléchargez manuellement :

1. Visitez : https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_daily/tifs/p05/
2. Sélectionnez l'année (ex: 2023)
3. Téléchargez les fichiers `.tif` pour les dates désirées
4. Placez-les dans `backend/data/raw/chirps/`

### Vérification

```bash
ls backend/data/raw/chirps/ | head -5
# Devrait afficher : chirps-v2.0.2023.01.01.tif, etc.

ls backend/data/*.csv
# Devrait afficher : chirps_mali_2020.csv, chirps_mali_2021.csv, etc.
```

---

## 🛰️ Étape 2 : Obtenir les Images Satellites

### Option A : Digital Earth Africa (Recommandé)

**Avantages** :
- Interface web simple
- Optimisé pour l'Afrique
- Données Sentinel pré-traitées

**Procédure** :

1. Visitez : https://maps.digitalearth.africa/
2. Sélectionnez "Sentinel-1" ou "Sentinel-2"
3. Dessinez une zone autour de Bamako
4. Sélectionnez des dates (saison des pluies : juin-septembre)
5. Téléchargez les images
6. Placez-les dans `backend/data/raw/sentinel/`

### Option B : Copernicus Hub

**Procédure** :

1. Créez un compte gratuit : https://scihub.copernicus.eu/
2. Lancez le script :

```bash
cd backend/data
python download_sentinel.py
```

3. Suivez les instructions

### Option C : Google Earth Engine

Pour les utilisateurs avancés, Earth Engine offre un accès API puissant.

```python
# Exemple Earth Engine (non inclus dans le projet)
import ee
ee.Initialize()

collection = ee.ImageCollection('COPERNICUS/S1_GRD') \
    .filterBounds(ee.Geometry.Point(-8.0, 12.6)) \
    .filterDate('2023-06-01', '2023-09-30')
```

### Note Importante

Pour le moment, le système fonctionne principalement avec le **modèle LSTM** (données météo). Les images satellites (CNN) sont optionnelles pour commencer.

---

## 🔧 Étape 3 : Préparer les Données d'Entraînement

Une fois les données CHIRPS téléchargées, préparez-les :

```bash
cd backend/data
python prepare_training_data.py
```

**Ce script va** :

1. ✅ Charger les CSV CHIRPS
2. ✅ Ajouter des features complémentaires (température, humidité, pression)
3. ✅ Ajouter les labels d'inondations historiques
4. ✅ Créer des séquences de 30 jours pour le LSTM
5. ✅ Diviser en train/validation (80/20)
6. ✅ Sauvegarder au format NumPy

**Résultat** :
- `backend/data/training/lstm/X_train.npy` (séquences d'entraînement)
- `backend/data/training/lstm/y_train.npy` (labels)
- `backend/data/training/lstm/X_val.npy` (validation)
- `backend/data/training/lstm/y_val.npy` (labels validation)
- `backend/data/training/mali_weather_complete.csv` (dataset complet)

⏱️ **Durée** : 2-5 minutes

### Personnaliser les Labels d'Inondations

Éditez `prepare_training_data.py` pour ajouter vos propres dates d'inondations :

```python
self.known_floods = {
    'Bamako': [
        '2023-08-15', '2023-08-16',  # Ajoutez vos dates ici
        '2022-07-20', '2022-07-21'
    ],
    # ... autres villes
}
```

**Sources pour trouver des dates** :
- FloodList : https://floodlist.com/
- EM-DAT : https://www.emdat.be/
- Rapports gouvernementaux maliens
- Articles de presse

---

## 🎓 Étape 4 : Entraîner les Modèles

Une fois les données préparées :

```bash
cd backend
python -m models.model_trainer_real
```

**Ce script va** :

1. ✅ Charger les données d'entraînement
2. ✅ Créer et configurer le modèle LSTM
3. ✅ Entraîner pendant 100 époques
4. ✅ Évaluer les performances
5. ✅ Sauvegarder le modèle entraîné

⏱️ **Durée** : 20-30 minutes

**Résultat** :
- `backend/models/lstm_model.h5` (modèle entraîné)
- `backend/models/lstm_scaler.pkl` (scaler pour normalisation)

### Interpréter les Résultats

```
📊 Résultats finaux :
   Loss (train) : 0.0234
   Loss (val) : 0.0289
   MAE (train) : 0.1234
   MAE (val) : 0.1456

🎯 Métriques de classification :
   Accuracy : 0.8542 (85.4%)
   Precision : 0.7234
   Recall : 0.6891
   F1-Score : 0.7058
```

**Bon modèle** :
- Loss < 0.05
- MAE < 0.20
- Accuracy > 80%
- Recall > 60% (important : ne pas manquer les inondations)

**Signes de problèmes** :
- `val_loss >> train_loss` → Surapprentissage (overfitting)
- `recall < 0.4` → Manque trop d'inondations
- `precision < 0.5` → Trop de fausses alertes

---

## 🌍 Sources de Données Alternatives

### Données Météorologiques

| Source | Variables | Résolution | Gratuit |
|--------|-----------|------------|---------|
| **CHIRPS** | Précipitations | 5 km, quotidien | ✅ |
| **GPM IMERG** | Précipitations | 10 km, 30 min | ✅ |
| **ERA5** | Toutes variables | 25 km, horaire | ✅ |
| **TAMSAT** | Précipitations | 4 km, quotidien | ✅ |
| **OpenWeatherMap** | Toutes variables | Point, horaire | ⚠️ Limité |

#### Télécharger ERA5 (Température, Humidité, etc.)

```bash
# Via CDS API (Climate Data Store)
pip install cdsapi

# Créer ~/.cdsapirc avec vos identifiants
# Télécharger : https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels
```

#### Télécharger GPM IMERG

```bash
# Via NASA Earthdata
# Créer un compte : https://urs.earthdata.nasa.gov/
# Télécharger : https://gpm.nasa.gov/data/directory
```

### Images Satellites

| Source | Type | Résolution | Gratuit |
|--------|------|------------|---------|
| **Sentinel-1** | Radar (SAR) | 10 m | ✅ |
| **Sentinel-2** | Optique | 10 m | ✅ |
| **Landsat 8/9** | Optique | 30 m | ✅ |
| **MODIS** | Optique | 250 m | ✅ |
| **Planet** | Optique | 3 m | 💰 Payant |

### Labels d'Inondations

| Source | Description | URL |
|--------|-------------|-----|
| **FloodList** | Base de données mondiale d'inondations | https://floodlist.com/ |
| **EM-DAT** | Événements de désastres | https://www.emdat.be/ |
| **Global Flood Database** | Cartes d'inondations satellite | https://global-flood-database.cloudtostreet.ai/ |
| **DFO** | Dartmouth Flood Observatory | https://floodobservatory.colorado.edu/ |

---

## 🔧 Problèmes Courants

### Problème : GDAL ne s'installe pas

**Solution 1** : Utilisez uniquement `rasterio` (modifiez `download_chirps.py`)

```python
import rasterio
# Au lieu de : from osgeo import gdal
```

**Solution 2** : Téléchargez les CSV pré-extraits (contactez la communauté)

### Problème : Téléchargement CHIRPS très lent

**Solution** :
- Téléchargez seulement 1-2 années pour commencer
- Modifiez dans `download_chirps.py` : `years = [2023, 2024]`

### Problème : Pas assez de labels d'inondations

**Solution** :
- Recherchez sur FloodList : https://floodlist.com/tag/mali
- Consultez les archives de presse maliennes
- Utilisez les données synthétiques pour commencer : `python -m models.model_trainer`

### Problème : Erreur "Out of Memory" pendant l'entraînement

**Solution** :
- Réduisez `batch_size` dans `model_trainer_real.py` : `batch_size=16`
- Réduisez le nombre de séquences dans `prepare_training_data.py`

### Problème : Le modèle ne prédit que des 0

**Solution** :
- Vérifiez l'équilibre des classes dans les données
- Augmentez le nombre d'exemples d'inondations
- Ajustez les seuils dans `prepare_training_data.py`

---

## 📈 Améliorer les Performances

### 1. Ajouter Plus de Données Historiques

```bash
# Dans download_chirps.py, modifiez :
years = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
```

Plus de données = meilleur modèle !

### 2. Remplacer les Features Synthétiques

Les features `temperature`, `humidity`, `pressure`, `soil_moisture` sont actuellement **synthétiques**.

**Remplacez-les par** :
- Température : ERA5 ou stations météo
- Humidité : ERA5
- Pression : ERA5
- Humidité du sol : SMAP (NASA) ou ERA5-Land

### 3. Ajouter Plus de Features

Dans `prepare_training_data.py`, ajoutez :
- Évapotranspiration
- Vitesse du vent
- Indice NDVI (végétation)
- Élévation (DEM)
- Proximité des cours d'eau

### 4. Améliorer les Labels

- Utilisez des cartes d'inondations satellite (Global Flood Database)
- Ajoutez des niveaux de sévérité (0.0 à 1.0)
- Incluez des données de stations hydrométriques

### 5. Augmentation de Données (Data Augmentation)

Pour le CNN (images satellites) :
- Rotation, flip, zoom
- Ajustement de contraste
- Augmentation spectrale

---

## 📝 Résumé : Workflow Complet

```bash
# 1. Activer l'environnement
cd /Users/macpro/IdeaProjects/alerti
source venv/bin/activate

# 2. Télécharger CHIRPS
cd backend/data
python download_chirps.py

# 3. Préparer les données
python prepare_training_data.py

# 4. Entraîner le modèle
cd ..
python -m models.model_trainer_real

# 5. Lancer l'application
python app.py
```

**Durée totale** : 1-2 heures (selon connexion internet)

---

## 🎯 Prochaines Étapes

1. ✅ Testez avec les données synthétiques d'abord
2. ✅ Téléchargez CHIRPS pour 1-2 années
3. ✅ Entraînez le modèle avec vraies données
4. 🔄 Améliorez progressivement avec plus de données
5. 🔄 Ajoutez les images satellites (CNN)
6. 🔄 Déployez en production

---

## 📞 Support

- **Documentation principale** : `README.md`
- **Guide entraînement débutant** : `GUIDE_ENTRAINEMENT.md`
- **Questions** : Ouvrez une issue GitHub

---

## 📚 Ressources Utiles

- [CHIRPS Documentation](https://www.chc.ucsb.edu/data/chirps)
- [Copernicus Open Access Hub](https://scihub.copernicus.eu/)
- [Digital Earth Africa](https://www.digitalearthafrica.org/)
- [NASA Earthdata](https://earthdata.nasa.gov/)
- [FloodList](https://floodlist.com/)
- [EM-DAT Database](https://www.emdat.be/)

---

**Bonne chance avec vos données réelles ! 🎓🌍💧**

