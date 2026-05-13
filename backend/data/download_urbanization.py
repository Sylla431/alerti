"""
Script pour télécharger les données d'urbanisation depuis OpenStreetMap
Extrait : bâtiments, densité, imperméabilisation pour les 6 communes de Bamako
"""
import os
import sys
import time

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
import numpy as np
import pandas as pd
from collections import defaultdict

# Coordonnées des 6 communes
from utils.bamako_communes import BAMAKO_COMMUNES

# Bounding box pour chaque commune (approximatif)
COMMUNE_BBOX = {
    'Commune I': {'lat_min': 12.64, 'lat_max': 12.67, 'lon_min': -8.00, 'lon_max': -7.98},
    'Commune II': {'lat_min': 12.63, 'lat_max': 12.65, 'lon_min': -8.01, 'lon_max': -7.99},
    'Commune III': {'lat_min': 12.61, 'lat_max': 12.63, 'lon_min': -8.03, 'lon_max': -8.01},
    'Commune IV': {'lat_min': 12.64, 'lat_max': 12.67, 'lon_min': -8.04, 'lon_max': -8.02},
    'Commune V': {'lat_min': 12.59, 'lat_max': 12.61, 'lon_min': -8.06, 'lon_max': -8.04},
    'Commune VI': {'lat_min': 12.60, 'lat_max': 12.63, 'lon_min': -7.95, 'lon_max': -7.93}
}


class UrbanizationDownloader:
    """Télécharge les données d'urbanisation depuis OpenStreetMap"""
    
    def __init__(self):
        self.download_dir = os.path.join(
            os.path.dirname(__file__), 'raw', 'urbanization'
        )
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Plusieurs instances Overpass en rotation (pour éviter les limites)
        self.overpass_urls = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.openstreetmap.ru/api/interpreter",
            "https://overpass.nchc.org.tw/api/interpreter"
        ]
        self.current_url_index = 0
        self.request_delay = 2  # Délai entre requêtes (secondes)
        self.max_retries = 3
        self.retry_delay = 10  # Délai initial pour retry (secondes)
    
    def _make_request(self, query, request_type="buildings"):
        """Fait une requête Overpass avec retry et gestion des erreurs 429"""
        for attempt in range(self.max_retries):
            url = self.overpass_urls[self.current_url_index]
            
            try:
                print(f"  📡 Requête {request_type} (tentative {attempt + 1}/{self.max_retries})...")
                print(f"     Instance: {url.split('//')[1].split('/')[0]}")
                
                response = requests.post(url, data=query, timeout=180)
                
                # Gérer erreur 429 (Too Many Requests)
                if response.status_code == 429:
                    wait_time = self.retry_delay * (2 ** attempt)  # Backoff exponentiel
                    print(f"  ⚠️  Limite de taux atteinte (429). Attente {wait_time}s...")
                    time.sleep(wait_time)
                    
                    # Changer d'instance
                    self.current_url_index = (self.current_url_index + 1) % len(self.overpass_urls)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"  ⚠️  Erreur réseau: {e}")
                    print(f"     Nouvelle tentative dans {wait_time}s...")
                    time.sleep(wait_time)
                    
                    # Changer d'instance
                    self.current_url_index = (self.current_url_index + 1) % len(self.overpass_urls)
                else:
                    print(f"  ❌ Erreur après {self.max_retries} tentatives: {e}")
                    return None
            except Exception as e:
                print(f"  ❌ Erreur inattendue: {e}")
                return None
        
        return None
    
    def query_buildings(self, bbox):
        """Requête Overpass pour les bâtiments"""
        query = f"""
        [out:json][timeout:60];
        (
          way["building"]({bbox['lat_min']},{bbox['lon_min']},{bbox['lat_max']},{bbox['lon_max']});
        );
        out geom;
        """
        
        result = self._make_request(query, "bâtiments")
        
        # Délai entre requêtes pour éviter les limites
        if result is not None:
            time.sleep(self.request_delay)
        
        return result
    
    def query_drainage(self, bbox):
        """Requête Overpass pour les canaux de drainage"""
        query = f"""
        [out:json][timeout:60];
        (
          way["waterway"="drain"]({bbox['lat_min']},{bbox['lon_min']},{bbox['lat_max']},{bbox['lon_max']});
          way["waterway"="ditch"]({bbox['lat_min']},{bbox['lon_min']},{bbox['lat_max']},{bbox['lon_max']});
          way["waterway"="canal"]({bbox['lat_min']},{bbox['lon_min']},{bbox['lat_max']},{bbox['lon_max']});
        );
        out geom;
        """
        
        result = self._make_request(query, "drainage")
        
        # Délai entre requêtes pour éviter les limites
        if result is not None:
            time.sleep(self.request_delay)
        
        return result
    
    def _normalize_coords(self, coords):
        """Normalise les coordonnées en format {lat, lon}"""
        if not coords or len(coords) == 0:
            return None
        
        first = coords[0]
        
        # Format dict {lat, lon}
        if isinstance(first, dict):
            if 'lat' in first and 'lon' in first:
                return coords
            elif 'y' in first and 'x' in first:
                # Format {y: lat, x: lon}
                return [{'lat': c['y'], 'lon': c['x']} for c in coords]
        
        # Format list [lat, lon] ou [lon, lat]
        elif isinstance(first, list) and len(first) >= 2:
            # Détecter l'ordre : si lat > 90 ou lon > 180, c'est inversé
            test_val = abs(first[0])
            if test_val > 90:
                # Probablement [lon, lat] inversé
                return [{'lat': c[1], 'lon': c[0]} for c in coords]
            else:
                # Probablement [lat, lon]
                return [{'lat': c[0], 'lon': c[1]} for c in coords]
        
        return None
    
    def calculate_building_area(self, elements):
        """Calcule la surface totale des bâtiments"""
        total_area = 0
        processed = 0
        
        for element in elements:
            if element['type'] == 'way':
                # Avec 'out geom', la géométrie est dans 'geometry'
                if 'geometry' in element:
                    coords_raw = element['geometry']
                    if len(coords_raw) >= 3:
                        coords = self._normalize_coords(coords_raw)
                        if coords:
                            area = self._polygon_area(coords)
                            if area > 0:
                                total_area += area
                                processed += 1
        
        if processed > 0:
            print(f"    📐 {processed} bâtiments avec géométrie calculée")
        
        return total_area
    
    def _polygon_area(self, coords):
        """Calcule l'aire d'un polygone en m² (approximation pour petits polygones)"""
        if len(coords) < 3:
            return 0
        
        # Pour les petits polygones (bâtiments), utiliser la formule de Shoelace
        # après conversion en coordonnées locales (mètres)
        R = 6371000  # Rayon Terre en mètres
        
        # Convertir les coordonnées en mètres (projection locale)
        # Utiliser le centre du polygone comme référence
        lats = [c['lat'] for c in coords]
        lons = [c['lon'] for c in coords]
        lat_center = np.mean(lats)
        lon_center = np.mean(lons)
        
        # Convertir en mètres (approximation plate pour petits polygones)
        x_coords = []
        y_coords = []
        for lat, lon in zip(lats, lons):
            # Conversion en mètres depuis le centre
            dx = (lon - lon_center) * 111000 * np.cos(np.radians(lat_center))
            dy = (lat - lat_center) * 111000
            x_coords.append(dx)
            y_coords.append(dy)
        
        # Formule de Shoelace
        area = 0.0
        n = len(x_coords)
        for i in range(n):
            j = (i + 1) % n
            area += x_coords[i] * y_coords[j]
            area -= x_coords[j] * y_coords[i]
        
        area = abs(area) / 2.0  # Aire en m²
        
        return area
    
    def calculate_drainage_length(self, elements):
        """Calcule la longueur totale des canaux"""
        total_length = 0
        processed = 0
        
        for element in elements:
            if element['type'] == 'way' and 'geometry' in element:
                coords_raw = element['geometry']
                
                if len(coords_raw) >= 2:
                    coords = self._normalize_coords(coords_raw)
                    if coords:
                        # Calculer la longueur
                        for i in range(len(coords) - 1):
                            lat1, lon1 = coords[i]['lat'], coords[i]['lon']
                            lat2, lon2 = coords[i+1]['lat'], coords[i+1]['lon']
                            
                            # Distance Haversine
                            length = self._haversine_distance(lat1, lon1, lat2, lon2)
                            total_length += length
                            processed += 1
        
        if processed > 0:
            print(f"    📏 {processed} segments de drainage calculés")
        
        return total_length
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calcule la distance entre deux points (Haversine)"""
        import math
        
        R = 6371000  # Rayon Terre en mètres
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(math.radians(lat1)) * 
             math.cos(math.radians(lat2)) * 
             math.sin(dlon/2)**2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def calculate_commune_area(self, bbox):
        """Calcule la surface d'une commune en km²"""
        lat_range = bbox['lat_max'] - bbox['lat_min']
        lon_range = bbox['lon_max'] - bbox['lon_min']
        lat_center = (bbox['lat_max'] + bbox['lat_min']) / 2
        
        # Convertir en km²
        lat_km = lat_range * 111.0  # 1 degré lat ≈ 111 km
        lon_km = lon_range * 111.0 * np.cos(np.radians(lat_center))
        area_km2 = lat_km * lon_km
        
        return area_km2
    
    def extract_for_commune(self, commune_name):
        """Extrait toutes les données d'urbanisation pour une commune"""
        print(f"\n🏘️  Traitement : {commune_name}")
        
        if commune_name not in COMMUNE_BBOX:
            print(f"  ❌ Bbox non définie pour {commune_name}")
            return None
        
        bbox = COMMUNE_BBOX[commune_name]
        commune_area_km2 = self.calculate_commune_area(bbox)
        
        # 1. Bâtiments
        buildings_data = self.query_buildings(bbox)
        if buildings_data and 'elements' in buildings_data:
            building_area_m2 = self.calculate_building_area(buildings_data['elements'])
            building_area_km2 = building_area_m2 / 1000000
            building_density = (building_area_km2 / commune_area_km2) * 100 if commune_area_km2 > 0 else 0
            num_buildings = len([e for e in buildings_data['elements'] if e['type'] == 'way'])
        else:
            building_area_km2 = 0
            building_density = 0
            num_buildings = 0
        
        # 2. Drainage
        drainage_data = self.query_drainage(bbox)
        if drainage_data and 'elements' in drainage_data:
            drainage_length_m = self.calculate_drainage_length(drainage_data['elements'])
            drainage_length_km = drainage_length_m / 1000
            drainage_density = drainage_length_km / commune_area_km2 if commune_area_km2 > 0 else 0
            num_drains = len([e for e in drainage_data['elements'] if e['type'] == 'way'])
        else:
            drainage_length_km = 0
            drainage_density = 0
            num_drains = 0
        
        # 3. Imperméabilisation (approximation)
        # Surface imperméable ≈ surface bâtie + routes (estimé)
        impermeable_surface = min(100, building_density * 1.3)  # Bâtiments + routes
        
        results = {
            'commune': commune_name,
            'area_km2': commune_area_km2,
            'num_buildings': num_buildings,
            'building_area_km2': building_area_km2,
            'building_density_pct': building_density,
            'impermeable_surface_pct': impermeable_surface,
            'num_drains': num_drains,
            'drainage_length_km': drainage_length_km,
            'drainage_density': drainage_density
        }
        
        print(f"  ✅ Bâtiments : {num_buildings} ({building_density:.1f}% surface)")
        print(f"  ✅ Drainage : {drainage_length_km:.2f} km ({drainage_density:.2f} km/km²)")
        print(f"  ✅ Imperméabilisation : {impermeable_surface:.1f}%")
        
        return results
    
    def _load_existing_results(self):
        """Charge les résultats existants pour reprendre"""
        output_json = os.path.join(
            os.path.dirname(self.download_dir),
            'bamako_urbanization.json'
        )
        
        if os.path.exists(output_json):
            try:
                with open(output_json, 'r') as f:
                    existing = json.load(f)
                # Créer un dict pour accès rapide
                return {r['commune']: r for r in existing}
            except:
                return {}
        return {}
    
    def _save_results(self, all_results):
        """Sauvegarde les résultats"""
        if not all_results:
            return
        
        df = pd.DataFrame(all_results)
        output_file = os.path.join(
            os.path.dirname(self.download_dir),
            'bamako_urbanization.csv'
        )
        df.to_csv(output_file, index=False)
        
        output_json = os.path.join(
            os.path.dirname(self.download_dir),
            'bamako_urbanization.json'
        )
        with open(output_json, 'w') as f:
            json.dump(all_results, f, indent=2)
    
    def extract_all_communes(self):
        """Extrait les données pour toutes les communes"""
        print("=" * 60)
        print("🏙️  EXTRACTION DONNÉES URBANISATION - BAMAKO")
        print("=" * 60)
        
        # Charger les résultats existants
        existing_results = self._load_existing_results()
        if existing_results:
            print(f"\n📂 {len(existing_results)} commune(s) déjà traitée(s)")
            print("   Reprise de l'extraction...")
        
        all_results = []
        communes_list = list(BAMAKO_COMMUNES.keys())
        
        for i, commune in enumerate(communes_list, 1):
            # Vérifier si déjà traité
            if commune in existing_results:
                print(f"\n⏭️  {commune} (déjà traité, saut)")
                all_results.append(existing_results[commune])
                continue
            
            print(f"\n[{i}/{len(communes_list)}] Traitement de {commune}...")
            results = self.extract_for_commune(commune)
            if results:
                all_results.append(results)
                # Sauvegarder progressivement
                self._save_results(all_results)
                print(f"  💾 Progression sauvegardée ({i}/{len(communes_list)})")
            else:
                print(f"  ⚠️  Aucune donnée pour {commune}")
                # Ajouter un résultat vide pour ne pas perdre la progression
                all_results.append({
                    'commune': commune,
                    'area_km2': self.calculate_commune_area(COMMUNE_BBOX[commune]) if commune in COMMUNE_BBOX else 0,
                    'num_buildings': 0,
                    'building_area_km2': 0,
                    'building_density_pct': 0,
                    'impermeable_surface_pct': 0.0,
                    'num_drains': 0,
                    'drainage_length_km': 0,
                    'drainage_density': 0
                })
                self._save_results(all_results)
        
        # Sauvegarder final et afficher statistiques
        if all_results:
            self._save_results(all_results)
            df = pd.DataFrame(all_results)
            
            output_file = os.path.join(
                os.path.dirname(self.download_dir),
                'bamako_urbanization.csv'
            )
            output_json = os.path.join(
                os.path.dirname(self.download_dir),
                'bamako_urbanization.json'
            )
            
            print("\n" + "=" * 60)
            print("✅ EXTRACTION TERMINÉE !")
            print("=" * 60)
            print(f"\n📄 Fichiers créés :")
            print(f"   {output_file}")
            print(f"   {output_json}")
            
            # Statistiques globales
            print(f"\n📊 Statistiques globales :")
            print(f"   Bâtiments totaux : {df['num_buildings'].sum():,}")
            print(f"   Surface bâtie : {df['building_area_km2'].sum():.2f} km²")
            print(f"   Drainage total : {df['drainage_length_km'].sum():.2f} km")
            print(f"   Densité drainage moyenne : {df['drainage_density'].mean():.2f} km/km²")
            
            return df
        else:
            print("\n❌ Aucune donnée extraite")
            return None


def main():
    """Fonction principale"""
    downloader = UrbanizationDownloader()
    
    print("=" * 60)
    print("🏙️  TÉLÉCHARGEMENT DONNÉES URBANISATION")
    print("=" * 60)
    print("\n📝 Source : OpenStreetMap (Overpass API)")
    print("   Données : Bâtiments, Canaux de drainage")
    print("   ⏱️  Durée estimée : 10-15 minutes (avec délais)")
    print("\n🛡️  Protection contre les limites de taux :")
    print("   • Délai de 2s entre chaque requête")
    print("   • Retry automatique avec backoff exponentiel")
    print("   • Rotation entre plusieurs instances Overpass")
    print("   • Sauvegarde progressive (reprise possible)")
    
    # Extraire pour toutes les communes
    df = downloader.extract_all_communes()
    
    if df is not None:
        print("\n📝 Prochaine étape :")
        print("   Mettez à jour backend/utils/bamako_features.py avec ces valeurs")
        print("   ou utilisez-les directement dans prepare_bamako_data.py")


if __name__ == '__main__':
    main()

