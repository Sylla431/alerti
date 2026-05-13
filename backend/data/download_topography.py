"""
Script pour télécharger les données topographiques (SRTM) pour Bamako
SRTM = Shuttle Radar Topography Mission (NASA)

Version utilisée : SRTM 1 Arc-Second Global (SRTMGL1.003)
- Résolution : ~30 mètres (1 arc-seconde)
- Couverture : Global (60°N à 56°S)
- Format : GeoTIFF
- Gratuit, nécessite compte NASA Earthdata
"""
import os
import sys
import time

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import numpy as np
try:
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False
    print("⚠️  Rasterio requis : pip install rasterio")

# Coordonnées de Bamako
BAMAKO_BBOX = {
    'lat_min': 12.55,
    'lat_max': 12.70,
    'lon_min': -8.10,
    'lon_max': -7.90
}

# Coordonnées des 6 communes
from utils.bamako_communes import BAMAKO_COMMUNES


class TopographyDownloader:
    """Télécharge les données d'élévation SRTM"""
    
    def __init__(self):
        self.download_dir = os.path.join(
            os.path.dirname(__file__), 'raw', 'topography'
        )
        os.makedirs(self.download_dir, exist_ok=True)
        
        # URLs SRTM 1 Arc-Second Global (SRTMGL1.003)
        # Note: Nécessite un compte gratuit sur https://urs.earthdata.nasa.gov/
        # Documentation: https://lpdaac.usgs.gov/products/srtmgl1v003/
        self.srtm_base_url = "https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/2000.02.11"
        
        # Tuile SRTM pour Bamako (Afrique de l'Ouest)
        # Format: SRTM_XX_YY.tif (XX = latitude, YY = longitude)
        # Pour Bamako (12.6°N, -8.0°E) : tuile SRTM_07_08
        self.srtm_tile = "SRTM_07_08.tif"  # Tuile couvrant le Mali
        
        # Sources alternatives (SRTM - différentes résolutions)
        # Note: Les URLs peuvent changer, utilisez Google Earth Engine si ces sources échouent
        self.alternative_sources = [
            {
                'name': 'OpenTopography (SRTM 30m)',
                'url': 'https://cloud.sdsc.edu/v1/AUTH_opentopography/Raster/SRTM_GL1_srtm/North/North_0_10/N07E008.SRTMGL1.hgt.zip',
                'resolution': '30m',
                'format': 'zip',
                'note': 'Source fiable, peut nécessiter authentification'
            },
            {
                'name': 'CGIAR-CSI (SRTM 90m)',
                'url': 'https://srtm.csi.cgiar.org/wp-content/uploads/files/srtm_5x5/TIFF/srtm_07_08.zip',
                'resolution': '90m',
                'format': 'zip',
                'note': 'URL peut avoir changé - site: https://srtm.csi.cgiar.org'
            },
            {
                'name': 'NASA Earthdata (via direct link)',
                'url': 'https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/2000.02.11/SRTM_07_08.tif',
                'resolution': '30m',
                'format': 'tif',
                'note': 'Nécessite authentification - peut échouer sans credentials'
            }
        ]
        
        self.max_retries = 3
        self.retry_delay = 5
    
    def _download_with_retry(self, url, local_path, description="fichier"):
        """Télécharge un fichier avec retry et gestion d'erreurs"""
        for attempt in range(self.max_retries):
            try:
                print(f"  📥 Téléchargement {description} (tentative {attempt + 1}/{self.max_retries})...")
                
                response = requests.get(url, stream=True, timeout=180)
                
                # Gérer erreurs HTTP
                if response.status_code == 404:
                    print(f"  ❌ Fichier non trouvé (404) - URL peut avoir changé")
                    return None  # Pas besoin de retry pour 404
                
                if response.status_code == 429:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"  ⚠️  Limite de taux (429). Attente {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code == 504:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"  ⚠️  Timeout serveur (504). Nouvelle tentative dans {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                
                # Télécharger le fichier
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                print(f"     Progression : {percent:.1f}%", end='\r')
                
                print(f"  ✅ Téléchargement terminé : {os.path.basename(local_path)}")
                return local_path
                
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"  ⚠️  Timeout. Nouvelle tentative dans {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"  ❌ Timeout après {self.max_retries} tentatives")
                    return None
                    
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"  ⚠️  Erreur réseau: {e}")
                    print(f"     Nouvelle tentative dans {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"  ❌ Erreur après {self.max_retries} tentatives: {e}")
                    return None
            except Exception as e:
                print(f"  ❌ Erreur inattendue: {e}")
                return None
        
        return None
    
    def download_srtm_tile(self, tile_name, use_alternatives=True):
        """Télécharge une tuile SRTM depuis plusieurs sources"""
        local_path = os.path.join(self.download_dir, tile_name)
        
        if os.path.exists(local_path):
            print(f"  ⏭️  Déjà téléchargé : {tile_name}")
            return local_path
        
        # Essayer d'abord la source principale (NASA - nécessite auth)
        url = f"{self.srtm_base_url}/{tile_name}"
        print(f"  📥 Tentative téléchargement depuis NASA Earthdata...")
        print("     ⚠️  Note: Nécessite authentification")
        print("     Créez un compte : https://urs.earthdata.nasa.gov/")
        
        # Pour l'instant, on passe aux alternatives car NASA nécessite auth
        if use_alternatives:
            print("\n  🔄 Essai des sources alternatives...")
            print("     (Les sources peuvent être lentes ou temporairement indisponibles)")
            
            for i, source in enumerate(self.alternative_sources, 1):
                print(f"\n  [{i}/{len(self.alternative_sources)}] 📡 Source : {source['name']} ({source['resolution']})")
                if 'note' in source:
                    print(f"     ℹ️  {source['note']}")
                print(f"     URL : {source['url'][:70]}...")
                
                if source['format'] == 'zip':
                    # Télécharger le ZIP
                    zip_path = local_path.replace('.tif', '.zip')
                    downloaded = self._download_with_retry(
                        source['url'], 
                        zip_path,
                        f"{source['name']} (ZIP)"
                    )
                    
                    if downloaded and os.path.exists(zip_path):
                        print(f"  📦 Extraction de {os.path.basename(zip_path)}...")
                        try:
                            import zipfile
                            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                                zip_ref.extractall(self.download_dir)
                            
                            # Chercher le fichier .tif ou .hgt extrait
                            extracted_files = [f for f in os.listdir(self.download_dir) 
                                             if (f.endswith('.tif') or f.endswith('.hgt')) 
                                             and f != os.path.basename(zip_path)]
                            
                            if extracted_files:
                                extracted_path = os.path.join(self.download_dir, extracted_files[0])
                                # Renommer si nécessaire
                                if extracted_path != local_path:
                                    if os.path.exists(local_path):
                                        os.remove(local_path)
                                    os.rename(extracted_path, local_path)
                                
                                # Nettoyer le ZIP
                                if os.path.exists(zip_path):
                                    os.remove(zip_path)
                                
                                print(f"  ✅ Fichier extrait et renommé : {tile_name}")
                                return local_path
                            else:
                                print(f"  ⚠️  Aucun fichier .tif ou .hgt trouvé dans le ZIP")
                        except Exception as e:
                            print(f"  ❌ Erreur extraction : {e}")
                            # Nettoyer le ZIP en cas d'erreur
                            if os.path.exists(zip_path):
                                try:
                                    os.remove(zip_path)
                                except:
                                    pass
                            continue
                    else:
                        print(f"  ⚠️  Échec du téléchargement depuis {source['name']}")
                else:
                    # Téléchargement direct
                    downloaded = self._download_with_retry(
                        source['url'],
                        local_path,
                        f"{source['name']}"
                    )
                    if downloaded and os.path.exists(local_path):
                        return local_path
        
        print("\n" + "=" * 60)
        print("  ❌ Toutes les tentatives de téléchargement automatique ont échoué")
        print("=" * 60)
        print("\n  💡 RECOMMANDATION : Utilisez Google Earth Engine")
        print("     C'est la méthode la plus fiable et la plus simple.")
        print("     Voir les instructions dans la section 'Méthode 2' ci-dessous.")
        print("\n  📝 Alternative : Téléchargement manuel depuis")
        print("     • NASA Earthdata : https://earthexplorer.usgs.gov/")
        print("     • CGIAR-CSI : https://srtm.csi.cgiar.org/")
        print("     • OpenTopography : https://opentopography.org/")
        return None
    
    def extract_elevation_for_location(self, tif_path, lat, lon):
        """Extrait l'élévation pour une coordonnée"""
        if not RASTERIO_AVAILABLE:
            return None
        
        try:
            with rasterio.open(tif_path) as src:
                # Vérifier que les coordonnées sont dans les bounds
                if not (src.bounds.left <= lon <= src.bounds.right and 
                       src.bounds.bottom <= lat <= src.bounds.top):
                    return None
                
                row, col = src.index(lon, lat)
                
                # Vérifier que les indices sont valides
                if row < 0 or row >= src.height or col < 0 or col >= src.width:
                    return None
                
                data = src.read(1)
                elevation = float(data[row, col])
                
                # -32768 = nodata pour SRTM
                return elevation if elevation > -32768 else None
        except rasterio.errors.RasterioIOError as e:
            print(f"  ⚠️  Erreur lecture fichier : {e}")
            return None
        except Exception as e:
            print(f"  ⚠️  Erreur extraction : {e}")
            return None
    
    def calculate_slope(self, tif_path, lat, lon, window_size=3):
        """Calcule la pente du terrain"""
        if not RASTERIO_AVAILABLE:
            return None
        
        try:
            with rasterio.open(tif_path) as src:
                # Vérifier que les coordonnées sont dans les bounds
                if not (src.bounds.left <= lon <= src.bounds.right and 
                       src.bounds.bottom <= lat <= src.bounds.top):
                    return None
                
                row, col = src.index(lon, lat)
                
                # Vérifier que les indices sont valides
                if row < 0 or row >= src.height or col < 0 or col >= src.width:
                    return None
                
                # Extraire une fenêtre autour du point (avec gestion des bords)
                row_start = max(0, row - window_size//2)
                row_end = min(src.height, row + window_size//2 + 1)
                col_start = max(0, col - window_size//2)
                col_end = min(src.width, col + window_size//2 + 1)
                
                window = rasterio.windows.Window(
                    col_start, row_start,
                    col_end - col_start, row_end - row_start
                )
                
                data = src.read(1, window=window)
                
                if data.size == 0 or np.all(data == -32768):  # Tous nodata
                    return None
                
                # Remplacer nodata par NaN pour le calcul
                data = data.astype(float)
                data[data == -32768] = np.nan
                
                # Calculer la pente (gradient)
                cell_size = src.res[0] * 111000  # Convertir degrés en mètres
                grad_x = np.gradient(data, axis=1)
                grad_y = np.gradient(data, axis=0)
                slope = np.arctan(np.sqrt(grad_x**2 + grad_y**2) / cell_size) * 180 / np.pi
                
                # Moyenne en ignorant NaN
                slope_mean = np.nanmean(slope)
                return float(slope_mean) if not np.isnan(slope_mean) else None
                
        except rasterio.errors.RasterioIOError as e:
            return None  # Erreur déjà gérée dans extract_elevation
        except Exception as e:
            return None  # Erreur silencieuse pour ne pas polluer l'affichage
    
    def extract_for_communes(self, tif_path):
        """Extrait élévation et pente pour toutes les communes"""
        print("\n📊 Extraction des données topographiques...")
        
        results = {}
        communes_list = list(BAMAKO_COMMUNES.items())
        
        for i, (commune, coords) in enumerate(communes_list, 1):
            lat = coords['lat']
            lon = coords['lon']
            
            print(f"  [{i}/{len(communes_list)}] {commune}...", end=' ')
            
            elevation = self.extract_elevation_for_location(tif_path, lat, lon)
            slope = self.calculate_slope(tif_path, lat, lon)
            
            if elevation is not None and slope is not None:
                results[commune] = {
                    'elevation': elevation,
                    'slope': slope
                }
                print(f"✅ Élévation={elevation:.1f}m, Pente={slope:.2f}°")
            else:
                print(f"⚠️  Données manquantes")
                results[commune] = {
                    'elevation': None,
                    'slope': None
                }
        
        return results


def download_from_earthdata():
    """Instructions pour télécharger depuis NASA Earthdata"""
    print("=" * 60)
    print("🗻 TÉLÉCHARGEMENT DONNÉES TOPOGRAPHIQUES (SRTM)")
    print("=" * 60)
    
    print("\n📝 Méthode 1 : NASA Earthdata (Recommandé)")
    print("   Produit : SRTM 1 Arc-Second Global (SRTMGL1.003)")
    print("   Résolution : 30 mètres")
    print("   URL : https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/")
    print("\n   Étapes :")
    print("   1. Créez un compte gratuit : https://urs.earthdata.nasa.gov/")
    print("   2. Visitez : https://earthexplorer.usgs.gov/")
    print("   3. Sélectionnez 'SRTM 1 Arc-Second Global' dans les datasets")
    print("   4. Définissez la zone :")
    print(f"      Latitude : {BAMAKO_BBOX['lat_min']} à {BAMAKO_BBOX['lat_max']}")
    print(f"      Longitude : {BAMAKO_BBOX['lon_min']} à {BAMAKO_BBOX['lon_max']}")
    print("   5. Téléchargez la tuile : SRTM_07_08.tif")
    print("   6. Placez-la dans : backend/data/raw/topography/")
    print("\n   Alternative directe (avec authentification) :")
    print("   https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/2000.02.11/SRTM_07_08.tif")
    
    print("\n" + "=" * 60)
    print("📝 Méthode 2 : Google Earth Engine ⭐ RECOMMANDÉ")
    print("=" * 60)
    print("   Produit : USGS/SRTMGL1_003 (SRTM 1 Arc-Second Global)")
    print("   Résolution : 30 mètres")
    print("   ✅ Gratuit, fiable, pas de problème d'URL")
    print("\n   Étapes :")
    print("   1. Créez un compte gratuit : https://earthengine.google.com/")
    print("   2. Ouvrez l'éditeur de code : https://code.earthengine.google.com/")
    print("   3. Collez ce code dans l'éditeur :")
    print("""
    // SRTM 1 Arc-Second Global pour Bamako
    var srtm = ee.Image('USGS/SRTMGL1_003');
    var bamako = ee.Geometry.Rectangle([-8.1, 12.55, -7.9, 12.70]);
    var elevation = srtm.select('elevation').clip(bamako);
    
    // Exporter vers Google Drive
    Export.image.toDrive({
      image: elevation,
      description: 'bamako_srtm_1arcsec',
      scale: 30,  // Résolution 30m (1 arc-seconde)
      region: bamako,
      maxPixels: 1e9
    });
    
    // Afficher dans la console
    print('Élévation min:', elevation.reduceRegion({
      reducer: ee.Reducer.min(),
      geometry: bamako,
      scale: 30
    }));
    """)
    print("   4. Cliquez sur 'Run' (en haut)")
    print("   5. Allez dans l'onglet 'Tasks' (en bas à droite)")
    print("   6. Cliquez sur 'RUN' à côté de la tâche 'bamako_srtm_1arcsec'")
    print("   7. Le fichier sera téléchargé dans votre Google Drive")
    print("   8. Téléchargez depuis Drive et placez-le dans :")
    print("      backend/data/raw/topography/")
    print("\n   ⏱️  Durée : 2-5 minutes (très simple !)")
    
    print("\n📝 Méthode 3 : CGIAR-CSI (Alternative, résolution 90m)")
    print("   ⚠️  Note : Cette source utilise SRTM 3 Arc-Second (90m), moins précis")
    print("   Pour SRTM 1 Arc-Second (30m), utilisez Méthode 1 ou 2")
    print("\n   Étapes :")
    print("   1. Visitez : https://srtm.csi.cgiar.org/srtmdata/")
    print("   2. Téléchargez la tuile pour l'Afrique de l'Ouest")
    print("   3. Format : srtm_XX_XX.tif (résolution 90m)")


def main():
    """Fonction principale"""
    downloader = TopographyDownloader()
    
    print("=" * 60)
    print("🗻 DONNÉES TOPOGRAPHIQUES POUR BAMAKO")
    print("=" * 60)
    print("\n📝 SRTM 1 Arc-Second Global (30m)")
    print("   🛡️  Protection : Retry automatique, sources alternatives")
    
    # Vérifier si des fichiers existent déjà
    try:
        tif_files = [f for f in os.listdir(downloader.download_dir) 
                     if f.endswith('.tif') or f.endswith('.hgt')]
    except OSError:
        # Répertoire n'existe pas encore
        tif_files = []
    
    if tif_files:
        print(f"\n✅ {len(tif_files)} fichier(s) SRTM trouvé(s)")
        tif_path = os.path.join(downloader.download_dir, tif_files[0])
        
        # Extraire pour les communes
        results = downloader.extract_for_communes(tif_path)
        
        # Sauvegarder
        import json
        output_file = os.path.join(
            os.path.dirname(downloader.download_dir),
            'bamako_topography.json'
        )
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Données sauvegardées : {output_file}")
        
        # Statistiques
        elevations = [r['elevation'] for r in results.values() if r['elevation'] is not None]
        slopes = [r['slope'] for r in results.values() if r['slope'] is not None]
        if elevations:
            print(f"\n📊 Statistiques :")
            print(f"   Élévation moyenne : {np.mean(elevations):.1f}m")
            print(f"   Élévation min/max : {np.min(elevations):.1f}m / {np.max(elevations):.1f}m")
            print(f"   Pente moyenne : {np.mean(slopes):.2f}°")
    else:
        print("\n❌ Aucun fichier SRTM trouvé")
        print("\n🔄 Tentative de téléchargement automatique...")
        print("   (Cela peut prendre quelques minutes)")
        
        # Essayer de télécharger
        tif_path = downloader.download_srtm_tile(downloader.srtm_tile, use_alternatives=True)
        
        if tif_path and os.path.exists(tif_path):
            print("\n" + "=" * 60)
            print("✅ TÉLÉCHARGEMENT RÉUSSI !")
            print("=" * 60)
            
            # Extraire pour les communes
            results = downloader.extract_for_communes(tif_path)
            
            # Sauvegarder
            import json
            output_file = os.path.join(
                os.path.dirname(downloader.download_dir),
                'bamako_topography.json'
            )
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n✅ Données sauvegardées : {output_file}")
            
            # Statistiques
            elevations = [r['elevation'] for r in results.values() if r['elevation'] is not None]
            slopes = [r['slope'] for r in results.values() if r['slope'] is not None]
            if elevations:
                print(f"\n📊 Statistiques :")
                print(f"   Élévation moyenne : {np.mean(elevations):.1f}m")
                print(f"   Élévation min/max : {np.min(elevations):.1f}m / {np.max(elevations):.1f}m")
                print(f"   Pente moyenne : {np.mean(slopes):.2f}°")
        else:
            print("\n" + "=" * 60)
            print("⚠️  TÉLÉCHARGEMENT AUTOMATIQUE ÉCHOUÉ")
            print("=" * 60)
            print("\n📝 Utilisez une des méthodes manuelles ci-dessous :")
            print("   (Recommandé : Google Earth Engine - Méthode 2)")
            print("\n" + "=" * 60)
            download_from_earthdata()


if __name__ == '__main__':
    main()

