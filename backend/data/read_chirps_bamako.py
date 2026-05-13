"""
Script pour lire les fichiers CHIRPS .tif et extraire les données pour les 6 communes de Bamako
Version simplifiée et ciblée pour Bamako
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime

# Ajouter le chemin backend
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.bamako_communes import BAMAKO_COMMUNES, format_for_chirps

# Essayer d'importer rasterio
try:
    import rasterio
    RASTERIO_AVAILABLE = True
    print("✅ Rasterio disponible")
except ImportError:
    RASTERIO_AVAILABLE = False
    print("❌ Rasterio non disponible. Installez avec : pip install rasterio")
    exit(1)


class BamakoChirpsReader:
    """Lecteur de fichiers CHIRPS .tif pour les communes de Bamako"""
    
    def __init__(self):
        self.communes = format_for_chirps()
    
    def extract_precipitation(self, tif_path, lat, lon):
        """Extraire la précipitation pour une coordonnée avec rasterio"""
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
            print(f"  ❌ Erreur : {e}")
            return None
    
    def process_tif_file(self, tif_path):
        """Traite un fichier TIF et extrait les données pour toutes les communes"""
        print(f"\n🔍 Traitement : {os.path.basename(tif_path)}")
        
        # Extraire la date du nom de fichier
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
            print("   ⚠️  Impossible d'extraire la date")
            return None
        
        # Extraire pour chaque commune
        data = []
        print(f"\n   📍 Précipitations par commune:")
        for commune, coords in self.communes.items():
            precip = self.extract_precipitation(
                tif_path, coords['lat'], coords['lon']
            )
            
            if precip is not None:
                # Afficher avec couleur selon le niveau
                if precip > 100:
                    symbol = "🔴"  # Fort
                elif precip > 50:
                    symbol = "🟠"  # Moyen
                elif precip > 10:
                    symbol = "🟡"  # Faible
                else:
                    symbol = "⚪"  # Très faible
                
                print(f"   {symbol} {commune:15s} : {precip:7.2f} mm")
                
                # Créer une entrée par jour du mois (répartition uniforme)
                days_in_month = 31 if month in [1,3,5,7,8,10,12] else 30 if month in [4,6,9,11] else 28
                daily_precip = precip / days_in_month
                
                for day in range(1, days_in_month + 1):
                    try:
                        date = datetime(year, month, day)
                        data.append({
                            'date': date.strftime('%Y-%m-%d'),
                            'commune': commune,
                            'lat': coords['lat'],
                            'lon': coords['lon'],
                            'precipitation': round(daily_precip, 2)
                        })
                    except ValueError:
                        pass
            else:
                print(f"   ❌ {commune:15s} : Erreur")
        
        return data
    
    def process_directory(self, tif_dir, output_csv=None):
        """Traite tous les fichiers TIF d'un dossier"""
        print("=" * 60)
        print("📂 EXTRACTION CHIRPS - BAMAKO")
        print("=" * 60)
        print(f"\n📍 6 communes de Bamako")
        
        # Lister les fichiers TIF
        tif_files = sorted([
            f for f in os.listdir(tif_dir)
            if f.endswith('.tif') and ('chirps' in f.lower())
        ])
        
        if not tif_files:
            print(f"\n❌ Aucun fichier TIF trouvé dans : {tif_dir}")
            return
        
        print(f"\n📊 {len(tif_files)} fichiers TIF trouvés")
        
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
                    f'bamako_communes_{first_year}.csv'
                )
            
            df.to_csv(output_csv, index=False)
            
            print("\n" + "=" * 60)
            print("✅ EXTRACTION TERMINÉE !")
            print("=" * 60)
            print(f"\n📄 CSV créé : {output_csv}")
            print(f"   📊 {len(df)} lignes")
            print(f"   📅 {len(df['date'].unique())} jours")
            print(f"   🏘️  {len(df['commune'].unique())} communes")
            
            # Statistiques par commune
            print(f"\n📊 Précipitations totales moyennes par commune:")
            commune_totals = df.groupby('commune')['precipitation'].sum().sort_values(ascending=False)
            for commune, total in commune_totals.items():
                print(f"   • {commune:15s} : {total:7.1f} mm")
            
            return output_csv
        else:
            print("\n❌ Aucune donnée extraite")
            return None


def main():
    """Fonction principale"""
    print("=" * 60)
    print("📊 LECTEUR CHIRPS - 6 COMMUNES DE BAMAKO")
    print("=" * 60)
    
    reader = BamakoChirpsReader()
    
    # Dossier contenant les fichiers TIF
    tif_dir = os.path.join(os.path.dirname(__file__), 'raw', 'chirps')
    
    if not os.path.exists(tif_dir):
        print(f"\n❌ Dossier non trouvé : {tif_dir}")
        print("   Créez-le et placez-y vos fichiers CHIRPS .tif")
        return
    
    # Traiter tous les fichiers
    output_csv = reader.process_directory(tif_dir)
    
    if output_csv:
        print("\n📝 Prochaine étape :")
        print("   python prepare_training_data.py")
        print("\n💡 Le fichier CSV est prêt pour l'entraînement du modèle !")


if __name__ == '__main__':
    main()

