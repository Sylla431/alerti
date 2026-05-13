"""
Utility script to fetch total precipitation for predefined neighborhoods
using OpenWeatherMap forecasts.
"""

import os
from typing import Dict

from services.weather_forecast_service import WeatherForecastService

NEIGHBORHOODS: Dict[str, Dict] = {
    'Sebenikoro': {
        'lat': 12.613138774011157,
        'lon': -8.045667553387089,
        'description': 'Quartier de Sebenikoro, Bamako',
    },
    'Yirimadio': {
        'lat': 12.607504405292698,
        'lon': -7.923320997395195,
        'description': 'Quartier de Yirimadio, Bamako',
    },
    'Missabougou': {
        'lat': 12.633253847822019,
        'lon': -7.9186749686637485,
        'description': 'Quartier de Missabougou, Bamako',
    },
}


def main(days: int = 5) -> None:
    service = WeatherForecastService()
    
    if not service.api_key:
        print("OPENWEATHERMAP_API_KEY is not configured. Please set it in your .env file.")
        return
    
    print(f"=== Total precipitation forecast for next {days} days ===")
    
    for name, data in NEIGHBORHOODS.items():
        result = service.get_total_precipitation(data['lat'], data['lon'], days=days)
        total = result['total_precipitation_mm']
        
        print(f"\n{name} ({data['description']})")
        print(f"  Coordonnées : ({data['lat']}, {data['lon']})")
        print(f"  Précipitations totales sur {result['days']} jours : {total:.2f} mm")
        print("  Détails journaliers :")
        for day in result['daily_breakdown']:
            print(f"    - {day['date']}: {day['total_mm']:.2f} mm")


if __name__ == "__main__":
    main()

