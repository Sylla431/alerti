"""
Weather Forecast Service - Fetches current weather and forecasts from OpenWeatherMap
"""
import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from utils.config import OPENWEATHERMAP_API_KEY

class WeatherForecastService:
    """Service for fetching weather forecasts from OpenWeatherMap"""
    
    def __init__(self):
        self.api_key = OPENWEATHERMAP_API_KEY
        self.base_url = "https://api.openweathermap.org/data/3.0"
        self.one_call_url = f"{self.base_url}/onecall"
    
    def get_current_weather(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Get current weather conditions for a location
        Returns: dict with temperature, humidity, pressure, precipitation, etc.
        """
        try:
            data = self._fetch_onecall(lat, lon, exclude="minutely,hourly,daily,alerts")
            current = data.get('current')
            if not current:
                return self._get_fallback_current_weather()
            weather = (current.get('weather') or [{}])[0]
            
            return {
                'temperature': current.get('temp'),
                'feels_like': current.get('feels_like'),
                'humidity': current.get('humidity'),
                'pressure': current.get('pressure'),
                'precipitation': current.get('rain', {}).get('1h', 0) or current.get('snow', {}).get('1h', 0),
                'wind_speed': current.get('wind_speed', 0),
                'wind_direction': current.get('wind_deg', 0),
                'clouds': current.get('clouds', 0),
                'description': weather.get('description', 'N/A'),
                'icon': weather.get('icon'),
                'timestamp': datetime.now().isoformat(),
                'coordinates': {'lat': lat, 'lon': lon}
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching current weather: {e}")
            return self._get_fallback_current_weather()
        except Exception as e:
            print(f"Error processing current weather: {e}")
            return self._get_fallback_current_weather()
    
    def get_forecast(self, lat: float, lon: float, days: int = 5) -> Dict:
        """
        Get weather forecast for next N days using One Call 3.0 daily data.
        """
        try:
            data = self._fetch_onecall(lat, lon, exclude="minutely,hourly,alerts")
            daily = data.get('daily', [])
            
            forecast_list = []
            for day in daily[:days]:
                date_key = datetime.fromtimestamp(day.get('dt', datetime.utcnow().timestamp())).date().isoformat()
                temps = day.get('temp', {})
                humidity = day.get('humidity', 0)
                pressure = day.get('pressure', 0)
                wind_speed = day.get('wind_speed', 0)
                wind_gust = day.get('wind_gust', wind_speed)
                precipitation_total = day.get('rain') or day.get('snow') or 0.0
                weather = (day.get('weather') or [{}])[0]
                
                forecast_list.append({
                    'date': date_key,
                    'temperature': {
                        'min': temps.get('min'),
                        'max': temps.get('max'),
                        'avg': temps.get('day')
                    },
                    'precipitation': {
                        'total': precipitation_total,
                        'max_3h': precipitation_total
                    },
                    'humidity': {
                        'min': humidity,
                        'max': humidity,
                        'avg': humidity
                    },
                    'pressure': {
                        'min': pressure,
                        'max': pressure,
                        'avg': pressure
                    },
                    'wind_speed': {
                        'avg': wind_speed,
                        'max': max(wind_speed, wind_gust or 0)
                    },
                    'description': weather.get('description', 'unknown')
                })
            
            return {
                'location': {'lat': lat, 'lon': lon},
                'forecast_days': len(forecast_list),
                'forecasts': forecast_list,
                'timestamp': datetime.now().isoformat(),
                'source': 'OpenWeatherMap One Call 3.0'
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching forecast: {e}")
            return self._get_fallback_forecast(days)
        except Exception as e:
            print(f"Error processing forecast: {e}")
            return self._get_fallback_forecast(days)
    
    def get_forecast_for_lstm(self, lat: float, lon: float, days: int = 7) -> List[Dict]:
        """
        Get forecast formatted for LSTM model input
        Returns list of daily forecasts with features needed for prediction
        """
        forecast_data = self.get_forecast(lat, lon, days)
        
        lstm_features = []
        for day_forecast in forecast_data.get('forecasts', []):
            lstm_features.append({
                'date': day_forecast['date'],
                'precipitation': day_forecast['precipitation']['total'],
                'temperature': day_forecast['temperature']['avg'],
                'humidity': day_forecast['humidity']['avg'],
                'pressure': day_forecast['pressure']['avg'],
                'wind_speed': day_forecast['wind_speed']['avg']
            })
        
        return lstm_features
    
    def get_total_precipitation(self, lat: float, lon: float, days: int = 5) -> Dict:
        """
        Get total precipitation (rain + snow) for the next N days for a location.
        Returns dict containing total precipitation in millimeters and daily breakdown.
        """
        forecast_data = self.get_forecast(lat, lon, days)
        forecasts = forecast_data.get('forecasts', [])
        
        daily_breakdown = []
        total_precip = 0.0
        
        for day in forecasts:
            day_total = day.get('precipitation', {}).get('total', 0) or 0
            daily_breakdown.append({
                'date': day.get('date'),
                'total_mm': day_total
            })
            total_precip += day_total
        
        return {
            'location': {'lat': lat, 'lon': lon},
            'days': len(daily_breakdown),
            'total_precipitation_mm': total_precip,
            'daily_breakdown': daily_breakdown,
            'source': forecast_data.get('source', 'OpenWeatherMap One Call 3.0'),
            'timestamp': datetime.now().isoformat()
        }

    def _fetch_onecall(self, lat: float, lon: float, exclude: Optional[str] = None) -> Dict:
        """Wrapper around OpenWeatherMap One Call 3.0 API."""
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key not configured")
        
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'units': 'metric',
            'lang': 'fr'
        }
        if exclude:
            params['exclude'] = exclude
        
        response = requests.get(self.one_call_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def _get_fallback_current_weather(self) -> Dict:
        """Fallback current weather data when API is unavailable"""
        return {
            'temperature': 30.0,
            'feels_like': 32.0,
            'humidity': 60.0,
            'pressure': 1013.0,
            'precipitation': 0.0,
            'wind_speed': 5.0,
            'wind_direction': 0,
            'clouds': 30,
            'description': 'partiellement nuageux',
            'timestamp': datetime.now().isoformat(),
            'source': 'fallback'
        }
    
    def _get_fallback_forecast(self, days: int) -> Dict:
        """Fallback forecast data when API is unavailable"""
        forecasts = []
        for i in range(days):
            date = (datetime.now() + timedelta(days=i)).date().isoformat()
            forecasts.append({
                'date': date,
                'temperature': {'min': 25.0, 'max': 35.0, 'avg': 30.0},
                'precipitation': {'total': 0.0, 'max_3h': 0.0},
                'humidity': {'min': 50.0, 'max': 70.0, 'avg': 60.0},
                'pressure': {'min': 1010.0, 'max': 1015.0, 'avg': 1013.0},
                'wind_speed': {'avg': 5.0, 'max': 10.0},
                'description': 'conditions normales'
            })
        
        return {
            'forecast_days': days,
            'forecasts': forecasts,
            'timestamp': datetime.now().isoformat(),
            'source': 'fallback'
        }

