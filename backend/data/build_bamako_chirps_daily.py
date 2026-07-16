"""
Construit une série journalière de PLUIE RÉELLE pour Bamako à partir de CHIRPS.

Deux méthodes (données CHIRPS identiques, ~5 km) :

  --method climateserv  (DÉFAUT, recommandé)
      API ClimateSERV (SERVIR/USAID). Récupère toute la période en UNE requête
      (~45 s pour 5 ans). Aucune auth, aucun téléchargement de fichiers.

  --method tiles
      Télécharge les GeoTIFF africa_daily jour par jour (serveur UCSB fortement
      throttlé : très lent pour de longues périodes, mais mis en cache disque).

Sortie :
    backend/data/raw/chirps/bamako_chirps_daily.csv   (colonnes: date, precipitation)

Consommé automatiquement par prepare_bamako_rainfall_only.py (source "chirps").

Usage :
    python data/build_bamako_chirps_daily.py                          # 2020→2024, ClimateSERV
    python data/build_bamako_chirps_daily.py --start 2021-01-01 --end 2024-10-31
    python data/build_bamako_chirps_daily.py --method tiles --workers 12
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import MALI_CITIES

BAMAKO = MALI_CITIES["bamako"]  # {'lat': 12.6392, 'lon': -8.0029, ...}

DEFAULT_START = date(2020, 1, 1)
DEFAULT_END = date(2024, 12, 31)


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _fetch_climateserv(lat: float, lon: float, start_date: date, end_date: date) -> dict:
    """Récupère la série via ClimateSERV, ANNÉE PAR ANNÉE.

    Les requêtes multi-années sont parfois tronquées côté serveur (trous en
    2020-2021 observés). Découper par année rend la récupération fiable et
    permet de contrôler la complétude de chaque tranche.
    """
    from services.climateserv_client import ClimateServClient

    client = ClimateServClient()
    geom = client.point_polygon(lat, lon, half_size=0.03)
    print("  🌐 Source : API ClimateSERV (CHIRPS, découpage annuel)")

    series: dict = {}
    for year in range(start_date.year, end_date.year + 1):
        y_start = max(start_date, date(year, 1, 1))
        y_end = min(end_date, date(year, 12, 31))
        expected = (y_end - y_start).days + 1

        chunk = client.fetch_daily(geom, y_start, y_end)
        # Une tranche annuelle doit être quasi complète ; on retente une fois sinon.
        if len(chunk) < expected - 3:
            print(f"    ⟳ {year}: {len(chunk)}/{expected} jours, nouvel essai…")
            chunk = client.fetch_daily(geom, y_start, y_end)

        got = len(chunk)
        flag = "✅" if got >= expected - 3 else "⚠️"
        print(f"    {flag} {year}: {got}/{expected} jours")
        series.update(chunk)

    return series


def _fetch_tiles(lat: float, lon: float, start_date: date, end_date: date, workers: int) -> dict:
    from services.chirps_reader import CHIRPSDailyReader, RASTERIO_AVAILABLE

    if not RASTERIO_AVAILABLE:
        raise SystemExit("❌ rasterio indisponible pour --method tiles. pip install rasterio")
    reader = CHIRPSDailyReader(extent="africa")
    print(f"  🗂️  Source : GeoTIFF africa_daily (téléchargement, {workers} threads)")
    return reader.get_series_concurrent(lat, lon, start_date, end_date, max_workers=workers)


def build(start_date: date, end_date: date, method: str, workers: int, output_csv: str) -> str:
    lat, lon = BAMAKO["lat"], BAMAKO["lon"]
    n_days = (end_date - start_date).days + 1

    print("=" * 60)
    print("🌧️  CONSTRUCTION SÉRIE PLUIE RÉELLE — CHIRPS (Bamako-ville)")
    print("=" * 60)
    print(f"  📍 Point : lat={lat}, lon={lon} (centre Bamako)")
    print(f"  📅 Période : {start_date} → {end_date} ({n_days} jours)")

    if method == "climateserv":
        series = _fetch_climateserv(lat, lon, start_date, end_date)
    else:
        series = _fetch_tiles(lat, lon, start_date, end_date, workers)

    rows, missing = [], []
    for day_iso, value in sorted(series.items()):
        if value is None:
            missing.append(day_iso)
            continue
        rows.append({"date": day_iso, "precipitation": round(float(value), 3)})

    if not rows:
        raise SystemExit("❌ Aucune donnée CHIRPS récupérée (plage non publiée ?)")

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Série journalière CONTINUE : réindexer sur toute la plage (les séquences
    # de 30 jours supposent des jours consécutifs). Les trous résiduels → 0.
    full_index = pd.date_range(start_date, end_date, freq="D")
    df = (
        df.set_index("date")
        .reindex(full_index)
        .rename_axis("date")
        .reset_index()
    )
    n_filled = int(df["precipitation"].isna().sum())
    df["precipitation"] = df["precipitation"].fillna(0.0)

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)

    total = df["precipitation"].sum()
    n_rain = int((df["precipitation"] > 0).sum())
    print("\n" + "=" * 60)
    print("✅ SÉRIE CONSTRUITE")
    print("=" * 60)
    print(f"  📄 CSV : {output_csv}")
    print(f"  📊 Jours : {len(df)} | avec pluie : {n_rain} | comblés à 0 : {n_filled}")
    print(f"  🌧️  Cumul total : {total:.0f} mm | moy : {total/len(df):.2f} mm/j "
          f"(~{total/max(1,(len(df)/365)):.0f} mm/an)")
    print("\n📝 Prochaine étape :")
    print("   python data/prepare_bamako_rainfall_only.py --source chirps")
    return output_csv


def main():
    parser = argparse.ArgumentParser(description="Série pluie journalière CHIRPS réelle (Bamako)")
    parser.add_argument("--start", type=_parse_date, default=DEFAULT_START,
                        help="Date de début YYYY-MM-DD (défaut 2020-01-01)")
    parser.add_argument("--end", type=_parse_date, default=DEFAULT_END,
                        help="Date de fin YYYY-MM-DD (défaut 2024-12-31)")
    parser.add_argument("--method", choices=["climateserv", "tiles"], default="climateserv",
                        help="Source des données (défaut climateserv)")
    parser.add_argument("--workers", type=int, default=12,
                        help="Threads (méthode tiles uniquement, défaut 12)")
    parser.add_argument("--out", default=None,
                        help="Chemin CSV de sortie (défaut raw/chirps/bamako_chirps_daily.csv)")
    args = parser.parse_args()

    if args.out is None:
        data_dir = os.path.dirname(os.path.abspath(__file__))
        args.out = os.path.join(data_dir, "raw", "chirps", "bamako_chirps_daily.csv")

    build(args.start, args.end, args.method, args.workers, args.out)


if __name__ == "__main__":
    main()
