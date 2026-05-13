"""
Script SIMPLIFIÉ pour télécharger les données CHIRPS
Alternative sans GDAL - Utilise l'API CHIRPS ou données pré-traitées
"""
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import json

class SimpleCHIRPSDownloader:
    """Téléchargeur CHIRPS simplifié sans GDAL"""
    
    def __init__(self):
        self.download_dir = os.path.join(
            os.path.dirname(__file__), 'raw', 'chirps_csv'
        )
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Coordonnées des villes du Mali
        self.mali_locations = {
            'Bamako': {'lat': 12.6392, 'lon': -8.0029},
            'Sikasso': {'lat': 11.3177, 'lon': -5.6671},
            'Ségou': {'lat': 13.4317, 'lon': -6.2633},
            'Mopti': {'lat': 14.4843, 'lon': -4.1960},
            'Gao': {'lat': 16.2715, 'lon': -0.0449},
            'Kayes': {'lat': 14.4461, 'lon': -11.4349},
            'Tombouctou': {'lat': 16.7731, 'lon': -3.0074},
            'Kidal': {'lat': 18.4411, 'lon': 1.4078}
        }
    
    def generate_synthetic_chirps_data(self, year):
        """Génère des données CHIRPS synthétiques réalistes pour tester"""
        print(f"\n📊 Génération de données CHIRPS synthétiques pour {year}...")
        print("   ⚠️  Ces données sont APPROXIMATIVES pour tester le système")
        print("   ⚠️  Pour la production, utilisez de vraies données CHIRPS")
        
        import numpy as np
        np.random.seed(year)  # Reproductibilité
        
        data = []
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        current_date = start_date
        
        while current_date <= end_date:
            for city, coords in self.mali_locations.items():
                # Simuler les précipitations selon la saison
                month = current_date.month
                
                # Saison des pluies au Mali : mai-octobre
                if 5 <= month <= 10:
                    # Forte probabilité de pluie
                    if np.random.random() < 0.4:  # 40% de chance de pluie
                        precip = np.random.exponential(15.0)  # Moyenne 15mm
                    else:
                        precip = 0.0
                else:
                    # Saison sèche
                    if np.random.random() < 0.05:  # 5% de chance de pluie
                        precip = np.random.exponential(2.0)  # Moyenne 2mm
                    else:
                        precip = 0.0
                
                data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'location': city,
                    'lat': coords['lat'],
                    'lon': coords['lon'],
                    'precipitation': round(precip, 2)
                })
            
            current_date += timedelta(days=1)
        
        # Sauvegarder en CSV
        df = pd.DataFrame(data)
        output_csv = os.path.join(
            os.path.dirname(self.download_dir),
            f'chirps_mali_{year}.csv'
        )
        df.to_csv(output_csv, index=False)
        
        print(f"\n✅ Données synthétiques créées : {output_csv}")
        print(f"   📊 {len(df)} lignes")
        
        return output_csv
    
    def download_from_climate_engine(self, location, start_date, end_date):
        """
        Alternative : Utiliser Climate Engine API (si disponible)
        https://support.climateengine.org/article/63-api
        """
        print(f"\n🌐 Téléchargement via Climate Engine API...")
        print("   ⚠️  Nécessite une clé API Climate Engine")
        print("   ⚠️  Fonction non implémentée - utilisez les données synthétiques pour tester")
        return None
    
    def instructions_manual_download(self):
        """Affiche les instructions pour téléchargement manuel"""
        print("\n" + "="*60)
        print("📥 INSTRUCTIONS DE TÉLÉCHARGEMENT MANUEL")
        print("="*60)
        
        print("\n🌐 Option 1 : Climate Engine (Recommandé)")
        print("   1. Visitez : https://app.climateengine.com/")
        print("   2. Sélectionnez 'CHIRPS' comme dataset")
        print("   3. Dessinez un polygone autour du Mali")
        print("   4. Sélectionnez la plage de dates (ex: 2020-2024)")
        print("   5. Téléchargez en format CSV")
        print("   6. Placez le CSV dans : backend/data/")
        
        print("\n🌐 Option 2 : Google Earth Engine")
        print("   1. Créez un compte : https://earthengine.google.com/")
        print("   2. Utilisez ce code pour extraire CHIRPS :")
        print("""
        var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY');
        var mali = ee.Geometry.Point([-8.0, 12.6]);
        var data = chirps
          .filterDate('2020-01-01', '2024-12-31')
          .filterBounds(mali);
        // Exportez vers Google Drive
        """)
        
        print("\n🌐 Option 3 : CHIRPS Portal")
        print("   1. Visitez : https://iridl.ldeo.columbia.edu/")
        print("   2. Naviguez vers : Climate > Precipitation > CHIRPS")
        print("   3. Sélectionnez votre zone et période")
        print("   4. Téléchargez en format NetCDF ou CSV")
        
        print("\n💡 Option 4 : Données Synthétiques (Pour Tester)")
        print("   Utilisez : generate_synthetic_chirps_data(year)")
        print("   Idéal pour tester le système avant d'obtenir vraies données")


def main():
    """Fonction principale"""
    print("=" * 60)
    print("🌧️  TÉLÉCHARGEMENT CHIRPS SIMPLIFIÉ")
    print("=" * 60)
    
    downloader = SimpleCHIRPSDownloader()
    
    print("\n📝 Ce script propose 2 options :")
    print("   1. Générer des données synthétiques (pour tester)")
    print("   2. Instructions pour téléchargement manuel")
    
    choice = input("\nVotre choix (1/2) : ")
    
    if choice == '1':
        years = [2020, 2021, 2022, 2023, 2024]
        print(f"\n📅 Génération de données pour : {', '.join(map(str, years))}")
        
        for year in years:
            downloader.generate_synthetic_chirps_data(year)
        
        print("\n" + "=" * 60)
        print("✅ GÉNÉRATION TERMINÉE !")
        print("=" * 60)
        print("\n📝 Prochaine étape :")
        print("   python prepare_training_data.py")
        
    elif choice == '2':
        downloader.instructions_manual_download()
        
    else:
        print("❌ Choix invalide")


if __name__ == '__main__':
    main()

