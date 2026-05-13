# Alerti - Systeme de prediction et d'alerte inondation

Alerti est une plateforme full-stack de prediction de risque d'inondation, orientee Afrique, avec un focus operationnel sur le Mali (notamment Bamako).  
Le projet combine:

- une API Flask pour l'inference, les alertes et les integrations externes,
- un frontend React pour la visualisation cartographique et le suivi des risques,
- un pipeline data/ML pour preparer des jeux de donnees et entrainer des modeles de prediction.

## Description generale du projet

Alerti transforme des signaux hydrometeorologiques et geospatiaux en niveaux de risque exploitables:

- **Prediction hybride**: combinaison de modeles temporels (LSTM) et image/satellite (CNN/hybride selon disponibilite).
- **Couverture Afrique**: endpoints pays + support multi-localisations.
- **Focus Bamako**: endpoint dedie `api/bamako/predict` avec logique commune/quartier.
- **Alerting multi-canal**: notifications email, SMS/WhatsApp (Twilio), push (FCM) selon configuration.
- **Front cartographique**: consultation des zones, niveaux de risque et interactions utilisateur.

Le depot contient donc a la fois:

1. un produit applicatif executable (backend + frontend),
2. des scripts d'entrainement et de preparation des donnees,
3. des utilitaires de verification et de reporting.

## Architecture

```text
alerti/
├── app.py                         # Point d'entree Flask principal (API)
├── train_models.py                # Script simplifie d'entrainement
├── requirements.txt               # Dependances Python
├── backend/
│   ├── models/                    # LSTM/CNN/Hybrid + trainers
│   ├── services/                  # Meteo, satellite, alertes, Bamako
│   ├── data/                      # Download/preparation datasets
│   └── utils/                     # Config + referentiels geographiques
├── frontend/
│   ├── package.json               # React app + scripts npm
│   └── src/                       # UI, routing, services API
├── GUIDE_ENTRAINEMENT.md
└── README_DATA.md
```

## Stack technique

### Backend

- Python + Flask (`app.py`)
- TensorFlow/Keras pour modeles IA
- NumPy, Pandas, scikit-learn pour traitement et feature engineering
- Services externes optionnels: OpenWeather, Twilio, Firebase, Sentinel/Copernicus

### Frontend

- React 18 (`react-scripts`)
- React Router
- Leaflet / React-Leaflet pour la carte
- Axios pour communication avec API

## Prerequis

- Python 3.11 ou 3.12 recommande
- Node.js 16+ (18+ recommande)
- `pip` et `npm`

> Note: certaines dependances geospatiales (ex: `rasterio`) peuvent necessiter des pre-requis systeme.

## Installation rapide (developpement)

### 1) Backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Creer un fichier `.env` a la racine (cles optionnelles pour demarrer en mode local):

```env
PORT=5000
FLASK_DEBUG=True

# Optionnel (integrations externes)
OPENWEATHERMAP_API_KEY=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
FCM_SERVER_KEY=
```

Lancer l'API:

```bash
python app.py
```

API disponible sur `http://localhost:5000`.

### 2) Frontend

```bash
cd frontend
npm install
npm start
```

UI disponible sur `http://localhost:3000` (proxy configure vers `http://localhost:5000`).

## Verification rapide

Avec le backend lance:

```bash
curl http://localhost:5000/
```

Vous devez recuperer un JSON contenant la version et la liste d'endpoints.

## Endpoints API principaux

### Prediction

- `GET /` - meta API et endpoints disponibles
- `POST /api/predict` - prediction complete
- `POST /api/predict-meteo` - prediction meteo (LSTM)
- `POST /api/predict-image` - prediction image (CNN)
- `POST /api/bamako/predict` - prediction Bamako (commune/quartier)
- `POST /api/predict/neighborhood` - prediction quartier (POST)
- `GET /api/mali/neighborhood/<name>/predict` - prediction quartier (GET)

### Donnees geographiques / coverage

- `GET /api/countries`
- `GET /api/mali/neighborhoods?city=bamako`
- `GET /api/satellite-image/<location>`

### Alertes / abonnements

- `GET /api/alerts`
- `GET /api/forecast/<country>`
- `POST /api/alert/subscribe`
- `POST /api/subscribe/push`

## Exemple de requete prediction

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Nigeria",
    "latitude": 9.0820,
    "longitude": 8.6753,
    "country": "nigeria"
  }'
```

## Pipeline data et entrainement

Le projet propose plusieurs workflows:

1. **Workflow simplifie (demo)**
  Lance l'entrainement via:
2. **Workflow data/ML detaille**
  Scripts sous `backend/data/` pour telechargement, preparation et verification.
   Exemple utile:
3. **Workflows specialises**
  - entrainement general: `backend/models/model_trainer.py`
  - entrainement "real data": `backend/models/model_trainer_real.py`
  - entrainement Bamako: `backend/models/model_trainer_bamako.py`

Modeles et artefacts sont generes dans `backend/models/` et `backend/data/training/`.

## Fichiers importants

- `app.py`: point d'entree unique du backend Flask.
- `train_models.py`: script guide pour demarrer rapidement l'entrainement.
- `backend/services/bamako_prediction_service.py`: logique inference Bamako.
- `backend/data/prepare_bamako_data.py`: preparation sequences Bamako.
- `frontend/src/App.jsx`: routing et vues principales.
- `frontend/src/services/api.js`: client API frontend.

## Bonnes pratiques

- Ne jamais committer de secrets (`.env`, credentials cloud, cles API).
- Verifier l'etat de l'installation avant entrainement avec `backend/data/check_setup.py`.
- Garder les versions Python/Node coherentes entre equipe et CI.

## Documentation complementaire

- `GUIDE_ENTRAINEMENT.md` - pas a pas entrainement
- `README_DATA.md` - details preparation/collecte donnees

## Limites connues

- Certaines integrations externes necessitent des comptes et cles valides.
- Les workflows ML peuvent etre longs et gourmands en RAM/CPU.
- Les dependances geospatiales peuvent demander une configuration machine supplementaire.

## Licence

A definir (ajouter une licence explicite si le projet doit etre partage publiquement).

# 🌊 Système d'Alerte de Prédiction d'Inondations pour l'Afrique

Système de prédiction d'inondations utilisant l'IA pour les pays d'Afrique, combinant des modèles LSTM (séries temporelles) et CNN (images satellite) pour fournir des prédictions précises et des alertes automatiques.

## 🎯 Fonctionnalités

- **Prédiction Hybride**: Combine LSTM (données météorologiques) et CNN (images satellite)
- **Prédiction par Quartier**: Prédictions granulaires par quartier pour le Mali (Bamako, Kayes, Sikasso, etc.)
- **Prévisions Météorologiques Futures**: Intégration OpenWeatherMap pour les prévisions jusqu'à 5 jours
- **Sources de Données Africaines**: CHIRPS, GPM IMERG, Sentinel-1/2, Digital Earth Africa
- **Système d'Alertes Multi-Canal**: 
  - Email
  - SMS (via Twilio)
  - WhatsApp (messages texte et vocaux)
  - Notifications Push (iOS/Android via Firebase Cloud Messaging)
- **Système d'Alertes**: 4 niveaux (Critique, Élevé, Moyen, Faible)
- **Interface Web Interactive**: Carte avec visualisation des risques, alertes en temps réel
- **Analyse d'Images Satellite**: Détection visuelle des zones inondées
- **Support Multi-Pays**: 20+ pays africains pré-configurés

## 🏗️ Architecture

```
alerti/
├── backend/
│   ├── models/          # Modèles IA (LSTM, CNN, Hybrid)
│   ├── services/        # Services données et alertes
│   ├── utils/           # Configuration
│   └── app.py          # API Flask
├── frontend/
│   ├── src/
│   │   ├── components/ # Composants React
│   │   └── services/   # Client API
│   └── public/
└── requirements.txt
```

## 🚀 Installation

### Prérequis

- **Python 3.11 ou 3.12** (recommandé) - Python 3.13 n'est pas encore complètement supporté par TensorFlow
- Node.js 16+ (pour le frontend)
- pip3 (installé avec Python)

**Note:** Si vous utilisez Python 3.13, TensorFlow peut ne pas être disponible. Utilisez `tf-nightly` ou une version antérieure de Python.

### Backend

1. **Créer un environnement virtuel (recommandé):**

```bash
# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement virtuel
# Sur macOS/Linux:
source venv/bin/activate
# Sur Windows:
# venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

**Note:** Après activation, votre terminal affichera `(venv)` au début de la ligne.

1. **Créer un fichier `.env` à la racine:**

```env
# API Keys (optionnel pour commencer)
EARTHDATA_USERNAME=your_username
EARTHDATA_PASSWORD=your_password
COPERNICUS_USERNAME=your_username
COPERNICUS_PASSWORD=your_password
SENTINEL_HUB_API_KEY=your_key

# Twilio (SMS et WhatsApp)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WHATSAPP_NUMBER=+1234567890  # Numéro WhatsApp Business vérifié

# Email
EMAIL_USER=your_email
EMAIL_PASSWORD=your_password
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587

# OpenWeatherMap (prévisions météorologiques)
OPENWEATHERMAP_API_KEY=your_openweathermap_key

# Firebase Cloud Messaging (notifications push)
FCM_SERVER_KEY=your_fcm_server_key
# OU
FCM_CREDENTIALS_PATH=/path/to/firebase-credentials.json

# Flask Configuration
PORT=5000
FLASK_DEBUG=False
```

1. **Lancer le serveur:**

```bash
python app.py
```

Le serveur sera disponible sur `http://localhost:5000`

### Frontend

1. **Installer les dépendances:**

```bash
cd frontend
npm install
```

1. **Lancer l'application:**

```bash
npm start
```

L'application sera disponible sur `http://localhost:3000`

## 🧠 Modèles IA

### LSTM (Long Short-Term Memory)

- **Usage**: Prédiction basée sur séries temporelles de précipitations
- **Entrée**: 30 jours de données météorologiques (précipitations, température, humidité, etc.)
- **Sortie**: Probabilité d'inondation pour les 7 prochains jours

### CNN/U-Net

- **Usage**: Segmentation sémantique pour détecter les zones inondées sur images satellite
- **Entrée**: Images satellite Sentinel-1/2 (256x256x3)
- **Sortie**: Masque binaire des zones inondées + probabilité

### Modèle Hybride

- **Méthode**: Fusion pondérée des prédictions LSTM et CNN
- **Poids**: LSTM (60%), CNN (40%) par défaut (peut être entraîné)

### Entraînement des Modèles

Pour entraîner les modèles avec des données synthétiques:

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Lancer l'entraînement (automatique)
python -m backend.models.model_trainer
```

**Pour les débutants** : Consultez `GUIDE_ENTRAINEMENT.md` pour un guide détaillé pas à pas.

L'entraînement prend environ 20-30 minutes et génère automatiquement :

- Modèle LSTM (prédictions météo)
- Modèle CNN (détection images satellites)
- Modèle de fusion (combinaison des deux)

## 📡 API Endpoints

### Prédictions

- `GET /` - Informations sur l'API
- `POST /api/predict` - Prédiction complète (hybride)
- `POST /api/predict-meteo` - Prédiction météo uniquement (LSTM)
- `POST /api/predict-image` - Prédiction image uniquement (CNN)
- `POST /api/bamako/predict` - Prédiction LSTM Bamako (commune/quartier) basée sur les 6 communes
- `POST /api/predict/neighborhood` - Prédiction pour un quartier (Mali)
- `GET /api/mali/neighborhood/<name>/predict` - Prédiction pour un quartier spécifique

#### Utiliser `/api/bamako/predict`

- **Payload minimal** :
  ```json
  {
    "commune": "Commune IV"
  }
  ```
- **Mapping quartier → commune** : le backend reconnaît automatiquement les quartiers listés dans `frontend/public/commune/Les Quartiers à risques d’inondation de Bamako(1).pdf`, p. ex. `{"neighborhood": "Banconi Sikoro"}`.
- **Réponse** :
  ```json
  {
    "commune": "Commune IV",
    "neighborhood": "Sabalibougou",
    "prediction": {
      "flood_probability": 0.67,
      "risk_level": "high",
      "sequence_end_date": "2024-10-08",
      "coordinates": {"lat": 12.6531, "lon": -8.0331}
    },
    "context": {
      "static_features": {...},
      "risk_factors": {...}
    },
    "metadata": {
      "latency_ms": 42.3,
      "last_sequence_loaded_at": "2025-11-27T12:00:31"
    }
  }
  ```
- **Notes** :
  - Le modèle charge automatiquement les dernières séquences `X_train.npy`/`X_val.npy` générées par `backend/data/prepare_bamako_data.py`.
  - Les logs Flask incluent `BamakoPredict commune=... prob=... latency=...` pour suivre la latence d’inférence.
  - Pour rafraîchir les séquences, régénérez les fichiers `bamako_lstm/` puis redémarrez le backend.

### Quartiers du Mali

- `GET /api/mali/neighborhoods?city=bamako` - Liste des quartiers d'une ville

### Alertes et Abonnements

- `GET /api/alerts` - Liste des alertes actives
- `GET /api/forecast/<country>` - Prévision pour un pays
- `POST /api/alert/subscribe` - S'abonner aux alertes (email, SMS, WhatsApp, push)
- `POST /api/subscribe/push` - S'abonner aux notifications push

### Données

- `GET /api/countries` - Liste des pays supportés
- `GET /api/satellite-image/<location>` - Image satellite

### Exemple de Requête

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Nigeria",
    "latitude": 9.0820,
    "longitude": 8.6753,
    "country": "nigeria"
  }'
```

## 📊 Sources de Données

### Météorologiques

- **CHIRPS**: Précipitations historiques (1981-présent) - **Recommandé pour l'Afrique**
- **GPM IMERG**: Précipitations temps réel (NASA)
- **TAMSAT**: Précipitations Afrique

### Images Satellite

- **Sentinel-1**: SAR (all-weather) - **Recommandé pour l'Afrique**
- **Sentinel-2**: Optique haute résolution
- **Digital Earth Africa**: Water Observations from Space (WOfS)

## 🚨 Système d'Alertes

### Niveaux d'Alerte

1. **Critique** (≥80%): Évacuation immédiate requise
2. **Élevé** (60-80%): Préparer plan d'évacuation
3. **Moyen** (40-60%): Surveillance renforcée
4. **Faible** (20-40%): Conditions normales
5. **Aucun** (<20%): Aucun risque détecté

### Notifications

- **Email** (configuré via SMTP)
- **SMS** (via Twilio - optionnel)
- **WhatsApp** (via Twilio WhatsApp API - nécessite un numéro Business vérifié)
  - Messages texte
  - Messages vocaux (pour alertes critiques)
- **Notifications Push** (via Firebase Cloud Messaging)
  - Support iOS et Android
  - Abonnements par quartier/localisation
- Notifications push navigateur (frontend)

## 🌍 Pays Supportés

Nigeria, Kenya, South Africa, Ghana, Tanzania, Uganda, Mali, Mozambique, Cameroon, Côte d'Ivoire, Madagascar, Angola, Niger, Burkina Faso, Malawi, Zambia, Senegal, Chad, Somalia, Zimbabwe

## 🛠️ Technologies Utilisées

### Backend

- Python 3.8+
- Flask (API REST)
- TensorFlow/Keras (Modèles IA)
- NumPy, Pandas (Traitement données)
- OpenCV (Traitement images)

### Frontend

- React 18
- Leaflet (Cartes)
- Axios (HTTP client)

### Données

- CHIRPS, GPM IMERG (Météo)
- Sentinel-1/2 (Satellite)
- Digital Earth Africa

## 📝 Notes

- Les modèles utilisent actuellement des données simulées pour la démonstration
- Pour la production, intégrer les vraies APIs des sources de données
- Les modèles peuvent être entraînés avec vos propres données historiques
- Les images satellite nécessitent des clés API (gratuites pour la recherche)

## 🔐 Configuration Sécurisée

Ne commitez jamais vos clés API dans le code. Utilisez toujours un fichier `.env` (qui devrait être dans `.gitignore`).

## 📄 License

Ce projet est open-source. Libre d'utilisation et de modification.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📞 Support

Pour toute question ou problème, veuillez ouvrir une issue sur le repository.

---

**Développé pour la prévention des inondations en Afrique** 🌍