"""
Client ClimateSERV (SERVIR/USAID) — série temporelle CHIRPS ponctuelle RÉELLE.

ClimateSERV expose l'archive CHIRPS (précipitations satellitaires, 0.05°) via une
API REST sans authentification. Une seule requête suffit pour récupérer plusieurs
années de pluie journalière sur un point/polygone — bien plus rapide que de
télécharger les milliers de GeoTIFF journaliers (serveur UCSB fortement throttlé).

Flux :
  1. submitDataRequest  -> renvoie un id de requête
  2. getDataRequestProgress (poll) -> [100.0] quand prêt
  3. getDataFromRequest  -> données journalières JSON

Réf. : https://climateserv.servirglobal.net/
"""
from __future__ import annotations

import math
import time
from datetime import date
from typing import Dict, Optional

import requests

# Types d'opération ClimateSERV
OP_MAX, OP_MIN, OP_MEDIAN, OP_RANGE, OP_SUM, OP_AVERAGE = 0, 1, 2, 3, 4, 5
# Datatype CHIRPS (pluie UCSB)
DATATYPE_CHIRPS = 0
# Intervalle journalier
INTERVAL_DAILY = 0


class ClimateServError(RuntimeError):
    pass


class ClimateServClient:
    """Client minimal pour récupérer une série CHIRPS journalière ponctuelle."""

    BASE_URL = "https://climateserv.servirglobal.net/chirps/"

    def __init__(self, timeout: int = 90, poll_interval: float = 2.0,
                 max_polls: int = 180, session: Optional[requests.Session] = None):
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_polls = max_polls
        self.session = session or requests.Session()

    @staticmethod
    def point_polygon(lat: float, lon: float, half_size: float = 0.03) -> dict:
        """Petit polygone GeoJSON (~2 pixels CHIRPS) centré sur (lat, lon)."""
        return {
            "type": "Polygon",
            "coordinates": [[
                [lon - half_size, lat - half_size],
                [lon + half_size, lat - half_size],
                [lon + half_size, lat + half_size],
                [lon - half_size, lat + half_size],
                [lon - half_size, lat - half_size],
            ]],
        }

    def fetch_daily(
        self,
        geometry: dict,
        start_date: date,
        end_date: date,
        operation: int = OP_AVERAGE,
        nan_to_zero: bool = True,
    ) -> Dict[str, Optional[float]]:
        """Récupère {"YYYY-MM-DD": mm} entre start_date et end_date inclus."""
        import json

        params = {
            "datatype": DATATYPE_CHIRPS,
            "begintime": start_date.strftime("%m/%d/%Y"),
            "endtime": end_date.strftime("%m/%d/%Y"),
            "intervaltype": INTERVAL_DAILY,
            "operationtype": operation,
            "geometry": json.dumps(geometry),
        }

        # 1) Soumission
        resp = self.session.get(
            self.BASE_URL + "submitDataRequest/", params=params, timeout=self.timeout
        )
        if resp.status_code != 200 or not resp.text.strip():
            raise ClimateServError(
                f"submitDataRequest a échoué: HTTP {resp.status_code} {resp.text[:120]}"
            )
        request_id = resp.text.strip().strip('[]"')
        if not request_id:
            raise ClimateServError("Aucun id de requête retourné par ClimateSERV")

        # 2) Attente de la fin du traitement
        progress = ""
        for _ in range(self.max_polls):
            p = self.session.get(
                self.BASE_URL + "getDataRequestProgress/",
                params={"id": request_id}, timeout=self.timeout,
            )
            progress = p.text
            if "100" in progress:
                break
            time.sleep(self.poll_interval)
        else:
            raise ClimateServError(
                f"Traitement ClimateSERV non terminé (dernier progrès: {progress[:60]})"
            )

        # 3) Récupération des données
        d = self.session.get(
            self.BASE_URL + "getDataFromRequest/",
            params={"id": request_id}, timeout=self.timeout,
        )
        payload = d.json()
        rows = payload.get("data", payload)
        if not isinstance(rows, list):
            raise ClimateServError(f"Réponse inattendue: {str(payload)[:120]}")

        series: Dict[str, Optional[float]] = {}
        for row in rows:
            iso = row.get("isodate") or row.get("date", "")
            # ClimateSERV renvoie MM/DD/YYYY
            try:
                mm, dd, yyyy = iso.split("/")
                key = f"{yyyy}-{mm}-{dd}"
            except ValueError:
                continue
            value = row.get("raw_value")
            if value is None:
                val_obj = row.get("value") or {}
                value = val_obj.get("avg") if isinstance(val_obj, dict) else val_obj
            if value is None or (isinstance(value, float) and math.isnan(value)):
                series[key] = 0.0 if nan_to_zero else None
            else:
                series[key] = max(0.0, float(value))
        return series


__all__ = ["ClimateServClient", "ClimateServError"]
