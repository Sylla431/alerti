"""
Bamako alert watcher — job périodique (horaire).

Évalue Alerti Pluie v1 + pluie journalière OpenWeather, puis envoie une push
FCM aux users Bamako (Supabase fcm_tokens → endpoint Vercel) si :
  - flood_probability > ALERT_PROB_THRESHOLD (défaut 0.5), ou
  - pluie prévue aujourd'hui/demain > ALERT_DAILY_RAIN_MM (défaut 20 mm)

Anti-spam : cooldown par type de déclencheur (défaut 3 h).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from utils.bamako_neighborhoods import (
    get_commune_from_neighborhood,
    normalize_commune_name,
)
from utils.config import (
    ALERT_COOLDOWN_HOURS,
    ALERT_DAILY_RAIN_MM,
    ALERT_PROB_THRESHOLD,
    ALERT_PUSH_URL,
    MALI_CITIES,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
)

TRIGGER_PROB = "prob_gt_50"
TRIGGER_RAIN = "daily_rain_gt_20"
MODEL_DISPLAY_NAME = "Alerti Pluie v1"


class BamakoAlertWatcher:
    """Évalue le risque Bamako et fan-out push si seuils dépassés."""

    def __init__(
        self,
        prediction_service=None,
        weather_service=None,
        cooldown_path: Optional[str] = None,
    ):
        backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if cooldown_path is None:
            cooldown_path = os.path.join(
                backend_root, "data", "bamako_alert_cooldown.json"
            )
        self.cooldown_path = cooldown_path
        self.status_path = os.path.join(
            backend_root, "data", "bamako_alert_status.json"
        )
        self.prediction_service = prediction_service
        self.weather_service = weather_service

        if self.prediction_service is None:
            from services.bamako_prediction_service import BamakoPredictionService

            self.prediction_service = BamakoPredictionService()
        if self.weather_service is None:
            from services.weather_forecast_service import WeatherForecastService

            self.weather_service = WeatherForecastService()

        bamako = MALI_CITIES["bamako"]
        self.lat = float(bamako["lat"])
        self.lon = float(bamako["lon"])

    # ------------------------------------------------------------------ #
    # Public
    # ------------------------------------------------------------------ #
    def run(self, dry_run: bool = False, force: bool = False) -> Dict[str, Any]:
        """Exécute une passe d'évaluation (+ envoi sauf dry_run)."""
        started = datetime.now(timezone.utc)
        proba, risk_level, pred_meta = self._evaluate_probability()
        daily_rain_mm, rain_day = self._evaluate_daily_rain()

        active_triggers: List[str] = []
        if proba > ALERT_PROB_THRESHOLD:
            active_triggers.append(TRIGGER_PROB)
        if daily_rain_mm > ALERT_DAILY_RAIN_MM:
            active_triggers.append(TRIGGER_RAIN)

        cooldown = self._load_cooldown()
        triggers_to_send: List[str] = []
        skipped_cooldown: List[str] = []
        for trigger in active_triggers:
            if force or self._cooldown_elapsed(cooldown, trigger):
                triggers_to_send.append(trigger)
            else:
                skipped_cooldown.append(trigger)

        map_status = self._derive_map_status(active_triggers, risk_level, proba)

        result: Dict[str, Any] = {
            "ok": True,
            "dry_run": dry_run,
            "force": force,
            "timestamp": started.isoformat(),
            "model": MODEL_DISPLAY_NAME,
            "flood_probability": round(float(proba), 4),
            "risk_level": risk_level,
            "daily_rain_mm": round(float(daily_rain_mm), 2),
            "rain_day": rain_day,
            "map_status": map_status,
            "thresholds": {
                "prob": ALERT_PROB_THRESHOLD,
                "daily_rain_mm": ALERT_DAILY_RAIN_MM,
                "cooldown_hours": ALERT_COOLDOWN_HOURS,
            },
            "active_triggers": active_triggers,
            "triggers_to_send": triggers_to_send,
            "skipped_cooldown": skipped_cooldown,
            "tokens_targeted": 0,
            "push": None,
            "prediction_meta": pred_meta,
        }

        if not triggers_to_send:
            result["action"] = "none"
            self._save_status_snapshot(result)
            return result

        title, body, data = self._build_message(
            triggers_to_send, proba, risk_level, daily_rain_mm, rain_day
        )
        tokens = self._fetch_bamako_tokens()
        result["tokens_targeted"] = len(tokens)
        result["notification"] = {"title": title, "body": body, "data": data}

        if dry_run:
            result["action"] = "dry_run"
            result["push"] = {"skipped": True, "reason": "dry_run"}
            self._save_status_snapshot(result)
            return result

        if not tokens:
            result["action"] = "no_tokens"
            result["push"] = {"skipped": True, "reason": "no_bamako_tokens"}
            self._save_status_snapshot(result)
            return result

        push_result = self._send_push(tokens, title, body, data)
        result["push"] = push_result
        result["action"] = "sent" if push_result.get("ok") else "send_failed"

        if push_result.get("ok"):
            now_iso = datetime.now(timezone.utc).isoformat()
            for trigger in triggers_to_send:
                cooldown[trigger] = now_iso
            self._save_cooldown(cooldown)

        self._save_status_snapshot(result)
        return result

    @staticmethod
    def _derive_map_status(
        active_triggers: List[str], risk_level: str, proba: float
    ) -> str:
        """Statut carte aligné sur les couleurs capteurs : urgence / alerte / normal."""
        risk = (risk_level or "").lower()
        if (
            TRIGGER_PROB in active_triggers
            or risk in ("critical", "high")
            or proba > ALERT_PROB_THRESHOLD
        ):
            return "urgence"
        if TRIGGER_RAIN in active_triggers or risk in ("medium", "moderate"):
            return "alerte"
        return "normal"

    def _save_status_snapshot(self, result: Dict[str, Any]) -> None:
        """Persiste le dernier résultat cron pour l'app mobile (couleurs carte)."""
        snapshot = {
            "ok": True,
            "updated_at": result.get("timestamp"),
            "model": result.get("model"),
            "flood_probability": result.get("flood_probability"),
            "risk_level": result.get("risk_level"),
            "daily_rain_mm": result.get("daily_rain_mm"),
            "rain_day": result.get("rain_day"),
            "map_status": result.get("map_status", "normal"),
            "active_triggers": result.get("active_triggers") or [],
            "action": result.get("action"),
            "scope": "regional_city",
        }
        try:
            os.makedirs(os.path.dirname(self.status_path), exist_ok=True)
            with open(self.status_path, "w", encoding="utf-8") as fh:
                json.dump(snapshot, fh, indent=2)
        except Exception as exc:
            print(f"[BamakoAlertWatcher] status save failed: {exc}")

    @classmethod
    def load_status_snapshot(cls) -> Dict[str, Any]:
        """Lit le dernier statut persisté (pour GET /api/bamako/alert-status)."""
        backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(backend_root, "data", "bamako_alert_status.json")
        if not os.path.exists(path):
            return {
                "ok": True,
                "available": False,
                "map_status": "normal",
                "message": "Aucun run cron encore disponible",
            }
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError("invalid status file")
            data["available"] = True
            data.setdefault("map_status", "normal")
            return data
        except Exception as exc:
            return {
                "ok": False,
                "available": False,
                "map_status": "normal",
                "error": str(exc),
            }

    # ------------------------------------------------------------------ #
    # Evaluation
    # ------------------------------------------------------------------ #
    def _evaluate_probability(self) -> Tuple[float, str, Dict]:
        pred = self.prediction_service.predict(
            commune="Commune I",
            latitude=self.lat,
            longitude=self.lon,
            model="rainfall",
        )
        prediction = pred.get("prediction") or {}
        proba = float(prediction.get("flood_probability") or 0.0)
        risk = str(prediction.get("risk_level") or "none")
        meta = {
            "source": prediction.get("source"),
            "scope": prediction.get("scope"),
            "inference_mode": (pred.get("metadata") or {}).get("inference_mode"),
        }
        return proba, risk, meta

    def _evaluate_daily_rain(self) -> Tuple[float, Optional[str]]:
        forecast = self.weather_service.get_forecast(self.lat, self.lon, days=2)
        days = forecast.get("forecasts") or []
        best_mm = 0.0
        best_day: Optional[str] = None
        for day in days:
            precip = day.get("precipitation") or {}
            if isinstance(precip, dict):
                total = float(precip.get("total") or 0.0)
            else:
                total = float(precip or 0.0)
            if total > best_mm:
                best_mm = total
                best_day = day.get("date")
        return best_mm, best_day

    # ------------------------------------------------------------------ #
    # Cooldown
    # ------------------------------------------------------------------ #
    def _load_cooldown(self) -> Dict[str, str]:
        if not os.path.exists(self.cooldown_path):
            return {}
        try:
            with open(self.cooldown_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            print(f"[BamakoAlertWatcher] cooldown load failed: {exc}")
            return {}

    def _save_cooldown(self, data: Dict[str, str]) -> None:
        try:
            os.makedirs(os.path.dirname(self.cooldown_path), exist_ok=True)
            with open(self.cooldown_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except Exception as exc:
            print(f"[BamakoAlertWatcher] cooldown save failed: {exc}")

    def _cooldown_elapsed(self, cooldown: Dict[str, str], trigger: str) -> bool:
        last = cooldown.get(trigger)
        if not last:
            return True
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return True
        return datetime.now(timezone.utc) - last_dt >= timedelta(hours=ALERT_COOLDOWN_HOURS)

    # ------------------------------------------------------------------ #
    # Tokens + push
    # ------------------------------------------------------------------ #
    def _is_bamako_localite(self, localite: Optional[str]) -> bool:
        """True si la localité vise Bamako (quartier/commune) ou le Mali (app Bamako).

        En pratique beaucoup de tokens Flutter sont enregistrés avec localite='Mali'
        (pays) plutôt qu'un quartier — on les inclut pour les alertes régionales.
        """
        if not localite:
            return False
        text = str(localite).strip()
        if not text:
            return False
        low = text.lower()
        if "bamako" in low or low in {"mali", "republic of mali", "république du mali"}:
            return True
        if get_commune_from_neighborhood(text):
            return True
        if normalize_commune_name(text):
            return True
        return False

    def _fetch_bamako_tokens(self) -> List[str]:
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            print("[BamakoAlertWatcher] SUPABASE_URL / SERVICE_ROLE_KEY manquants")
            return []

        url = f"{SUPABASE_URL}/rest/v1/fcm_tokens"
        headers = {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Accept": "application/json",
        }
        params = {
            "select": "fcm_token,localite,is_active",
            "is_active": "eq.true",
        }
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=45)
        except requests.RequestException as exc:
            print(f"[BamakoAlertWatcher] Supabase error: {exc}")
            return []

        if resp.status_code != 200:
            print(f"[BamakoAlertWatcher] Supabase HTTP {resp.status_code}: {resp.text[:200]}")
            return []

        rows = resp.json()
        if not isinstance(rows, list):
            return []

        tokens: List[str] = []
        seen = set()
        for row in rows:
            if not self._is_bamako_localite(row.get("localite")):
                continue
            token = (row.get("fcm_token") or "").strip()
            if not token or token in seen:
                continue
            seen.add(token)
            tokens.append(token)
        return tokens

    def _build_message(
        self,
        triggers: List[str],
        proba: float,
        risk_level: str,
        daily_rain_mm: float,
        rain_day: Optional[str],
    ) -> Tuple[str, str, Dict[str, str]]:
        has_prob = TRIGGER_PROB in triggers
        has_rain = TRIGGER_RAIN in triggers

        if has_prob and has_rain:
            title = "Alerte inondation Bamako"
            body = (
                f"Risque {risk_level} ({proba * 100:.0f} %) et forte pluie prévue "
                f"({daily_rain_mm:.0f} mm). Vigilance — {MODEL_DISPLAY_NAME}."
            )
            alert_type = "prob_and_rain"
        elif has_prob:
            title = "Alerte inondation Bamako — risque élevé"
            body = (
                f"Probabilité {proba * 100:.0f} % ({risk_level}). "
                f"Restez vigilant — {MODEL_DISPLAY_NAME}."
            )
            alert_type = TRIGGER_PROB
        else:
            title = "Forte pluie prévue à Bamako"
            day_label = f" ({rain_day})" if rain_day else ""
            body = (
                f"Pluie prévue > {ALERT_DAILY_RAIN_MM:.0f} mm{day_label} "
                f"({daily_rain_mm:.0f} mm). Vigilance inondation — {MODEL_DISPLAY_NAME}."
            )
            alert_type = TRIGGER_RAIN

        data = {
            "type": "flood_alert",
            "alert_type": alert_type,
            "model": MODEL_DISPLAY_NAME,
            "scope": "regional_city",
            "localite": "Bamako",
            "flood_probability": f"{proba:.4f}",
            "risk_level": risk_level,
            "daily_rain_mm": f"{daily_rain_mm:.2f}",
            "rain_day": rain_day or "",
        }
        return title, body, data

    def _send_push(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Dict[str, str],
    ) -> Dict[str, Any]:
        if not ALERT_PUSH_URL:
            return {"ok": False, "error": "ALERT_PUSH_URL manquant"}

        # Envoi par lots pour éviter des payloads trop gros
        batch_size = 100
        success = 0
        errors = 0
        details: List[Dict] = []

        for i in range(0, len(tokens), batch_size):
            batch = tokens[i : i + batch_size]
            payload = {
                "tokens": batch,
                "title": title,
                "body": body,
                "data": data,
            }
            try:
                resp = requests.post(
                    ALERT_PUSH_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=90,
                )
                body_json: Any
                try:
                    body_json = resp.json()
                except Exception:
                    body_json = {"raw": resp.text[:300]}

                if resp.status_code >= 200 and resp.status_code < 300:
                    success += int(body_json.get("successCount") or len(batch))
                    errors += int(body_json.get("errorCount") or 0)
                else:
                    errors += len(batch)
                details.append(
                    {
                        "status": resp.status_code,
                        "batch_size": len(batch),
                        "response": body_json,
                    }
                )
            except requests.RequestException as exc:
                errors += len(batch)
                details.append({"error": str(exc), "batch_size": len(batch)})

        return {
            "ok": success > 0,
            "success_count": success,
            "error_count": errors,
            "batches": details,
        }


__all__ = ["BamakoAlertWatcher", "TRIGGER_PROB", "TRIGGER_RAIN", "MODEL_DISPLAY_NAME"]
