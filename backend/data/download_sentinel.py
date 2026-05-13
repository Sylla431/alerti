"""
Script pour télécharger les images Sentinel via l'API Copernicus
Nécessite un compte gratuit sur https://scihub.copernicus.eu/
"""
import os
import requests
from datetime import datetime, timedelta
import json

class SentinelDownloader:
    """Télécharge les images Sentinel-1/2"""
    
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.base_url = "https://scihub.copernicus.eu/dhus"
        self.download_dir = os.path.join(
            os.path.dirname(__file__), 'raw', 'sentinel'
        )
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Zones d'intérêt pour le Mali (bounding boxes)
        self.mali_areas = {
            'Bamako': {
                'lat': 12.6392,
                'lon': -8.0029,
                'bbox': (-8.1, 12.5, -7.9, 12.7)  # (lon_min, lat_min, lon_max, lat_max)
            },
            'Sikasso': {
                'lat': 11.3177,
                'lon': -5.6671,
                'bbox': (-5.8, 11.2, -5.6, 11.4)
            },
            'Ségou': {
                'lat': 13.4317,
                'lon': -6.2633,
                'bbox': (-6.4, 13.3, -6.2, 13.5)
            },
            'Mopti': {
                'lat': 14.4843,
                'lon': -4.1960,
                'bbox': (-4.3, 14.4, -4.1, 14.6)
            }
        }
    
    def search_products(self, area_name, start_date, end_date, product_type='S1'):
        """
        Recherche les produits Sentinel disponibles
        product_type: 'S1' (radar) ou 'S2' (optique)
        """
        if area_name not in self.mali_areas:
            print(f"❌ Zone inconnue : {area_name}")
            return None
            
        bbox = self.mali_areas[area_name]['bbox']
        
        # Construire la requête
        footprint = f"POLYGON(({bbox[0]} {bbox[1]},{bbox[2]} {bbox[1]},{bbox[2]} {bbox[3]},{bbox[0]} {bbox[3]},{bbox[0]} {bbox[1]}))"
        
        # Filtres
        platform = "Sentinel-1" if product_type == 'S1' else "Sentinel-2"
        
        query = (
            f"platformname:{platform} AND "
            f"footprint:\"Intersects({footprint})\" AND "
            f"beginPosition:[{start_date}T00:00:00.000Z TO {end_date}T23:59:59.999Z]"
        )
        
        if product_type == 'S1':
            query += " AND producttype:GRD"  # Ground Range Detected
        else:
            query += " AND producttype:S2MSI2A AND cloudcoverpercentage:[0 TO 20]"  # < 20% nuages
        
        # Requête API
        search_url = f"{self.base_url}/search?q={query}&rows=100"
        
        try:
            print(f"🔍 Recherche {platform} pour {area_name}...")
            response = requests.get(
                search_url,
                auth=(self.username, self.password),
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✅ Recherche terminée")
                return response.text
            elif response.status_code == 401:
                print(f"❌ Erreur d'authentification (vérifiez vos identifiants)")
                return None
            else:
                print(f"❌ Erreur recherche : {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur : {e}")
            return None
    
    def download_product(self, product_id, product_name):
        """Télécharge un produit Sentinel"""
        download_url = f"{self.base_url}/odata/v1/Products('{product_id}')/$value"
        local_path = os.path.join(self.download_dir, f"{product_name}.zip")
        
        if os.path.exists(local_path):
            print(f"  ⏭️  Déjà téléchargé : {product_name}")
            return local_path
        
        try:
            print(f"  📥 Téléchargement : {product_name}...")
            response = requests.get(
                download_url,
                auth=(self.username, self.password),
                stream=True,
                timeout=600
            )
            
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                
                with open(local_path, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Afficher progression
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"     {percent:.1f}%", end='\r')
                
                print(f"  ✅ Téléchargé : {product_name}")
                return local_path
            else:
                print(f"  ❌ Erreur : {response.status_code}")
                return None
                
        except Exception as e:
            print(f"  ❌ Erreur : {e}")
            return None


def main():
    """Fonction principale"""
    print("=" * 60)
    print("🛰️  TÉLÉCHARGEMENT DES IMAGES SENTINEL")
    print("=" * 60)
    
    print("\n📝 IMPORTANT : Ce script nécessite un compte Copernicus")
    print("   Créez un compte gratuit sur : https://scihub.copernicus.eu/")
    print()
    print("💡 ALTERNATIVE RECOMMANDÉE : Digital Earth Africa")
    print("   Plus facile d'utilisation et optimisé pour l'Afrique")
    print("   https://www.digitalearthafrica.org/")
    print()
    
    choice = input("Voulez-vous continuer avec Copernicus ? (o/n) : ")
    
    if choice.lower() != 'o':
        print("\n✅ Utilisez plutôt Digital Earth Africa :")
        print("   1. Visitez : https://maps.digitalearth.africa/")
        print("   2. Sélectionnez votre zone au Mali")
        print("   3. Téléchargez les images Sentinel-1/2")
        print("   4. Placez-les dans : backend/data/raw/sentinel/")
        return
    
    # Demander les identifiants
    username = input("\nNom d'utilisateur Copernicus : ")
    password = input("Mot de passe : ")
    
    downloader = SentinelDownloader(username, password)
    
    # Rechercher des images pour Bamako (saison des pluies)
    print("\n🔍 Recherche d'images Sentinel-1 pour Bamako...")
    print("   (Saison des pluies 2023 : juin-septembre)")
    
    start_date = "2023-06-01"
    end_date = "2023-09-30"
    
    results = downloader.search_products('Bamako', start_date, end_date, 'S1')
    
    if results:
        # Sauvegarder les résultats
        results_file = 'sentinel_search_results.xml'
        with open(results_file, 'w') as f:
            f.write(results)
        print(f"\n✅ Résultats sauvegardés dans : {results_file}")
        print("\n📝 Prochaines étapes :")
        print("   1. Consultez sentinel_search_results.xml")
        print("   2. Utilisez sentinelsat pour télécharger : pip install sentinelsat")
        print("   3. Ou téléchargez manuellement via l'interface web")
    
    print("\n" + "=" * 60)
    print("💡 CONSEIL FINAL")
    print("=" * 60)
    print("Pour le Mali, utilisez plutôt :")
    print("  • Digital Earth Africa (plus facile)")
    print("  • Google Earth Engine (API Python)")
    print("  • NASA Earthdata (gratuit)")


if __name__ == '__main__':
    main()

