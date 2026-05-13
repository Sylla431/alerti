"""
Africa Data Service - Fetches meteorological data optimized for Africa
Data sources: CHIRPS, GPM IMERG, TAMSAT
"""
import requests
import os
from datetime import datetime, timedelta
import json
import numpy as np
from utils.config import (
    CHIRPS_BASE_URL, GPM_BASE_URL, 
    EARTHDATA_USERNAME, EARTHDATA_PASSWORD
)

class AfricaDataService:
    """Service for fetching Africa-specific flood forecasting data"""
    
    def __init__(self):
        self.chirps_base_url = CHIRPS_BASE_URL
        self.gpm_base_url = GPM_BASE_URL
        self.earthdata_username = EARTHDATA_USERNAME
        self.earthdata_password = EARTHDATA_PASSWORD
    
    def get_chirps_precipitation(self, lat, lon, start_date, end_date):
        """Get CHIRPS precipitation data - BEST for Africa"""
        try:
            # CHIRPS provides daily data in NetCDF format
            # Format: /global_daily/netcdf/p05/chirps-v2.0.YYYY.MM.DD.days_p05.nc
            
            dates = []
            current_date = start_date
            while current_date <= end_date:
                dates.append(current_date)
                current_date += timedelta(days=1)
            
            total_precipitation = 0
            daily_precip = []
            
            for date in dates:
                # CHIRPS file URL
                file_url = (
                    f"{self.chirps_base_url}/"
                    f"global_daily/netcdf/p05/"
                    f"chirps-v2.0.{date.year}.{date.month:02d}.{date.day:02d}.days_p05.nc"
                )
                
                # In production, download and process NetCDF file using xarray/netCDF4
                # For now, return simulated data
                daily_amount = self._simulate_chirps_data(lat, lon, date)
                daily_precip.append({
                    'date': date.isoformat(),
                    'precipitation': daily_amount
                })
                total_precipitation += daily_amount
            
            return {
                'source': 'CHIRPS',
                'location': {'lat': lat, 'lon': lon},
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_precipitation': total_precipitation,
                'average_daily_precipitation': total_precipitation / len(dates) if dates else 0,
                'daily_data': daily_precip,
                'note': 'Replace with actual CHIRPS NetCDF processing using xarray'
            }
        except Exception as e:
            print(f"Error fetching CHIRPS data: {e}")
            return self._simulate_chirps_data_range(lat, lon, start_date, end_date)
    
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
    
    def _simulate_chirps_data(self, lat, lon, date):
        """Simulate CHIRPS precipitation data"""
        import random
        # Simulate Africa rainfall patterns (seasonal)
        month = date.month
        # Higher rainfall in wet season (varies by region)
        # West/Central Africa: June-September
        # East Africa: March-May, October-December
        if month in [6, 7, 8, 9] or (lat < 0 and month in [3, 4, 5, 10, 11, 12]):
            base_rainfall = 3.0
        else:
            base_rainfall = 0.5
        
        return max(0, random.uniform(0, base_rainfall * 3))
    
    def _simulate_chirps_data_range(self, lat, lon, start_date, end_date):
        """Simulate CHIRPS data for date range"""
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        total = sum(self._simulate_chirps_data(lat, lon, d) for d in dates)
        
        return {
            'source': 'CHIRPS (simulated)',
            'location': {'lat': lat, 'lon': lon},
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_precipitation': total,
            'average_daily_precipitation': total / len(dates) if dates else 0,
            'note': 'Simulated data'
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

