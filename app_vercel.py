"""
Point d'entrée Vercel — API légère (météo uniquement).
Prédictions inondation (TensorFlow) : héberger sur Railway, pas sur Vercel.
"""
import os
import sys

from flask import Flask, jsonify, request
from flask_cors import CORS

backend_path = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_path)

from services.weather_forecast_service import WeatherForecastService

app = Flask(__name__)
CORS(app)
weather_forecast_service = WeatherForecastService()


@app.route("/")
def index():
    return jsonify(
        {
            "message": "Alerti API (Vercel — météo uniquement)",
            "version": "1.0.0-vercel",
            "note": "LSTM/CNN : utiliser l'API Railway (TensorFlow trop lourd pour Vercel).",
            "endpoints": {
                "weather_at": "/api/weather/at?lat=&lon=",
                "weather_diag": "/api/weather/diag",
            },
        }
    )


@app.route("/api/weather/diag", methods=["GET"])
def weather_key_diagnostics():
    return jsonify(weather_forecast_service.key_diagnostics())


@app.route("/api/weather/at", methods=["GET", "OPTIONS"])
def weather_at_coordinates():
    if request.method == "OPTIONS":
        return ("", 204)
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if lat is None or lon is None:
        return jsonify({"error": "Query params lat and lon required"}), 400
    snapshot = weather_forecast_service.get_weather_snapshot(lat, lon)
    status = 200 if snapshot.get("success", True) else 503
    return jsonify(snapshot), status


@app.route("/api/bamako/predict", methods=["POST", "OPTIONS"])
@app.route("/api/predict", methods=["POST"])
@app.route("/api/predict-meteo", methods=["POST"])
def ml_not_on_vercel():
    return (
        jsonify(
            {
                "error": "Prediction ML indisponible sur Vercel (limite 500 Mo).",
                "hint": "Utilisez l'API Railway ou python app.py en local.",
            }
        ),
        503,
    )
