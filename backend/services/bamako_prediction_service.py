"""
Service de prédiction pour Bamako.
Charge le modèle LSTM spécifique, les séquences les plus récentes par commune
et fournit une API simplifiée pour exposer ces prédictions au frontend.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import joblib
import numpy as np

from models.predictors.lstm_model_bamako import LSTMPredictorBamako
from models.predictors.lstm_model_bamako_rainfall import (
    RAINFALL_FEATURE_COLS,
    LSTMPredictorBamakoRainfall,
)
from services.bamako_live_sequence_builder import (
    build_model_sequence,
    fetch_merged_daily_meteo,
)
from utils.bamako_communes import BAMAKO_COMMUNES
from utils.bamako_features import get_risk_factors, get_static_features
from utils.bamako_neighborhoods import (
    BAMAKO_COMMUNE_NEIGHBORHOODS,
    get_commune_from_neighborhood,
    normalize_commune_name,
)


@dataclass
class CommuneSequence:
    commune: str
    end_date: Optional[str]
    split: str
    sequence: np.ndarray


class BamakoPredictionService:
    """Chargement du modèle Bamako + expose des prédictions par commune/quartier."""

    def __init__(self):
        backend_root = os.path.dirname(os.path.dirname(__file__))
        self.training_dir = os.path.join(backend_root, "data", "training", "bamako_lstm")
        self.lstm_predictor = LSTMPredictorBamako()

        # Modèle pluie-seule (régional Bamako-ville). Chargé uniquement si son
        # artefact entraîné existe, pour ne jamais servir un modèle non entraîné.
        self.rainfall_predictor: Optional[LSTMPredictorBamakoRainfall] = None
        rainfall_h5 = os.path.join(
            backend_root, "models", "artifacts", "lstm_model_bamako_rainfall.h5"
        )
        rainfall_pkl = os.path.join(
            backend_root, "models", "artifacts", "lstm_scaler_bamako_rainfall.pkl"
        )
        if os.path.exists(rainfall_h5) and os.path.exists(rainfall_pkl):
            try:
                self.rainfall_predictor = LSTMPredictorBamakoRainfall()
                print("[BamakoPredictionService] ✅ Modèle pluie-seule disponible")
            except Exception as exc:
                print(f"[BamakoPredictionService] ⚠️ Modèle pluie-seule indisponible: {exc}")
                self.rainfall_predictor = None
        else:
            print("[BamakoPredictionService] ℹ️ Artefact pluie-seule absent (modèle 29-feat seul)")

        self.sequences_by_commune: Dict[str, CommuneSequence] = {}
        self.last_loaded_at: Optional[datetime] = None
        self._load_latest_sequences()
        # Fit scaler on loaded sequences to avoid "not fitted" errors at inference
        try:
            self._fit_scaler_with_sequences()
        except Exception as exc:
            print(f"[BamakoPredictionService] ⚠️ Impossible de fitter le scaler: {exc}")

    def _fit_scaler_with_sequences(self):
        """Fit the LSTM scaler using loaded commune sequences (fallback if scaler.pkl absent)."""
        if not self.sequences_by_commune:
            return
        sequences = np.stack([seq.sequence for seq in self.sequences_by_commune.values()], axis=0)
        flat = sequences.reshape(-1, sequences.shape[-1])
        if np.isnan(flat).all():
            return
        self.lstm_predictor.scaler.fit(flat)
        # Persist scaler for next runs
        try:
            joblib.dump(self.lstm_predictor.scaler, self.lstm_predictor.scaler_path)
        except Exception as exc:
            print(f"[BamakoPredictionService] ⚠️ Impossible de sauvegarder le scaler: {exc}")

    # ------------------------------------------------------------------ #
    # Chargement des séquences depuis les fichiers numpy/metadata
    # ------------------------------------------------------------------ #
    def _load_latest_sequences(self):
        if not os.path.isdir(self.training_dir):
            print(f"[BamakoPredictionService] ⚠️ Dossier introuvable : {self.training_dir}")
            return

        sequences: Dict[str, CommuneSequence] = {}
        for split in ("train", "val"):
            x_path = os.path.join(self.training_dir, f"X_{split}.npy")
            meta_path = os.path.join(self.training_dir, f"metadata_{split}.json")
            if not os.path.exists(x_path) or not os.path.exists(meta_path):
                continue

            try:
                data = np.load(x_path)
                with open(meta_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception as exc:
                print(f"[BamakoPredictionService] ❌ Impossible de charger {split}: {exc}")
                continue

            if len(metadata) != len(data):
                print(
                    f"[BamakoPredictionService] ⚠️ Taille metadata ({len(metadata)}) ≠ données ({len(data)}) pour {split}"
                )

            for idx, meta in enumerate(metadata):
                if idx >= len(data):
                    break
                commune = meta.get("commune")
                end_date = meta.get("end_date")
                if not commune:
                    continue

                try:
                    sequence = np.array(data[idx], dtype=np.float32, copy=True)
                except Exception as exc:
                    print(f"[BamakoPredictionService] ⚠️ Impossible de copier la séquence {idx}: {exc}")
                    continue

                key = commune
                current = sequences.get(key)

                def to_dt(value: Optional[str]) -> datetime:
                    if not value:
                        return datetime.min
                    try:
                        return datetime.strptime(value, "%Y-%m-%d")
                    except ValueError:
                        return datetime.min

                new_dt = to_dt(end_date)
                current_dt = to_dt(current.end_date) if current else datetime.min

                if new_dt >= current_dt:
                    sequences[key] = CommuneSequence(
                        commune=commune,
                        end_date=end_date,
                        split=split,
                        sequence=sequence,
                    )

        self.sequences_by_commune = sequences
        self.last_loaded_at = datetime.now()
        print(
            f"[BamakoPredictionService] ✅ Séquences chargées pour {len(self.sequences_by_commune)} communes "
            f"(dernière mise à jour: {self.last_loaded_at.isoformat(timespec='seconds')})"
        )

    # ------------------------------------------------------------------ #
    # API publique
    # ------------------------------------------------------------------ #
    def _model_n_features(self) -> Optional[int]:
        model = self.lstm_predictor.model
        if model is not None and getattr(model, "input_shape", None):
            shape = model.input_shape
            if shape and len(shape) >= 3 and shape[-1]:
                return int(shape[-1])
        return None

    def predict(
        self,
        commune: Optional[str] = None,
        neighborhood: Optional[str] = None,
        *,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        use_live_weather: bool = True,
        model: str = "rainfall",
    ) -> Dict:
        """Prédiction Bamako.

        model :
          - "rainfall" (défaut) : modèle pluie-seule régional (5 features) —
            recommandé, validé sur CHIRPS réel. Repli auto sur "full" si absent.
          - "full"     : modèle 29 features par commune.

        En live : reconstruit une fenêtre de 30 jours (météo récente + prévisions)
        puis infère ; repli sur les séquences .npy en cas d'échec.
        """
        want_rainfall = model == "rainfall" and self.rainfall_predictor is not None
        if model == "rainfall" and self.rainfall_predictor is None:
            print(
                "[BamakoPredictionService] ℹ️ Modèle pluie-seule indisponible, "
                "repli sur le modèle 29 features"
            )

        if use_live_weather:
            try:
                if want_rainfall:
                    return self.predict_rainfall_live(
                        commune=commune,
                        neighborhood=neighborhood,
                        latitude=latitude,
                        longitude=longitude,
                    )
                return self.predict_live(
                    commune=commune,
                    neighborhood=neighborhood,
                    latitude=latitude,
                    longitude=longitude,
                )
            except Exception as exc:
                print(
                    f"[BamakoPredictionService] ⚠️ predict_live échoué ({exc}), "
                    "repli séquences entraînement"
                )
        return self._predict_from_cached_sequences(commune=commune, neighborhood=neighborhood)

    def predict_rainfall_live(
        self,
        commune: Optional[str] = None,
        neighborhood: Optional[str] = None,
        *,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict:
        """Prédiction LIVE avec le modèle pluie-seule (risque régional Bamako-ville).

        Reconstruit la fenêtre de 30 jours de pluie (CHIRPS + OpenWeather) et
        infère sur les 5 features pluie. Le résultat est identique pour toute la
        ville (aucune différenciation commune) ; commune/quartier servent au
        contexte (zones à risque, facteurs).
        """
        if self.rainfall_predictor is None:
            raise ValueError("Modèle pluie-seule non disponible")

        start_time = time.perf_counter()
        # Commune facultative pour le modèle régional : sert au contexte.
        resolved_commune = self._resolve_commune(commune, neighborhood)

        commune_info = BAMAKO_COMMUNES.get(resolved_commune, {}) if resolved_commune else {}
        if latitude is not None and longitude is not None:
            lat, lon = float(latitude), float(longitude)
        else:
            lat = commune_info.get("lat")
            lon = commune_info.get("lon")
        if lat is None or lon is None:
            # Repli sur le centre-ville de Bamako pour un signal régional.
            lat, lon = 12.6392, -8.0029

        seq_len = self.rainfall_predictor.sequence_length
        future_days = int(getattr(self.rainfall_predictor, "forecast_days", 7))
        input_length = int(getattr(self.rainfall_predictor, "input_length", seq_len + future_days))
        daily_df, weather_meta = fetch_merged_daily_meteo(
            float(lat),
            float(lon),
            sequence_length=seq_len,
            forecast_days=future_days,
            # Étend la fenêtre à aujourd'hui + 7 jours : le modèle voit la pluie
            # PRÉVUE (déclencheur) en plus des antécédents observés.
            future_days=future_days,
        )

        missing = [c for c in RAINFALL_FEATURE_COLS if c not in daily_df.columns]
        if missing:
            raise ValueError(f"Features pluie manquantes dans la série live: {missing}")

        window = daily_df.iloc[-input_length:]
        if len(window) < input_length:
            raise ValueError(
                f"Série trop courte ({len(window)} jours, besoin de {input_length} "
                f"= {seq_len} observés + {future_days} prévus)"
            )
        sequence = window[RAINFALL_FEATURE_COLS].astype(np.float32).values
        sequence = np.nan_to_num(sequence, nan=0.0, posinf=0.0, neginf=0.0)

        batch = sequence[np.newaxis, ...]
        probability = float(self.rainfall_predictor.predict(batch)[0])
        risk_level = self.rainfall_predictor._get_risk_level(probability)

        static_features = get_static_features(resolved_commune) or {} if resolved_commune else {}
        risk_factors = get_risk_factors(resolved_commune) or {} if resolved_commune else {}
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Ligne "aujourd'hui" (jour d'émission) = avant les jours de prévision.
        issue_row = daily_df.iloc[-(future_days + 1)] if future_days > 0 else daily_df.iloc[-1]
        # Résumé de la prévision de pluie sur l'horizon.
        forecast_rows = daily_df.iloc[-future_days:] if future_days > 0 else daily_df.iloc[0:0]
        forecast_precip = forecast_rows["precipitation"].astype(float) if not forecast_rows.empty else None
        return {
            "commune": resolved_commune,
            "neighborhood": neighborhood,
            "prediction": {
                "flood_probability": probability,
                "risk_level": risk_level,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sequence_end_date": weather_meta.get("sequence_end_date"),
                "sequence_start_date": weather_meta.get("sequence_start_date"),
                "forecast_horizon_end": weather_meta.get("forecast_horizon_end"),
                "forecast_days": future_days,
                "forecast_precip_total_mm": (
                    round(float(forecast_precip.sum()), 1) if forecast_precip is not None else None
                ),
                "forecast_precip_max_mm": (
                    round(float(forecast_precip.max()), 1) if forecast_precip is not None else None
                ),
                "last_day_precipitation_mm": float(issue_row.get("precipitation", 0)),
                "antecedent_precip_7d_mm": float(issue_row.get("antecedent_precip_7d", 0)),
                "coordinates": {"lat": lat, "lon": lon},
                "source": "lstm_bamako_rainfall_live",
                "scope": "regional_city",
                "stale": False,
            },
            "context": {
                "static_features": static_features,
                "risk_factors": risk_factors,
                "zones_risque": commune_info.get("zones_risque"),
            },
            "metadata": {
                "latency_ms": duration_ms,
                "inference_mode": "live_weather",
                "model": "rainfall_only",
                "data_sources": weather_meta.get("data_sources", []),
                "feature_count": len(RAINFALL_FEATURE_COLS),
                "features_used": list(RAINFALL_FEATURE_COLS),
                "weather_error": weather_meta.get("weather_error"),
                "forecast_days_available": weather_meta.get("forecast_days_available"),
            },
        }

    def predict_live(
        self,
        commune: Optional[str] = None,
        neighborhood: Optional[str] = None,
        *,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict:
        """
        Reconstruit une fenêtre de 30 jours (pas journalier) avec météo récente
        puis infère avec lstm_model_bamako.h5.
        """
        start_time = time.perf_counter()
        resolved_commune = self._resolve_commune(commune, neighborhood)
        if not resolved_commune:
            raise ValueError("Commune ou quartier inconnu. Précisez 'commune' ou 'neighborhood'.")

        commune_info = BAMAKO_COMMUNES.get(resolved_commune, {})
        if latitude is not None and longitude is not None:
            lat, lon = float(latitude), float(longitude)
        else:
            lat = commune_info.get("lat")
            lon = commune_info.get("lon")
        if lat is None or lon is None:
            raise ValueError(f"Coordonnées manquantes pour {resolved_commune}")

        seq_len = self.lstm_predictor.sequence_length
        daily_df, weather_meta = fetch_merged_daily_meteo(
            float(lat),
            float(lon),
            sequence_length=seq_len,
            forecast_days=self.lstm_predictor.forecast_days,
        )
        sequence, feature_cols = build_model_sequence(
            daily_df,
            resolved_commune,
            seq_len,
            target_n_features=self._model_n_features(),
        )
        batch = sequence[np.newaxis, ...]
        probability = float(self.lstm_predictor.predict(batch)[0])
        risk_level = self.lstm_predictor._get_risk_level(probability)

        static_features = get_static_features(resolved_commune) or {}
        risk_factors = get_risk_factors(resolved_commune) or {}
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        last_row = daily_df.iloc[-1]
        return {
            "commune": resolved_commune,
            "neighborhood": neighborhood,
            "prediction": {
                "flood_probability": probability,
                "risk_level": risk_level,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sequence_end_date": weather_meta.get("sequence_end_date"),
                "sequence_start_date": weather_meta.get("sequence_start_date"),
                "last_day_precipitation_mm": float(last_row.get("precipitation", 0)),
                "antecedent_precip_7d_mm": float(last_row.get("antecedent_precip_7d", 0)),
                "coordinates": {"lat": lat, "lon": lon},
                "source": "lstm_bamako_live",
                "stale": False,
            },
            "context": {
                "static_features": static_features,
                "risk_factors": risk_factors,
                "zones_risque": commune_info.get("zones_risque"),
            },
            "metadata": {
                "latency_ms": duration_ms,
                "inference_mode": "live_weather",
                "data_sources": weather_meta.get("data_sources", []),
                "feature_count": len(feature_cols),
                "features_used": feature_cols,
                "weather_error": weather_meta.get("weather_error"),
                "forecast_days_available": weather_meta.get("forecast_days_available"),
            },
        }

    def _predict_from_cached_sequences(
        self,
        commune: Optional[str] = None,
        neighborhood: Optional[str] = None,
    ) -> Dict:
        start_time = time.perf_counter()
        resolved_commune = self._resolve_commune(commune, neighborhood)
        if not resolved_commune:
            raise ValueError("Commune ou quartier inconnu. Précisez 'commune' ou 'neighborhood'.")

        sequence_info = self.sequences_by_commune.get(resolved_commune)
        if not sequence_info:
            raise ValueError(f"Aucune séquence disponible pour {resolved_commune}.")

        sequence = sequence_info.sequence[np.newaxis, ...]
        probability = float(self.lstm_predictor.predict(sequence)[0])
        risk_level = self.lstm_predictor._get_risk_level(probability)

        commune_info = BAMAKO_COMMUNES.get(resolved_commune, {})
        static_features = get_static_features(resolved_commune) or {}
        risk_factors = get_risk_factors(resolved_commune) or {}

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "commune": resolved_commune,
            "neighborhood": neighborhood,
            "prediction": {
                "flood_probability": probability,
                "risk_level": risk_level,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sequence_end_date": sequence_info.end_date,
                "sequence_split": sequence_info.split,
                "coordinates": commune_info.get("lat") and commune_info.get("lon")
                and {"lat": commune_info["lat"], "lon": commune_info["lon"]}
                or None,
                "source": "lstm_bamako_cached",
                "stale": True,
            },
            "context": {
                "static_features": static_features,
                "risk_factors": risk_factors,
                "zones_risque": commune_info.get("zones_risque"),
            },
            "metadata": {
                "latency_ms": duration_ms,
                "inference_mode": "cached_npy",
                "last_sequence_loaded_at": self.last_loaded_at.isoformat(timespec="seconds")
                if self.last_loaded_at
                else None,
            },
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _resolve_commune(self, commune: Optional[str], neighborhood: Optional[str]) -> Optional[str]:
        if neighborhood:
            resolved = get_commune_from_neighborhood(neighborhood)
            if resolved:
                return resolved

        normalized_commune = normalize_commune_name(commune) if commune else None
        if normalized_commune:
            return normalized_commune

        # Si quartier inconnu mais ressemble à "Commune X"
        if neighborhood:
            normalized_commune = normalize_commune_name(neighborhood)
            if normalized_commune:
                return normalized_commune

        return None

    def list_supported_neighborhoods(self) -> Dict[str, list]:
        return BAMAKO_COMMUNE_NEIGHBORHOODS


