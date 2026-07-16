"""
CHIRPS Daily Reader — téléchargement et lecture des précipitations journalières RÉELLES.

Source : CHIRPS-2.0 Global Daily GeoTIFF (0.05°, ~5 km), UC Santa Barbara CHG.
URL type :
  {base}/global_daily/tifs/p05/{YYYY}/chirps-v2.0.{YYYY}.{MM}.{DD}.tif.gz

Les fichiers journaliers sont téléchargés (~2.4 Mo/jour) puis mis en cache sur
disque. La lecture d'un pixel se fait via rasterio (GDAL /vsigzip/ : pas besoin
de décompresser le fichier sur disque).

Latence : les données finales CHIRPS ont ~3 semaines de retard. Les jours non
encore publiés renvoient None (le producteur du 404). C'est à l'appelant de
décider quoi faire des jours manquants (ex. enrichissement OpenWeather).
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Dict, List, Optional

import requests

try:  # rasterio est requis pour lire les GeoTIFF ; import paresseux et tolérant
    import rasterio

    RASTERIO_AVAILABLE = True
    _RASTERIO_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - dépend de l'environnement
    rasterio = None  # type: ignore
    RASTERIO_AVAILABLE = False
    _RASTERIO_IMPORT_ERROR = str(exc)

try:
    from utils.config import CHIRPS_BASE_URL
except Exception:  # fallback si config indisponible
    CHIRPS_BASE_URL = "https://data.chc.ucsb.edu/products/CHIRPS-2.0"

# Valeur "no data" CHIRPS (masque océans / hors couverture)
CHIRPS_NODATA_THRESHOLD = -9000.0


class CHIRPSDailyReader:
    """Télécharge, met en cache et lit les précipitations journalières CHIRPS.

    `extent` :
      - "africa" (défaut) : tuiles africa_daily (~1 Mo/jour, extent Afrique) —
        recommandé pour Bamako/Mali (plus léger, mêmes valeurs que global) ;
      - "global"          : tuiles global_daily (~2,4 Mo/jour, couverture monde).
    """

    DAILY_PATH_TEMPLATE = (
        "{base}/{extent}_daily/tifs/p05/{year}/chirps-v2.0.{year}.{month:02d}.{day:02d}.tif.gz"
    )
    VALID_EXTENTS = ("africa", "global")

    def __init__(
        self,
        base_url: str = CHIRPS_BASE_URL,
        cache_dir: Optional[str] = None,
        session: Optional[requests.Session] = None,
        timeout: int = 90,
        extent: str = "africa",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        if extent not in self.VALID_EXTENTS:
            raise ValueError(f"extent doit être parmi {self.VALID_EXTENTS}")
        self.extent = extent

        if cache_dir is None:
            # backend/data/raw/chirps/daily
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(backend_dir, "data", "raw", "chirps", "daily")
        # Sous-dossier par extent pour éviter tout mélange global/africa
        self.cache_dir = os.path.join(cache_dir, extent)
        os.makedirs(self.cache_dir, exist_ok=True)

        # Petit cache mémoire {"YYYY-MM-DD": disponible?} pour éviter de re-tenter
        # des 404 répétés dans un même run.
        self._unavailable: set[str] = set()

    # ------------------------------------------------------------------ #
    # Téléchargement / cache
    # ------------------------------------------------------------------ #
    def _daily_url(self, d: date) -> str:
        return self.DAILY_PATH_TEMPLATE.format(
            base=self.base_url, extent=self.extent,
            year=d.year, month=d.month, day=d.day,
        )

    def _local_path(self, d: date) -> str:
        year_dir = os.path.join(self.cache_dir, str(d.year))
        os.makedirs(year_dir, exist_ok=True)
        return os.path.join(
            year_dir, f"chirps-v2.0.{d.year}.{d.month:02d}.{d.day:02d}.tif.gz"
        )

    def _ensure_file(self, d: date) -> Optional[str]:
        """Retourne le chemin local du .tif.gz, le téléchargeant si nécessaire.

        Retourne None si le fichier n'est pas (encore) publié (404) ou en cas
        d'erreur réseau.
        """
        key = d.isoformat()
        if key in self._unavailable:
            return None

        local_path = self._local_path(d)
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            return local_path

        url = self._daily_url(d)
        try:
            resp = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            print(f"[CHIRPS] Erreur réseau {key}: {exc}")
            return None

        if resp.status_code == 404:
            # Jour non encore publié (latence CHIRPS) ou hors archive
            self._unavailable.add(key)
            return None
        if resp.status_code != 200 or not resp.content:
            print(f"[CHIRPS] {key}: HTTP {resp.status_code}")
            self._unavailable.add(key)
            return None

        tmp_path = local_path + ".part"
        with open(tmp_path, "wb") as fh:
            fh.write(resp.content)
        os.replace(tmp_path, local_path)
        return local_path

    # ------------------------------------------------------------------ #
    # Lecture pixel
    # ------------------------------------------------------------------ #
    def get_daily_precip(self, lat: float, lon: float, d: date) -> Optional[float]:
        """Précipitation journalière réelle (mm) pour (lat, lon) ou None si indispo."""
        if not RASTERIO_AVAILABLE:
            raise RuntimeError(
                "rasterio requis pour lire CHIRPS ("
                f"{_RASTERIO_IMPORT_ERROR}). Installez: pip install rasterio"
            )

        local_path = self._ensure_file(d)
        if local_path is None:
            return None

        try:
            # GDAL peut lire directement le .gz via /vsigzip/ (pas de décompression disque)
            with rasterio.open(f"/vsigzip/{local_path}") as src:
                value = float(next(src.sample([(lon, lat)]))[0])
        except Exception as exc:
            print(f"[CHIRPS] Lecture échouée {d.isoformat()} @ {local_path}: {exc}")
            return None

        if value < CHIRPS_NODATA_THRESHOLD:
            return 0.0
        return max(0.0, value)

    def get_series(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> Dict[str, Optional[float]]:
        """Série {"YYYY-MM-DD": mm ou None} entre start_date et end_date inclus."""
        series: Dict[str, Optional[float]] = {}
        cursor = start_date
        while cursor <= end_date:
            series[cursor.isoformat()] = self.get_daily_precip(lat, lon, cursor)
            cursor += timedelta(days=1)
        return series

    def get_series_concurrent(
        self,
        lat: float,
        lon: float,
        start_date: date,
        end_date: date,
        max_workers: int = 16,
        progress_every: int = 100,
    ) -> Dict[str, Optional[float]]:
        """Comme get_series mais télécharge en parallèle (serveur CHIRPS throttlé).

        La lecture pixel reste faite après téléchargement. Retourne un dict
        ordonné par date.
        """
        if not RASTERIO_AVAILABLE:
            raise RuntimeError(
                "rasterio requis pour lire CHIRPS ("
                f"{_RASTERIO_IMPORT_ERROR}). Installez: pip install rasterio"
            )

        days: List[date] = []
        cursor = start_date
        while cursor <= end_date:
            days.append(cursor)
            cursor += timedelta(days=1)

        # 1) Téléchargement concurrent (I/O bound)
        done = {"n": 0}

        def _fetch(d: date):
            path = self._ensure_file(d)
            done["n"] += 1
            if progress_every and done["n"] % progress_every == 0:
                print(f"[CHIRPS] {done['n']}/{len(days)} fichiers récupérés…")
            return d, path

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            fetched = list(pool.map(_fetch, days))

        # 2) Extraction pixel (rapide, séquentielle)
        series: Dict[str, Optional[float]] = {}
        for d, path in fetched:
            if path is None:
                series[d.isoformat()] = None
                continue
            try:
                with rasterio.open(f"/vsigzip/{path}") as src:
                    value = float(next(src.sample([(lon, lat)]))[0])
                series[d.isoformat()] = 0.0 if value < CHIRPS_NODATA_THRESHOLD else max(0.0, value)
            except Exception as exc:
                print(f"[CHIRPS] Lecture échouée {d.isoformat()}: {exc}")
                series[d.isoformat()] = None
        return series


__all__ = ["CHIRPSDailyReader", "RASTERIO_AVAILABLE"]
