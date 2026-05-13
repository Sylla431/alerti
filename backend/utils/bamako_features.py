"""
Features statiques et géographiques pour les 6 communes de Bamako
Données topographiques, hydrologiques, urbanisation, infrastructure
"""
import numpy as np
from .bamako_communes import BAMAKO_COMMUNES

# Features statiques par commune (à compléter avec vraies données)
BAMAKO_STATIC_FEATURES = {
    'Commune I': {
        # Topographie
        'elevation': 330,  # mètres (moyenne)
        'elevation_min': 320,
        'elevation_max': 340,
        'slope': 2.5,  # degrés (pente moyenne)
        'distance_to_river': 1200,  # mètres (distance au Niger)
        'in_flood_plain': 0,  # 0=non, 1=oui
        'depression_depth': 0.5,  # mètres (profondeur cuvettes)
        
        # Urbanisation
        'impermeable_surface': 65,  # % surface imperméable
        'building_density': 45,  # % surface bâtie
        'population_density': 8500,  # hab/km²
        'land_use_residential': 60,  # %
        'land_use_commercial': 25,  # %
        'land_use_industrial': 5,  # %
        'land_use_other': 10,  # %
        
        # Infrastructure drainage
        'drainage_density': 3.2,  # km canaux / km²
        'drainage_state': 2,  # 1=mauvais, 5=excellent
        'drainage_coverage': 40,  # % zone couverte par drainage
        'pumping_stations': 0,  # nombre
        'blocked_drainage_pct': 35,  # % canaux bouchés
        
        # Hydrologie
        'groundwater_level': 8,  # mètres (profondeur nappe)
        'runoff_coefficient': 0.75,  # coefficient ruissellement
        'infiltration_rate': 15,  # mm/h
        'soil_type': 'latéritique',  # Type de sol
        'soil_permeability': 2,  # 1=imperméable, 5=très perméable
        
        # Végétation
        'vegetation_cover': 15,  # % couverture végétale
        'ndvi_avg': 0.25,  # Index végétation normalisé
        
        # Vulnérabilité
        'informal_settlement_pct': 30,  # % habitat précaire
        'poverty_index': 45,  # Indice pauvreté (0-100)
        'flood_preparedness': 2,  # 1=faible, 5=élevé
    },
    'Commune II': {
        'elevation': 335,
        'elevation_min': 325,
        'elevation_max': 345,
        'slope': 3.0,
        'distance_to_river': 800,
        'in_flood_plain': 0,
        'depression_depth': 0.3,
        'impermeable_surface': 70,
        'building_density': 50,
        'population_density': 12000,
        'land_use_residential': 40,
        'land_use_commercial': 35,
        'land_use_industrial': 10,
        'land_use_other': 15,
        'drainage_density': 4.5,
        'drainage_state': 3,
        'drainage_coverage': 55,
        'pumping_stations': 1,
        'blocked_drainage_pct': 25,
        'groundwater_level': 7,
        'runoff_coefficient': 0.80,
        'infiltration_rate': 12,
        'soil_type': 'latéritique',
        'soil_permeability': 2,
        'vegetation_cover': 12,
        'ndvi_avg': 0.22,
        'informal_settlement_pct': 20,
        'poverty_index': 35,
        'flood_preparedness': 3,
    },
    'Commune III': {
        'elevation': 340,
        'elevation_min': 330,
        'elevation_max': 350,
        'slope': 4.0,
        'distance_to_river': 2000,
        'in_flood_plain': 0,
        'depression_depth': 0.2,
        'impermeable_surface': 55,
        'building_density': 40,
        'population_density': 6500,
        'land_use_residential': 50,
        'land_use_commercial': 20,
        'land_use_industrial': 20,
        'land_use_other': 10,
        'drainage_density': 2.8,
        'drainage_state': 2,
        'drainage_coverage': 35,
        'pumping_stations': 0,
        'blocked_drainage_pct': 40,
        'groundwater_level': 10,
        'runoff_coefficient': 0.70,
        'infiltration_rate': 18,
        'soil_type': 'latéritique',
        'soil_permeability': 3,
        'vegetation_cover': 20,
        'ndvi_avg': 0.30,
        'informal_settlement_pct': 25,
        'poverty_index': 40,
        'flood_preparedness': 2,
    },
    'Commune IV': {
        'elevation': 325,
        'elevation_min': 315,
        'elevation_max': 335,
        'slope': 1.5,
        'distance_to_river': 500,  # Plus proche du Niger
        'in_flood_plain': 1,  # DANS la plaine inondable
        'depression_depth': 1.2,  # Plus de cuvettes
        'impermeable_surface': 60,
        'building_density': 50,
        'population_density': 10000,
        'land_use_residential': 70,
        'land_use_commercial': 15,
        'land_use_industrial': 5,
        'land_use_other': 10,
        'drainage_density': 2.5,  # Moins de drainage
        'drainage_state': 1,  # MAUVAIS état
        'drainage_coverage': 30,
        'pumping_stations': 0,
        'blocked_drainage_pct': 50,  # Beaucoup bouchés
        'groundwater_level': 5,  # Nappe plus proche
        'runoff_coefficient': 0.85,
        'infiltration_rate': 10,
        'soil_type': 'argileux',
        'soil_permeability': 1,  # Très imperméable
        'vegetation_cover': 10,
        'ndvi_avg': 0.18,
        'informal_settlement_pct': 50,  # Beaucoup d'habitat précaire
        'poverty_index': 60,
        'flood_preparedness': 1,  # Très faible
    },
    'Commune V': {
        'elevation': 322,
        'elevation_min': 310,
        'elevation_max': 330,
        'slope': 1.0,
        'distance_to_river': 300,  # Très proche du Niger
        'in_flood_plain': 1,
        'depression_depth': 1.5,  # Beaucoup de cuvettes
        'impermeable_surface': 55,
        'building_density': 45,
        'population_density': 12500,
        'land_use_residential': 75,
        'land_use_commercial': 10,
        'land_use_industrial': 5,
        'land_use_other': 10,
        'drainage_density': 2.0,  # Très peu de drainage
        'drainage_state': 1,
        'drainage_coverage': 25,
        'pumping_stations': 0,
        'blocked_drainage_pct': 55,
        'groundwater_level': 4,
        'runoff_coefficient': 0.90,
        'infiltration_rate': 8,
        'soil_type': 'argileux',
        'soil_permeability': 1,
        'vegetation_cover': 8,
        'ndvi_avg': 0.15,
        'informal_settlement_pct': 60,  # Zone très précaire
        'poverty_index': 70,
        'flood_preparedness': 1,
    },
    'Commune VI': {
        'elevation': 328,
        'elevation_min': 318,
        'elevation_max': 338,
        'slope': 2.0,
        'distance_to_river': 1500,
        'in_flood_plain': 0,
        'depression_depth': 0.4,
        'impermeable_surface': 58,
        'building_density': 42,
        'population_density': 30000,  # Très dense
        'land_use_residential': 65,
        'land_use_commercial': 20,
        'land_use_industrial': 8,
        'land_use_other': 7,
        'drainage_density': 3.5,
        'drainage_state': 2,
        'drainage_coverage': 40,
        'pumping_stations': 0,
        'blocked_drainage_pct': 30,
        'groundwater_level': 9,
        'runoff_coefficient': 0.75,
        'infiltration_rate': 14,
        'soil_type': 'latéritique',
        'soil_permeability': 2,
        'vegetation_cover': 12,
        'ndvi_avg': 0.20,
        'informal_settlement_pct': 35,
        'poverty_index': 50,
        'flood_preparedness': 2,
    }
}

# Coordonnées du fleuve Niger à Bamako (pour calcul distance)
NIGER_RIVER_BAMAKO = {
    'lat': 12.65,
    'lon': -8.00,
    'segments': [
        {'lat': 12.66, 'lon': -8.05},  # Segment nord
        {'lat': 12.65, 'lon': -8.00},  # Segment centre
        {'lat': 12.64, 'lon': -7.95},  # Segment sud
    ]
}


def get_static_features(commune_name):
    """Récupère toutes les features statiques d'une commune"""
    return BAMAKO_STATIC_FEATURES.get(commune_name, {})


def get_all_static_features():
    """Retourne toutes les features statiques pour toutes les communes"""
    return BAMAKO_STATIC_FEATURES


def calculate_distance_to_river(lat, lon):
    """Calcule la distance au fleuve Niger (en mètres)"""
    import math
    
    river_lat = NIGER_RIVER_BAMAKO['lat']
    river_lon = NIGER_RIVER_BAMAKO['lon']
    
    # Formule de Haversine
    R = 6371000  # Rayon Terre en mètres
    
    dlat = math.radians(lat - river_lat)
    dlon = math.radians(lon - river_lon)
    
    a = (math.sin(dlat/2)**2 + 
         math.cos(math.radians(river_lat)) * 
         math.cos(math.radians(lat)) * 
         math.sin(dlon/2)**2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance


def get_risk_factors(commune_name):
    """Calcule un score de risque basé sur les features statiques"""
    features = get_static_features(commune_name)
    
    if not features:
        return None
    
    # Facteurs de risque (0-1, 1 = très risqué)
    risk_factors = {
        'topography_risk': (
            (1 - features['elevation'] / 400) * 0.3 +  # Plus bas = plus risqué
            (features['depression_depth'] / 2) * 0.3 +  # Cuves = risqué
            (1 if features['in_flood_plain'] else 0) * 0.4
        ),
        'drainage_risk': (
            (1 - features['drainage_density'] / 10) * 0.3 +  # Moins drainage = risqué
            (1 - features['drainage_state'] / 5) * 0.4 +  # Mauvais état = risqué
            (features['blocked_drainage_pct'] / 100) * 0.3  # Bouchés = risqué
        ),
        'urbanization_risk': (
            (features['impermeable_surface'] / 100) * 0.4 +  # Imperméable = risqué
            (1 - features['infiltration_rate'] / 50) * 0.3 +  # Infiltration faible = risqué
            (features['runoff_coefficient']) * 0.3  # Ruissellement élevé = risqué
        ),
        'vulnerability_risk': (
            (features['informal_settlement_pct'] / 100) * 0.4 +
            (features['poverty_index'] / 100) * 0.3 +
            (1 - features['flood_preparedness'] / 5) * 0.3
        )
    }
    
    # Risque total (moyenne pondérée)
    total_risk = (
        risk_factors['topography_risk'] * 0.3 +
        risk_factors['drainage_risk'] * 0.3 +
        risk_factors['urbanization_risk'] * 0.25 +
        risk_factors['vulnerability_risk'] * 0.15
    )
    
    risk_factors['total_risk'] = total_risk
    
    return risk_factors


if __name__ == '__main__':
    print("=" * 60)
    print("📊 FEATURES STATIQUES - 6 COMMUNES DE BAMAKO")
    print("=" * 60)
    
    for commune in BAMAKO_STATIC_FEATURES.keys():
        print(f"\n🏘️  {commune}")
        features = get_static_features(commune)
        risk = get_risk_factors(commune)
        
        print(f"  📍 Topographie:")
        print(f"     Élévation : {features['elevation']}m")
        print(f"     Pente : {features['slope']}°")
        print(f"     Distance au Niger : {features['distance_to_river']}m")
        print(f"     Plaine inondable : {'Oui' if features['in_flood_plain'] else 'Non'}")
        
        print(f"  🏗️  Infrastructure:")
        print(f"     Drainage : {features['drainage_density']:.1f} km/km²")
        print(f"     État drainage : {features['drainage_state']}/5")
        print(f"     Canaux bouchés : {features['blocked_drainage_pct']}%")
        
        print(f"  🏙️  Urbanisation:")
        print(f"     Surface imperméable : {features['impermeable_surface']}%")
        print(f"     Densité bâtiments : {features['building_density']}%")
        
        print(f"  ⚠️  Risque total : {risk['total_risk']:.2f} ({'ÉLEVÉ' if risk['total_risk'] > 0.6 else 'MOYEN' if risk['total_risk'] > 0.4 else 'FAIBLE'})")

