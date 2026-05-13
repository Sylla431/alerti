# 📊 Guide de Téléchargement des Données CHIRPS

## ⚠️ Problème avec l'URL CHIRPS ?

Si vous obtenez une erreur **404** lors du téléchargement, c'est normal ! Les URLs CHIRPS ont changé.

---

## 🎯 Solutions Disponibles

### ✅ Solution 1 : Données Synthétiques (Rapide - Pour Tester)

**Avantages** :
- Pas de téléchargement nécessaire
- Fonctionne immédiatement
- Idéal pour tester le système

**Utilisation** :

```bash
python download_chirps_simple.py
# Choisir option 1
```

⏱️ **Durée** : 1 minute

---

### 🔄 Solution 2 : Script Corrigé (Données Mensuelles)

Le script `download_chirps.py` a été mis à jour pour utiliser les **données mensuelles** (plus fiables) :

```bash
python download_chirps.py
```

**Changements** :
- Utilise l'URL mensuelle au lieu de quotidienne
- Télécharge 12 fichiers par an (au lieu de 365)
- Répartit les précipitations mensuelles sur les jours

⏱️ **Durée** : 10-15 minutes par année

---

### 🌐 Solution 3 : Climate Engine (Recommandé pour Production)

**Le plus simple et le plus fiable !**

1. Visitez : https://app.climateengine.com/
2. Sélectionnez **"CHIRPS"** comme dataset
3. Dessinez un polygone autour du Mali
4. Sélectionnez dates : 2020-01-01 à 2024-12-31
5. **Téléchargez en CSV**
6. Placez dans `backend/data/chirps_mali_YYYY.csv`

✅ **Avantages** :
- Interface web simple
- Données pré-extraites
- Pas besoin de GDAL
- Format CSV directement utilisable

---

### 🛰️ Solution 4 : Google Earth Engine

Pour les utilisateurs avancés avec compte Earth Engine.

**Code Python** :

```python
import ee
ee.Initialize()

# Définir la région (Mali)
mali = ee.Geometry.Rectangle([-12.5, 10.0, 4.5, 25.0])

# Charger CHIRPS
chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
    .filterDate('2020-01-01', '2024-12-31') \
    .filterBounds(mali)

# Extraire pour les villes
locations = {
    'Bamako': ee.Geometry.Point([-8.0029, 12.6392]),
    'Sikasso': ee.Geometry.Point([-5.6671, 11.3177]),
    # ... autres villes
}

# Exporter vers Drive
for name, point in locations.items():
    task = ee.batch.Export.table.toDrive(
        collection=chirps.map(lambda img: img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=5000
        )),
        description=f'chirps_{name}',
        fileFormat='CSV'
    )
    task.start()
```

---

### 📥 Solution 5 : IRI Data Library

**URL** : https://iridl.ldeo.columbia.edu/

1. Climate → Precipitation → CHIRPS
2. Sélectionnez "Daily" ou "Monthly"
3. Définissez la bbox : lon(-12, 5), lat(10, 25)
4. Dates : 2020-2024
5. Téléchargez en NetCDF ou CSV

---

## 🔧 Dépannage

### Erreur 404 lors du téléchargement

```
❌ Téléchargement : chirps-v2.0.2020.01.01.tif... (code 404)
```

**Cause** : Les URLs quotidiennes CHIRPS v2 ne sont plus disponibles ou ont changé.

**Solutions** :
1. Utilisez les données synthétiques : `python download_chirps_simple.py`
2. Téléchargez manuellement depuis Climate Engine (voir ci-dessus)
3. Utilisez le script corrigé avec données mensuelles

### GDAL ne s'installe pas

**Solution** : Utilisez `download_chirps_simple.py` qui ne nécessite pas GDAL.

### Téléchargement très lent

**Solution** : Utilisez les données mensuelles (12 fichiers au lieu de 365).

---

## 📝 Workflow Recommandé

### Pour Démarrer Rapidement (Test)

```bash
# 1. Générer données synthétiques
python download_chirps_simple.py  # Option 1

# 2. Préparer les données
python prepare_training_data.py

# 3. Entraîner
cd ..
python -m models.model_trainer_real
```

⏱️ **Durée totale** : 5-10 minutes

### Pour Production (Vraies Données)

```bash
# 1. Télécharger depuis Climate Engine (manuel)
# Visitez https://app.climateengine.com/
# Téléchargez les CSV pour 2020-2024

# 2. Placer les CSV dans backend/data/
# Exemple : chirps_mali_2020.csv

# 3. Préparer les données
python prepare_training_data.py

# 4. Entraîner
cd ..
python -m models.model_trainer_real
```

⏱️ **Durée totale** : 30-60 minutes

---

## 📊 Format des Données Attendu

Les CSV doivent avoir ce format :

```csv
date,location,lat,lon,precipitation
2020-01-01,Bamako,12.6392,-8.0029,0.0
2020-01-01,Sikasso,11.3177,-5.6671,1.2
2020-01-01,Ségou,13.4317,-6.2633,0.0
...
```

---

## 🆘 Besoin d'Aide ?

1. **Données de test** : Utilisez `download_chirps_simple.py`
2. **Problème technique** : Ouvrez une issue GitHub
3. **Questions** : Consultez `README_DATA.md`

---

## 🎯 Résumé Rapide

| Méthode | Difficulté | Temps | Qualité |
|---------|------------|-------|---------|
| **Synthétiques** | ⭐ Facile | 1 min | ⚠️ Test uniquement |
| **Climate Engine** | ⭐⭐ Moyen | 30 min | ✅ Excellente |
| **Script mensuel** | ⭐⭐⭐ Avancé | 15 min | ✅ Bonne |
| **Earth Engine** | ⭐⭐⭐⭐ Expert | Variable | ✅ Excellente |

**Recommandation** : Commencez avec les **données synthétiques** pour tester, puis passez à **Climate Engine** pour la production.

