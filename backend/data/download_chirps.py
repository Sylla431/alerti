"""
Script pour télécharger les données CHIRPS (précipitations) pour le Mali
CHIRPS = Climate Hazards Group InfraRed Precipitation with Station data
"""
import os
import requests
from datetime import datetime, timedelta
import numpy as np
try:
    from osgeo import gdal
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    print("⚠️  GDAL non disponible. Installation : pip install gdal")
import json

class CHIRPSDownloader:
    """Télécharge les données de précipitations CHIRPS"""
    
    def __init__(self):
        # URLs CHIRPS v3.0 (version actuelle depuis juin 2025)
        self.base_urls = {
            'monthly_v3_global': "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/tifs",
            'monthly_v3_africa': "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/africa/tifs",
            'daily_v3_global': "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/global/tifs/p05"
        }
        self.base_url = self.base_urls['monthly_v3_global']  # CHIRPS v3 mensuel global
        self.chirps_version = "v3.0"  # Version actuelle
        self.download_dir = os.path.join(
            os.path.dirname(__file__), 'raw', 'chirps'
        )
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Coordonnées des villes du Mali
        self.mali_locations = {
            'Bamako': {'lat': 12.6392, 'lon': -8.0029},
            # 'Sikasso': {'lat': 11.3177, 'lon': -5.6671},
            # 'Ségou': {'lat': 13.4317, 'lon': -6.2633},
            # 'Mopti': {'lat': 14.4843, 'lon': -4.1960},
            # 'Gao': {'lat': 16.2715, 'lon': -0.0449},
            # 'Kayes': {'lat': 14.4461, 'lon': -11.4349},
            # 'Tombouctou': {'lat': 16.7731, 'lon': -3.0074},
            # 'Kidal': {'lat': 18.4411, 'lon': 1.4078}
        }
    
    def download_chirps_year_monthly(self, year):
        """Télécharge les données CHIRPS v3 mensuelles pour une année"""
        print(f"\n📅 Téléchargement CHIRPS v3 mensuel pour {year}...")
        
        downloaded = 0
        skipped = 0
        errors = 0
        
        for month in range(1, 13):
            # Format CHIRPS v3 : chirps-v3.0.YYYY.MM.tif
            filename = f"chirps-{self.chirps_version}.{year}.{month:02d}.tif"
            url = f"{self.base_url}/{filename}"
            local_path = os.path.join(self.download_dir, filename)
            
            if not os.path.exists(local_path):
                try:
                    print(f"  Téléchargement : {filename}...", end=' ')
                    response = requests.get(url, timeout=60)
                    
                    if response.status_code == 200:
                        total_size = len(response.content) / (1024 * 1024)  # MB
                        with open(local_path, 'wb') as f:
                            f.write(response.content)
                        print(f"✅ ({total_size:.1f} MB)")
                        downloaded += 1
                    else:
                        print(f"❌ (code {response.status_code})")
                        errors += 1
                except Exception as e:
                    print(f"❌ Erreur : {e}")
                    errors += 1
            else:
                print(f"  ⏭️  Déjà présent : {filename}")
                skipped += 1
        
        print(f"\n📊 Résumé pour {year}:")
        print(f"  ✅ Téléchargés : {downloaded}")
        print(f"  ⏭️  Déjà présents : {skipped}")
        print(f"  ❌ Erreurs : {errors}")
        
        return downloaded
    
    def download_chirps_year(self, year):
        """Télécharge toutes les données CHIRPS pour une année"""
        # Essayer d'abord les données mensuelles (plus fiables)
        return self.download_chirps_year_monthly(year)
    
    def extract_data_for_location(self, lat, lon, tif_path):
        """Extrait la valeur de précipitation pour une coordonnée"""
        if not GDAL_AVAILABLE:
            return None
            
        try:
            dataset = gdal.Open(tif_path)
            if dataset is None:
                return None
            
            # Obtenir les informations de géoréférencement
            geotransform = dataset.GetGeoTransform()
            
            # Convertir lat/lon en pixel
            x_origin = geotransform[0]
            y_origin = geotransform[3]
            pixel_width = geotransform[1]
            pixel_height = geotransform[5]
            
            x_pixel = int((lon - x_origin) / pixel_width)
            y_pixel = int((lat - y_origin) / pixel_height)
            
            # Lire la valeur
            band = dataset.GetRasterBand(1)
            data = band.ReadAsArray(x_pixel, y_pixel, 1, 1)
            
            if data is not None and data.size > 0:
                value = float(data[0, 0])
                # CHIRPS utilise -9999 pour les valeurs manquantes
                return value if value > -9999 else 0.0
            
            return 0.0
            
        except Exception as e:
            print(f"Erreur extraction : {e}")
            return None
    
    def create_csv_from_monthly_tifs(self, year, output_csv=None):
        """Crée un CSV à partir des fichiers CHIRPS v3 mensuels"""
        if not GDAL_AVAILABLE:
            print("❌ GDAL requis pour créer le CSV. Installez avec : pip install gdal")
            return None
            
        if output_csv is None:
            output_csv = os.path.join(
                os.path.dirname(self.download_dir),
                f'chirps_mali_{year}.csv'
            )
        
        print(f"\n📊 Création du CSV pour {year}...")
        
        # Préparer les données
        data = []
        
        for month in range(1, 13):
            filename = f"chirps-{self.chirps_version}.{year}.{month:02d}.tif"
            tif_path = os.path.join(self.download_dir, filename)
            
            if os.path.exists(tif_path):
                print(f"  Traitement : {datetime(year, month, 1).strftime('%B %Y')}")
                
                # Extraire pour chaque ville
                for city, coords in self.mali_locations.items():
                    precip_monthly = self.extract_data_for_location(
                        coords['lat'], coords['lon'], tif_path
                    )
                    
                    if precip_monthly is not None and precip_monthly > 0:
                        # Diviser les précipitations mensuelles en valeurs quotidiennes
                        # Approximation : répartir uniformément sur les jours du mois
                        days_in_month = 31 if month in [1,3,5,7,8,10,12] else 30 if month in [4,6,9,11] else 28
                        daily_precip = precip_monthly / days_in_month
                        
                        # Créer une entrée par jour du mois
                        for day in range(1, days_in_month + 1):
                            try:
                                current_date = datetime(year, month, day)
                                data.append({
                                    'date': current_date.strftime('%Y-%m-%d'),
                                    'location': city,
                                    'lat': coords['lat'],
                                    'lon': coords['lon'],
                                    'precipitation': round(daily_precip, 2)
                                })
                            except ValueError:
                                # Gérer les dates invalides (ex: 29 février années non bissextiles)
                                pass
        
        # Sauvegarder en CSV
        if data:
            import pandas as pd
            df = pd.DataFrame(data)
            df.to_csv(output_csv, index=False)
            print(f"\n✅ CSV créé : {output_csv}")
            print(f"   📊 {len(df)} lignes, {len(df['location'].unique())} villes")
            print(f"   📅 {len(df) // len(self.mali_locations)} jours approximatifs")
            print(f"   ⚠️  Note : précipitations mensuelles réparties uniformément sur les jours")
            return output_csv
        else:
            print("❌ Aucune donnée à sauvegarder")
            return None
    
    def create_csv_from_tifs(self, year, output_csv=None):
        """Crée un CSV à partir des fichiers CHIRPS téléchargés"""
        # Utiliser la version mensuelle
        return self.create_csv_from_monthly_tifs(year, output_csv)


def main():
    """Fonction principale"""
    downloader = CHIRPSDownloader()
    
    # Télécharger les années désirées
    years = [2021,2022, 2023, 2024]  # 3 dernières années (plus rapide)
    
    print("=" * 60)
    print("🌧️  TÉLÉCHARGEMENT DES DONNÉES CHIRPS v3 (PRÉCIPITATIONS)")
    print("=" * 60)
    print(f"\n✨ Version : CHIRPS {downloader.chirps_version} (mise à jour juin 2025)")
    print(f"📍 Villes du Mali : {', '.join(downloader.mali_locations.keys())}")
    print(f"📅 Années : {', '.join(map(str, years))}")
    print(f"📦 Format : Données mensuelles (12 fichiers/an)")
    
    # Informations
    print("\n⏱️  Durée estimée : 10-20 minutes par année")
    print("📊 Taille : ~20 MB par mois (~240 MB/an)")
    print("\n🚀 Démarrage du téléchargement...")
    
    for year in years:
        # Télécharger les fichiers TIFF
        downloader.download_chirps_year(year)
        
        # Créer le CSV
        if GDAL_AVAILABLE:
            downloader.create_csv_from_tifs(year)
        else:
            print(f"⚠️  CSV non créé pour {year} (GDAL manquant)")
    
    print("\n" + "=" * 60)
    print("✅ TÉLÉCHARGEMENT TERMINÉ !")
    print("=" * 60)
    
    if GDAL_AVAILABLE:
        print("\nFichiers CSV créés dans : backend/data/")
        print("\n📝 Prochaine étape :")
        print("   python prepare_training_data.py")
    else:
        print("\n⚠️  Pour créer les CSV, installez GDAL :")
        print("   pip install gdal")


if __name__ == '__main__':
    main()

