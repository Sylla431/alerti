"""
Africa Data Service - Fetches meteorological data optimized for Africa
Data sources: CHIRPS, GPM IMERG, TAMSAT
"""
import requests
from datetime import datetime, date as date_cls, timedelta
import json
import numpy as np
from utils.config import (
    CHIRPS_BASE_URL, GPM_BASE_URL, 
    EARTHDATA_USERNAME, EARTHDATA_PASSWORD
)

try:
    from services.chirps_reader import CHIRPSDailyReader, RASTERIO_AVAILABLE
except Exception as _exc:  # pragma: no cover
    CHIRPSDailyReader = None  # type: ignore
    RASTERIO_AVAILABLE = False


def _to_date(value):
    """Normalise un datetime/date en date."""
    if isinstance(value, datetime):
        return value.date()
    return value


class AfricaDataService:
    """Service for fetching Africa-specific flood forecasting data"""

    def __init__(self):
        self.chirps_base_url = CHIRPS_BASE_URL
        self.gpm_base_url = GPM_BASE_URL
        self.earthdata_username = EARTHDATA_USERNAME
        self.earthdata_password = EARTHDATA_PASSWORD

        self._chirps_reader = None
        if CHIRPSDailyReader is not None and RASTERIO_AVAILABLE:
            try:
                self._chirps_reader = CHIRPSDailyReader(base_url=self.chirps_base_url)
            except Exception as exc:
                print(f"[CHIRPS] Initialisation du lecteur impossible: {exc}")
                self._chirps_reader = None

    def get_chirps_precipitation(self, lat, lon, start_date, end_date):
        """Précipitations journalières CHIRPS RÉELLES (GeoTIFF p05, ~5 km).

        Chaque jour vient de la version finale si elle est publiée (~4 semaines
        de retard), sinon de la préliminaire (~1 semaine). Un jour publié dans
        aucune des deux est compté à 0, marqué `is_real: False` et listé dans
        `missing_dates` : à l'appelant de le combler par une autre source.
        """
        start = _to_date(start_date)
        end = _to_date(end_date)

        dates = []
        current_date = start
        while current_date <= end:
            dates.append(current_date)
            current_date += timedelta(days=1)

        series = {}
        if self._chirps_reader is None:
            print("[CHIRPS] Lecteur réel indisponible (rasterio manquant ?) — aucun jour CHIRPS.")
        else:
            try:
                series = self._chirps_reader.get_series_with_source(lat, lon, start, end)
            except Exception as exc:
                print(f"[CHIRPS] Erreur lecture {start.isoformat()} → {end.isoformat()}: {exc}")

        daily_precip = []
        total_precipitation = 0.0
        final_days = 0
        prelim_days = 0
        missing_dates = []

        for d in dates:
            amount, product = series.get(d.isoformat(), (None, None))
            if amount is None:
                missing_dates.append(d.isoformat())
                amount = 0.0
            elif product == 'final':
                final_days += 1
            else:
                prelim_days += 1

            daily_precip.append({
                'date': d.isoformat(),
                'precipitation': round(float(amount), 3),
                'is_real': product is not None,
                'product': product,
            })
            total_precipitation += float(amount)

        real_days = final_days + prelim_days
        source = 'CHIRPS'
        if missing_dates and not real_days:
            source = 'CHIRPS (aucun jour publié)'
        elif missing_dates:
            source = 'CHIRPS (partiel: jours non publiés comptés à 0)'

        return {
            'source': source,
            'location': {'lat': lat, 'lon': lon},
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'total_precipitation': round(total_precipitation, 3),
            'average_daily_precipitation': (
                round(total_precipitation / len(dates), 3) if dates else 0
            ),
            'daily_data': daily_precip,
            'real_days': real_days,
            'final_days': final_days,
            'prelim_days': prelim_days,
            'missing_dates': missing_dates,
            'note': (
                f'{final_days} jours CHIRPS finals, {prelim_days} préliminaires, '
                f'{len(missing_dates)} non publiés (comptés à 0)'
            ),
        }
    
    def get_gpm_imerg_precipitation(self, lat, lon, hours_back=72):
        """Get GPM IMERG near real-time precipitation"""
        try:
            # GPM IMERG provides 30-minute intervals
            # Best for recent/historical data
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)
            
            # For production, use NASA Earthdata API
            # Format: /data/GPM_L3/GPM_3IMERGHH.06/
            params = {
                'latitude': lat,
                'longitude': lon,
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            }
            
            # Simulated data for now
            return {
                'source': 'GPM_IMERG',
                'location': {'lat': lat, 'lon': lon},
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'precipitation_72h': self._simulate_gpm_data(hours_back),
                'precipitation_rate': np.random.uniform(0, 5),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error fetching GPM IMERG data: {e}")
            return None
    
    def get_tamsat_precipitation(self, lat, lon, date):
        """Get TAMSAT precipitation - Africa-specific"""
        try:
            # TAMSAT provides Africa-focused daily precipitation
            # Format: /data/rfe/v3.1/daily/{year}/rfe{year}{month:02d}{day:02d}.v3.1.nc
            file_url = (
                f"https://www.tamsat.org.uk/data/rfe/v3.1/daily/"
                f"{date.year}/rfe{date.year}{date.month:02d}{date.day:02d}.v3.1.nc"
            )
            
            # In production, download and process NetCDF
            return {
                'source': 'TAMSAT',
                'location': {'lat': lat, 'lon': lon},
                'date': date.isoformat(),
                'precipitation': self._simulate_tamsat_data(lat, lon, date),
                'note': 'Replace with actual TAMSAT NetCDF processing'
            }
        except Exception as e:
            print(f"Error fetching TAMSAT data: {e}")
            return None
    
    def get_comprehensive_meteo_data(self, lat, lon, days_back=30):
        """Get comprehensive meteorological data from multiple sources"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Get CHIRPS data (primary source)
        chirps_data = self.get_chirps_precipitation(lat, lon, start_date, end_date)
        
        # Get recent GPM data
        gpm_data = self.get_gpm_imerg_precipitation(lat, lon, hours_back=72)
        
        return {
            'chirps': chirps_data,
            'gpm_imerg': gpm_data,
            'timestamp': datetime.now().isoformat()
        }
    
    def _simulate_gpm_data(self, hours):
        """Simulate GPM IMERG data"""
        import random
        # Simulate precipitation over time period
        return random.uniform(0, hours * 0.5)  # mm over time period
    
    def _simulate_tamsat_data(self, lat, lon, date):
        """Simulate TAMSAT data"""
        import random
        month = date.month
        base = 2.0 if month in [6, 7, 8, 9] else 0.3
        return random.uniform(0, base * 2)

