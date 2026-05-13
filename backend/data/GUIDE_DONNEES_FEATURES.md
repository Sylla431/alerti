# 📊 Guide : Obtenir les Données Réelles pour les Nouvelles Features

Ce guide explique comment télécharger/extraire les données réelles pour toutes les features étendues du modèle.

---

## 🗻 1. TOPOGRAPHIE (Élévation, Pente)

### Source : SRTM (NASA) - Gratuit

**Méthode 1 : NASA Earthdata (Recommandé)**

1. **Créer un compte** : https://urs.earthdata.nasa.gov/
2. **Visiter EarthExplorer** : https://earthexplorer.usgs.gov/
3. **Sélectionner** : "SRTM 1 Arc-Second Global"
4. **Zone** :
   - Latitude : 12.55° à 12.70°
   - Longitude : -8.10° à -7.90°
5. **Télécharger** les tuiles
6. **Placer** dans : `backend/data/raw/topography/`

**Méthode 2 : Google Earth Engine (Plus simple)**

```javascript
// Code Earth Engine
var srtm = ee.Image('USGS/SRTMGL1_003');
var bamako = ee.Geometry.Rectangle([-8.1, 12.55, -7.9, 12.70]);
var elevation = srtm.select('elevation').clip(bamako);

Export.image.toDrive({
  image: elevation,
  description: 'bamako_srtm',
  scale: 30,
  region: bamako
});
```

**Méthode 3 : CGIAR-CSI**

- URL : https://srtm.csi.cgiar.org/srtmdata/
- Télécharger tuile Afrique de l'Ouest
- Format : `srtm_XX_XX.tif`

**Script Python** :
```bash
python backend/data/download_topography.py
```

---

## 🏙️ 2. URBANISATION (Bâtiments, Imperméabilisation)

### Source A : OpenStreetMap (Gratuit)

**Méthode 1 : Overpass API**

```python
import requests
import json

# Requête Overpass pour bâtiments à Bamako
query = """
[out:json][timeout:25];
(
  way["building"](12.55,-8.10,12.70,-7.90);
  relation["building"](12.55,-8.10,12.70,-7.90);
);
out body;
>;
out skel qt;
"""

url = "https://overpass-api.de/api/interpreter"
response = requests.post(url, data=query)
data = response.json()

# Calculer densité de bâtiments par commune
```

**Méthode 2 : OSMnx (Python)**

```bash
pip install osmnx
```

```python
import osmnx as ox

# Télécharger bâtiments pour Bamako
bamako = ox.geocode_to_gdf("Bamako, Mali")
buildings = ox.features_from_place("Bamako, Mali", tags={"building": True})

# Calculer densité
building_density = len(buildings) / bamako.area * 1000000  # par km²
```

**Méthode 3 : QuickOSM (QGIS Plugin)**

1. Installer plugin QuickOSM dans QGIS
2. Requête : `building` dans `Bamako`
3. Exporter en GeoJSON

### Source B : Images Sentinel-2 (NDBI - Index de Bâti)

**Google Earth Engine** :

```javascript
var sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR')
  .filterBounds(bamako)
  .filterDate('2023-01-01', '2023-12-31')
  .median();

// Calculer NDBI (Normalized Difference Built-up Index)
var ndbi = sentinel2.normalizedDifference(['B11', 'B8']);

Export.image.toDrive({
  image: ndbi,
  description: 'bamako_ndbi',
  scale: 10,
  region: bamako
});
```

**NDBI > 0.2** = Zone bâtie

---

## 🏗️ 3. INFRASTRUCTURE DE DRAINAGE

### Source A : OpenStreetMap

**Requête Overpass** :

```python
query = """
[out:json][timeout:25];
(
  way["waterway"="drain"](12.55,-8.10,12.70,-7.90);
  way["waterway"="ditch"](12.55,-8.10,12.70,-7.90);
  way["waterway"="canal"](12.55,-8.10,12.70,-7.90);
);
out body;
>;
out skel qt;
"""
```

**Calculer** :
- `drainage_density` = Longueur totale canaux / Surface (km/km²)
- `drainage_coverage` = % zone couverte par canaux

### Source B : Données Municipales (Bamako)

**À contacter** :
- **Direction Régionale de l'Hydraulique** (Bamako)
- **District de Bamako** (Service Assainissement)
- **AGETIC** (Agence des Technologies de l'Information)

**Données disponibles** :
- Plans de canalisations
- État des infrastructures
- Stations de pompage

### Source C : Enquêtes Terrain

**Méthode** :
1. Cartographier canaux avec GPS
2. Évaluer état (1-5)
3. Noter % bouchés
4. Utiliser OpenDataKit (ODK) pour collecte

---

## 💧 4. HYDROLOGIE (Niveau Fleuve, Nappe)

### Source A : Stations Hydrométriques

**Direction Nationale de l'Hydraulique (Mali)** :
- Stations sur le Niger à Bamako
- Données niveau d'eau quotidiennes
- Contact : Direction Nationale de l'Hydraulique, Bamako

**GloFAS (Global Flood Awareness System)** :
- URL : https://www.globalfloods.eu/
- Données de débit du Niger
- Prévisions 10 jours

### Source B : Nappe Phréatique

**FAO AQUASTAT** :
- URL : https://www.fao.org/aquastat/fr/
- Données nappe phréatique Mali
- Profondeur moyenne : 5-15m à Bamako

**Mesures terrain** :
- Puits existants
- Forages
- Stations de mesure

### Source C : Ruissellement

**Calculé à partir de** :
- Précipitations (CHIRPS)
- Type de sol
- Pente (SRTM)
- Imperméabilisation

**Formule** :
```
Runoff = Precipitation × Runoff_Coefficient
Runoff_Coefficient = f(soil_type, slope, impermeability)
```

---

## 🌳 5. VÉGÉTATION (NDVI, Couverture)

### Source : Sentinel-2 (Gratuit)

**Google Earth Engine** :

```javascript
var sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR')
  .filterBounds(bamako)
  .filterDate('2023-01-01', '2023-12-31')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
  .median();

// Calculer NDVI
var ndvi = sentinel2.normalizedDifference(['B8', 'B4']);

// Extraire pour communes
var communes = ee.FeatureCollection('path/to/communes');
var ndvi_by_commune = ndvi.reduceRegions({
  collection: communes,
  reducer: ee.Reducer.mean(),
  scale: 10
});

Export.table.toDrive({
  collection: ndvi_by_commune,
  description: 'bamako_ndvi_communes'
});
```

**Python avec Sentinel Hub** :

```python
from sentinelhub import SentinelHubRequest, DataCollection, MimeType

request = SentinelHubRequest(
    evalscript="""
        return [B08 - B04) / (B08 + B04)];  // NDVI
    """,
    input_data=[
        SentinelHubRequest.input_data(
            data_collection=DataCollection.SENTINEL2_L2A,
            time_interval=('2023-01-01', '2023-12-31')
        )
    ],
    responses=[SentinelHubRequest.output_response('default', MimeType.TIFF)],
    bbox=bamako_bbox,
    size=(512, 512)
)
```

---

## 🏘️ 6. FACTEURS SOCIO-ÉCONOMIQUES

### Source A : Recensement (INSTAT Mali)

**Institut National de la Statistique (Mali)** :
- URL : http://www.instat-mali.org/
- Données population par commune
- Indices de pauvreté
- Accès aux services

### Source B : WorldPop

**WorldPop** :
- URL : https://www.worldpop.org/
- Densité de population haute résolution
- Données gratuites

**Téléchargement** :
```python
import requests

url = "https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/MLI/mli_ppp_2020_1km_Aggregated.tif"
response = requests.get(url)
# Télécharger et extraire pour Bamako
```

### Source C : Enquêtes Terrain

**Méthodes** :
- Enquêtes ménages
- Cartographie participative
- Données ONG locales

---

## 📝 7. WORKFLOW COMPLET

### Étape 1 : Données Faciles (Gratuites, Automatisables)

```bash
# 1. Topographie (SRTM)
python backend/data/download_topography.py

# 2. Urbanisation (OpenStreetMap)
python backend/data/download_urbanization.py

# 3. Végétation (Sentinel-2 via Earth Engine)
# Utiliser le code JavaScript fourni ci-dessus
```

### Étape 2 : Données Moyennes (Nécessitent Comptes)

```bash
# 1. Images Sentinel-2 (Copernicus Hub)
# Créer compte : https://scihub.copernicus.eu/
python backend/data/download_sentinel.py

# 2. Données hydrologiques (GloFAS)
# Télécharger depuis : https://www.globalfloods.eu/
```

### Étape 3 : Données Locales (À Contacter)

1. **Direction Nationale de l'Hydraulique** :
   - Niveau du Niger
   - Stations de mesure
   - Données nappe

2. **District de Bamako** :
   - Plans de canalisations
   - État des infrastructures
   - Maintenance

3. **INSTAT Mali** :
   - Données démographiques
   - Indices socio-économiques

---

## 🔧 8. SCRIPTS D'AUTOMATISATION

### Script Complet (À Créer)

```python
# backend/data/download_all_features.py

def download_all():
    """Télécharge toutes les données nécessaires"""
    
    # 1. Topographie
    download_srtm()
    
    # 2. Urbanisation
    download_osm_buildings()
    download_sentinel2_ndbi()
    
    # 3. Drainage
    download_osm_drainage()
    
    # 4. Végétation
    download_sentinel2_ndvi()
    
    # 5. Population
    download_worldpop()
    
    print("✅ Toutes les données téléchargées !")
```

---

## 📊 9. PRIORISATION

### Niveau 1 : Critique (À Faire Maintenant)

✅ **Topographie (SRTM)** - Facile, gratuit
✅ **Urbanisation (OSM)** - Facile, gratuit
✅ **Précipitations accumulées** - Déjà calculé

### Niveau 2 : Important (À Faire Ensuite)

⭐ **Drainage (OSM)** - Facile, gratuit
⭐ **Végétation (Sentinel-2)** - Moyen, gratuit (compte requis)
⭐ **Population (WorldPop)** - Facile, gratuit

### Niveau 3 : Utile (Long Terme)

💡 **Niveau du Niger** - Contacter autorités
💡 **État drainage** - Enquêtes terrain
💡 **Données socio-économiques** - INSTAT

---

## 🎯 10. RÉSUMÉ RAPIDE

| Feature | Source | Difficulté | Gratuit | Script |
|---------|--------|------------|---------|--------|
| **Élévation** | SRTM | ⭐ Facile | ✅ | `download_topography.py` |
| **Pente** | SRTM | ⭐ Facile | ✅ | `download_topography.py` |
| **Bâtiments** | OSM | ⭐ Facile | ✅ | `download_urbanization.py` |
| **Drainage** | OSM | ⭐ Facile | ✅ | `download_urbanization.py` |
| **NDVI** | Sentinel-2 | ⭐⭐ Moyen | ✅ | Earth Engine |
| **Population** | WorldPop | ⭐ Facile | ✅ | API |
| **Niveau Niger** | Autorités | ⭐⭐⭐ Difficile | ⚠️ | Contact |
| **État drainage** | Terrain | ⭐⭐⭐ Difficile | ⚠️ | Enquête |

---

## 💡 CONSEIL FINAL

**Commencez simple** :
1. Utilisez les valeurs actuelles (synthétiques mais réalistes)
2. Testez le modèle
3. Remplacez progressivement par vraies données
4. Commencez par SRTM et OSM (faciles et gratuits)

**Les données synthétiques actuelles sont suffisantes pour tester le système !**

---

## 📞 CONTACTS UTILES

- **Direction Nationale de l'Hydraulique** : Bamako, Mali
- **INSTAT** : http://www.instat-mali.org/
- **District de Bamako** : Service Assainissement
- **AGETIC** : Agence des Technologies de l'Information

---

**Bon courage ! 🚀**

