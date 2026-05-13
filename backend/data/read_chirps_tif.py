"""
Script pour lire les fichiers CHIRPS .tif et extraire les données pour le Mali
Compatible avec CHIRPS v2 et v3
"""
import os
import numpy as np
import pandas as pd
from datetime import datetime

# Essayer d'importer GDAL ou rasterio
GDAL_AVAILABLE = False
RASTERIO_AVAILABLE = False

try:
    from osgeo import gdal
    GDAL_AVAILABLE = True
    print("✅ GDAL disponible")
except ImportError:
    print("⚠️  GDAL non disponible")

try:
    import rasterio
    RASTERIO_AVAILABLE = True
    print("✅ Rasterio disponible")
except ImportError:
    print("⚠️  Rasterio non disponible")

if not GDAL_AVAILABLE and not RASTERIO_AVAILABLE:
    print("\n❌ Aucune bibliothèque de lecture TIF disponible !")
    print("   Installez l'une d'entre elles :")
    print("   pip install rasterio")
    print("   OU")
    print("   pip install gdal")
    exit(1)


class CHIRPSTifReader:
    """Lecteur de fichiers CHIRPS .tif"""
    
    def __init__(self):
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
    
    def read_with_rasterio(self, tif_path, lat, lon):
        """Lire un fichier TIF avec rasterio"""
        try:
            with rasterio.open(tif_path) as src:
                # Convertir lat/lon en coordonnées pixel
                row, col = src.index(lon, lat)
                
                # Lire la valeur
                data = src.read(1)  # Lire la première bande
                value = data[row, col]
                
                # CHIRPS utilise -9999 pour valeurs manquantes
                if value < -9000:
                    return 0.0
                
                return float(value)
                
        except Exception as e:
            print(f"  ❌ Erreur lecture avec rasterio : {e}")
            return None
    
    def read_with_gdal(self, tif_path, lat, lon):
        """Lire un fichier TIF avec GDAL"""
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
                # CHIRPS utilise -9999 pour valeurs manquantes
                return value if value > -9000 else 0.0
            
            return 0.0
            
        except Exception as e:
            print(f"  ❌ Erreur lecture avec GDAL : {e}")
            return None
    
    def extract_precipitation(self, tif_path, lat, lon):
        """Extraire la précipitation pour une coordonnée"""
        # Essayer rasterio d'abord (plus simple)
        if RASTERIO_AVAILABLE:
            return self.read_with_rasterio(tif_path, lat, lon)
        elif GDAL_AVAILABLE:
            return self.read_with_gdal(tif_path, lat, lon)
        else:
            return None
    
    def get_tif_info(self, tif_path):
        """Affiche les informations d'un fichier TIF"""
        print(f"\n📄 Informations du fichier : {os.path.basename(tif_path)}")
        print(f"   Taille : {os.path.getsize(tif_path) / (1024*1024):.2f} MB")
        
        if RASTERIO_AVAILABLE:
            try:
                with rasterio.open(tif_path) as src:
                    print(f"   Dimensions : {src.width} x {src.height} pixels")
                    print(f"   Bandes : {src.count}")
                    print(f"   CRS : {src.crs}")
                    print(f"   Bounds : {src.bounds}")
                    print(f"   Résolution : {src.res}")
                    
                    # Lire quelques statistiques
                    data = src.read(1)
                    valid_data = data[data > -9000]
                    if len(valid_data) > 0:
                        print(f"   Précipitation min : {valid_data.min():.2f} mm")
                        print(f"   Précipitation max : {valid_data.max():.2f} mm")
                        print(f"   Précipitation moyenne : {valid_data.mean():.2f} mm")
            except Exception as e:
                print(f"   ❌ Erreur : {e}")
        
        elif GDAL_AVAILABLE:
            try:
                dataset = gdal.Open(tif_path)
                if dataset:
                    print(f"   Dimensions : {dataset.RasterXSize} x {dataset.RasterYSize} pixels")
                    print(f"   Bandes : {dataset.RasterCount}")
                    geotransform = dataset.GetGeoTransform()
                    print(f"   Résolution : {geotransform[1]:.5f} degrés")
            except Exception as e:
                print(f"   ❌ Erreur : {e}")
    
    def process_tif_file(self, tif_path):
        """Traite un fichier TIF et extrait les données pour toutes les villes"""
        print(f"\n🔍 Traitement : {os.path.basename(tif_path)}")
        
        # Extraire la date du nom de fichier
        # Format : chirps-v2.0.YYYY.MM.tif ou chirps-v3.0.YYYY.MM.tif
        filename = os.path.basename(tif_path)
        parts = filename.replace('.tif', '').split('.')
        
        try:
            if len(parts) >= 3:
                year = int(parts[-2])
                month = int(parts[-1])
                print(f"   📅 Date : {year}-{month:02d}")
            else:
                print("   ⚠️  Format de nom de fichier non reconnu")
                return None
        except ValueError:
            print("   ⚠️  Impossible d'extraire la date du nom de fichier")
            return None
        
        # Extraire pour chaque ville
        data = []
        for city, coords in self.mali_locations.items():
            precip = self.extract_precipitation(
                tif_path, coords['lat'], coords['lon']
            )
            
            if precip is not None:
                print(f"   • {city:15s} : {precip:6.2f} mm")
                
                # Créer une entrée par jour du mois (répartition uniforme)
                days_in_month = 31 if month in [1,3,5,7,8,10,12] else 30 if month in [4,6,9,11] else 28
                daily_precip = precip / days_in_month
                
                for day in range(1, days_in_month + 1):
                    try:
                        date = datetime(year, month, day)
                        data.append({
                            'date': date.strftime('%Y-%m-%d'),
                            'location': city,
                            'lat': coords['lat'],
                            'lon': coords['lon'],
                            'precipitation': round(daily_precip, 2)
                        })
                    except ValueError:
                        pass
            else:
                print(f"   • {city:15s} : ❌ Erreur")
        
        return data
    
    def process_directory(self, tif_dir, output_csv=None):
        """Traite tous les fichiers TIF d'un dossier"""
        print("=" * 60)
        print("📂 TRAITEMENT DES FICHIERS CHIRPS")
        print("=" * 60)
        
        # Lister les fichiers TIF
        tif_files = sorted([
            f for f in os.listdir(tif_dir)
            if f.endswith('.tif') and ('chirps' in f.lower())
        ])
        
        if not tif_files:
            print(f"\n❌ Aucun fichier TIF trouvé dans : {tif_dir}")
            return
        
        print(f"\n📊 {len(tif_files)} fichiers TIF trouvés")
        
        # Afficher les infos du premier fichier
        first_file = os.path.join(tif_dir, tif_files[0])
        self.get_tif_info(first_file)
        
        # Traiter tous les fichiers
        all_data = []
        for tif_file in tif_files:
            tif_path = os.path.join(tif_dir, tif_file)
            data = self.process_tif_file(tif_path)
            if data:
                all_data.extend(data)
        
        # Sauvegarder en CSV
        if all_data:
            df = pd.DataFrame(all_data)
            
            if output_csv is None:
                # Extraire l'année du premier fichier
                first_year = df['date'].iloc[0][:4]
                output_csv = os.path.join(
                    os.path.dirname(tif_dir),
                    f'chirps_mali_{first_year}.csv'
                )
            
            df.to_csv(output_csv, index=False)
            
            print("\n" + "=" * 60)
            print("✅ TRAITEMENT TERMINÉ !")
            print("=" * 60)
            print(f"\n📄 CSV créé : {output_csv}")
            print(f"   📊 {len(df)} lignes")
            print(f"   📅 {len(df['date'].unique())} jours")
            print(f"   🏙️  {len(df['location'].unique())} villes")
            print(f"   🌧️  Précipitation totale moyenne : {df['precipitation'].sum() / len(self.mali_locations):.1f} mm")
            
            return output_csv
        else:
            print("\n❌ Aucune donnée extraite")
            return None


def main():
    """Fonction principale"""
    print("=" * 60)
    print("📊 LECTEUR DE FICHIERS CHIRPS .TIF")
    print("=" * 60)
    
    reader = CHIRPSTifReader()
    
    # Dossier contenant les fichiers TIF
    tif_dir = os.path.join(os.path.dirname(__file__), 'raw', 'chirps')
    
    if not os.path.exists(tif_dir):
        print(f"\n❌ Dossier non trouvé : {tif_dir}")
        print("   Créez-le et placez-y vos fichiers CHIRPS .tif")
        return
    
    # Traiter tous les fichiers
    reader.process_directory(tif_dir)
    
    print("\n📝 Prochaine étape :")
    print("   python prepare_training_data.py")


if __name__ == '__main__':
    main()

