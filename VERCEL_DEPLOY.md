# Déploiement Vercel — Alerti

## Pourquoi l'erreur « 2552 MB > 500 MB » ?

Vercel compte tout ce qui part au build :

| Élément | Taille approx. |
|---------|----------------|
| `venv/` local uploadé par erreur | ~2,1 Go |
| `backend/data/` (CHIRPS, CSV, etc.) | ~1,3 Go |
| `pip install tensorflow` au build | ~1,1 Go |
| OpenCV, rasterio, netCDF | centaines de Mo |

**Total observé : ~2,5 Go** → dépasse la limite **500 Mo** de stockage éphémère Lambda.

Même sans `venv/` dans le zip, **TensorFlow seul dépasse la limite Vercel**.  
L'API complète (`app.py` + LSTM Bamako) **ne peut pas** tourner sur Vercel Serverless classique.

## Architecture recommandée

| Service | Hébergement | Rôle |
|---------|-------------|------|
| API ML (LSTM, Bamako, CHIRPS) | **Railway** (déjà en prod) | `app.py` + `requirements.txt` |
| Météo légère (optionnel) | **Vercel** | `app_vercel.py` + `requirements-vercel.txt` |
| Push FCM | **Vercel** (`flood-alert-lambda`) | Node.js |

Flutter : garder `ALERTI_API_BASE` sur **Railway** pour les prédictions.

## Déployer la version légère sur Vercel

```bash
cd alerti
npx vercel          # preview
npx vercel --prod   # production
```

Fichiers utilisés :

- `vercel.json` → installe `requirements-vercel.txt`, lance `app_vercel.py`
- `.vercelignore` → exclut `venv/`, données, modèles `.h5`, `requirements.txt` (TF)

Routes disponibles sur Vercel :

- `GET /`
- `GET /api/weather/at?lat=&lon=`
- `GET /api/weather/diag`

Routes **503** (volontaire) : `/api/bamako/predict`, `/api/predict`, etc.

## Tester en local avant deploy

```bash
source venv/bin/activate
pip install -r requirements-vercel.txt
PORT=5000 python app_vercel.py
```

```bash
curl "http://127.0.0.1:5000/api/weather/at?lat=12.65&lon=-7.98"
```

Simuler Vercel :

```bash
npx vercel dev
```

## API complète (ML) — Railway

```bash
pip install -r requirements.txt
python app.py
```

Variables d'environnement : copier `.env` dans le dashboard Railway.

## Si vous voulez tout sur une seule URL

Ne pas utiliser Vercel pour le Python ML. Options :

1. **Railway uniquement** (recommandé, déjà configuré dans l'app Flutter prod).
2. **Vercel** pour le frontend React + **Railway** pour l'API Python.
3. Conteneur Docker (Fly.io, Render, AWS) si vous avez besoin de >500 Mo en un seul service.
