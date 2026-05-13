"""
Télécharge les précipitations journalières pour les 6 communes de Bamako
via l'API OpenWeatherMap (One Call 3.0 Day Summary).

Usage :
    cd backend/data
    python download_openweather_precip.py --start-date 2023-01-01 --end-date 2023-12-31

L'API Day Summary retourne une observation journalière consolidée qui inclut
les précipitations totales, les températures et autres paramètres. Nous
agrégeons ces informations par commune et stockons un CSV compatible avec
prepare_bamako_data.py.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

# Ajouter backend au path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.config import OPENWEATHERMAP_API_KEY  # noqa: E402
from utils.bamako_communes import BAMAKO_COMMUNES  # noqa: E402


class OpenWeatherPrecipDownloader:
    """Téléchargeur OpenWeather pour précipitations journalières."""

    BASE_URL = "https://api.openweathermap.org/data/3.0/onecall/day_summary"

    def __init__(self, start_date: date, end_date: date, delay: float = 1.2, retries: int = 3):
        self.api_key = OPENWEATHERMAP_API_KEY
        if not self.api_key:
            raise ValueError("OPENWEATHERMAP_API_KEY n'est pas configurée. Ajoutez-la dans votre .env.")

        if start_date > end_date:
            raise ValueError("start_date doit être antérieure ou égale à end_date")

        self.start_date = start_date
        self.end_date = end_date
        self.delay = delay
        self.retries = retries

        data_dir = os.path.dirname(__file__)
        self.output_dir = os.path.join(data_dir, "raw", "openweather")
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, "bamako_communes_openweather_daily.csv")

        self.session = requests.Session()

    def daterange(self) -> List[date]:
        days = []
        current = self.start_date
        while current <= self.end_date:
            days.append(current)
            current += timedelta(days=1)
        return days

    def fetch_day_summary(self, lat: float, lon: float, target_date: date) -> Optional[Dict]:
        """Appelle l'API day_summary pour une coordonnée/date."""
        params = {
            "lat": lat,
            "lon": lon,
            "date": target_date.strftime("%Y-%m-%d"),
            "appid": self.api_key,
            "units": "metric",
        }

        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=15)
                if response.status_code == 429:
                    wait_time = self.delay * attempt * 2
                    print(f"  ⚠️  Rate limit (429). Pause {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                payload = response.json()

                # L'API retourne une clé "data" (liste) contenant le résumé journalier
                day_data = None
                if isinstance(payload, dict):
                    data_block = payload.get("data")
                    if isinstance(data_block, list) and data_block:
                        day_data = data_block[0]
                    elif isinstance(data_block, dict):
                        day_data = data_block
                    else:
                        day_data = payload  # fallback
                else:
                    day_data = payload

                if not isinstance(day_data, dict):
                    return None

                return day_data
            except requests.exceptions.RequestException as exc:
                wait_time = self.delay * attempt
                print(f"  ⚠️  Erreur réseau ({exc}). Retry dans {wait_time:.1f}s...")
                time.sleep(wait_time)
            except ValueError as exc:
                print(f"  ⚠️  Erreur de parsing JSON : {exc}")
                return None

        return None

    @staticmethod
    def _extract_precipitation(day_data: Dict) -> Tuple[float, Optional[float], Optional[str]]:
        """Extrait la pluie totale (mm) depuis les différentes structures possibles."""
        precipitation_hours = None
        precipitation_type = None

        if not isinstance(day_data, dict):
            return 0.0, precipitation_hours, precipitation_type

        precip_total = 0.0

        # Cas 1 : bloc "precipitation"
        precipitation_block = day_data.get("precipitation")
        if isinstance(precipitation_block, dict):
            precipitation_hours = precipitation_block.get("hours")
            precipitation_type = precipitation_block.get("type") or precipitation_block.get("mode")

            for key in ["total", "sum", "rain", "snow"]:
                value = precipitation_block.get(key)
                if isinstance(value, (int, float)):
                    if key == "total" or key == "sum":
                        precip_total = float(value)
                        break
                    else:
                        precip_total += float(value)

        # Cas 2 : champs séparés rain/snow
        rain_block = day_data.get("rain")
        snow_block = day_data.get("snow")

        if (precip_total == 0.0) and isinstance(rain_block, dict):
            precip_total += float(rain_block.get("sum") or rain_block.get("total") or 0.0)
        if isinstance(snow_block, dict):
            precip_total += float(snow_block.get("sum") or snow_block.get("total") or 0.0)

        # Cas 3 : champ direct precipitation_total
        direct_value = day_data.get("precipitation_total") or day_data.get("prec")
        if isinstance(direct_value, (int, float)) and precip_total == 0.0:
            precip_total = float(direct_value)

        return round(max(precip_total, 0.0), 3), precipitation_hours, precipitation_type

    @staticmethod
    def _extract_temperature(day_data: Dict) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        temps = day_data.get("temperature") or day_data.get("temp")
        if isinstance(temps, dict):
            return (
                temps.get("min") or temps.get("minimal"),
                temps.get("max") or temps.get("maximal"),
                temps.get("mean") or temps.get("day"),
            )
        return None, None, None

    def download(self, force_refresh: bool = False, target_communes: Optional[List[str]] = None) -> pd.DataFrame:
        """Télécharge la plage demandée et sauvegarde un CSV cumulatif."""
        existing_keys = set()

        if os.path.exists(self.output_file):
            existing_subset = pd.read_csv(
                self.output_file,
                usecols=["date", "commune"],
                parse_dates=["date"]
            )
            existing_keys = set(
                (row.date.date(), row.commune)
                for row in existing_subset.itertuples()
            )
            print(f"📄 Fichier existant détecté : {self.output_file} ({len(existing_subset)} lignes)")

        communes = list(BAMAKO_COMMUNES.items())
        if target_communes:
            target_set = set(target_communes)
            communes = [(name, info) for name, info in communes if name in target_set]
            print(f"📍 Limité aux communes : {', '.join(target_set)}")

        new_records = []
        total_calls = 0
        days = self.daterange()
        print(f"\n🌧️  Téléchargement OpenWeather du {days[0]} au {days[-1]} ({len(days)} jours)")

        for current_day in days:
            for commune, coords in communes:
                key = (current_day, commune)
                if key in existing_keys and not force_refresh:
                    continue

                print(f"  → {commune} | {current_day} ...", end=" ")
                day_data = self.fetch_day_summary(coords["lat"], coords["lon"], current_day)
                total_calls += 1
                time.sleep(self.delay)  # respect du rate limit

                if not day_data:
                    print("❌")
                    continue

                precip_mm, precip_hours, precip_type = self._extract_precipitation(day_data)
                t_min, t_max, t_mean = self._extract_temperature(day_data)
                humidity = None
                pressure = None
                wind_speed = None

                humidity_block = day_data.get("humidity")
                if isinstance(humidity_block, dict):
                    humidity = humidity_block.get("mean") or humidity_block.get("avg")
                elif isinstance(humidity_block, (int, float)):
                    humidity = humidity_block

                pressure_block = day_data.get("pressure")
                if isinstance(pressure_block, dict):
                    pressure = pressure_block.get("mean") or pressure_block.get("avg")
                elif isinstance(pressure_block, (int, float)):
                    pressure = pressure_block

                wind_block = day_data.get("wind")
                if isinstance(wind_block, dict):
                    wind_speed = wind_block.get("max") or wind_block.get("mean") or wind_block.get("speed")
                elif isinstance(wind_block, (int, float)):
                    wind_speed = wind_block

                record = {
                    "date": current_day,
                    "commune": commune,
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "precipitation": precip_mm,
                    "precipitation_hours": precip_hours,
                    "precipitation_type": precip_type,
                    "temperature_min": t_min,
                    "temperature_max": t_max,
                    "temperature_mean": t_mean,
                    "humidity_mean": humidity,
                    "pressure_mean": pressure,
                    "wind_speed_max": wind_speed,
                    "source": "openweather_day_summary",
                }
                new_records.append(record)
                self._append_record(record)
                existing_keys.add(key)
                print(f"{precip_mm:.2f} mm")

        if not new_records:
            print("\n✅ Rien à ajouter, le fichier est déjà à jour.")
            combined = pd.read_csv(self.output_file, parse_dates=["date"]) if os.path.exists(self.output_file) else pd.DataFrame()
            return combined

        # Recharger le fichier complet pour garantir l'ordre et la déduplication
        combined = pd.read_csv(self.output_file, parse_dates=["date"])
        combined = combined.drop_duplicates(subset=["date", "commune"]).sort_values(["date", "commune"])
        combined.to_csv(self.output_file, index=False, date_format="%Y-%m-%d")

        print(f"\n✅ Sauvegardé : {self.output_file}")
        print(f"   Total lignes : {len(combined)}")
        print(f"   Appels API : {total_calls}")
        return combined

    def _append_record(self, record: Dict) -> None:
        """Écrit immédiatement une ligne dans le CSV pour éviter les pertes en cas d'arrêt."""
        file_exists = os.path.exists(self.output_file)
        df_row = pd.DataFrame([record])
        df_row.to_csv(
            self.output_file,
            mode='a',
            header=not file_exists,
            index=False,
            date_format="%Y-%m-%d"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Télécharge les précipitations journalières OpenWeather pour Bamako.")
    parser.add_argument("--start-date", type=str, help="Date de début (YYYY-MM-DD).")
    parser.add_argument("--end-date", type=str, help="Date de fin (YYYY-MM-DD). Par défaut = aujourd'hui.")
    parser.add_argument("--days", type=int, default=60, help="Nombre de jours à récupérer si start-date non fourni (par défaut 60).")
    parser.add_argument("--delay", type=float, default=1.2, help="Pause entre les appels API (secondes).")
    parser.add_argument("--force", action="store_true", help="Force la réécriture même si la date existe déjà.")
    parser.add_argument("--communes", nargs="*", help="Liste optionnelle des communes à traiter.")
    return parser.parse_args()


def main():
    args = parse_args()

    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date() if args.end_date else datetime.utcnow().date()
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    else:
        start_date = end_date - timedelta(days=args.days - 1)

    downloader = OpenWeatherPrecipDownloader(start_date=start_date, end_date=end_date, delay=args.delay)

    try:
        downloader.download(force_refresh=args.force, target_communes=args.communes)
    except ValueError as exc:
        print(f"❌ {exc}")


if __name__ == "__main__":
    main()

