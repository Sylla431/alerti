"""
Configuration des 6 communes de Bamako pour la prédiction d'inondations
"""

# Coordonnées approximatives des centres des 6 communes de Bamako
BAMAKO_COMMUNES = {
    'Commune I': {
        'lat': 12.6563,
        'lon': -7.9928,
        'description': 'Centre administratif, marché de Médina Coura',
        'population': 335000,
        'zones_risque': ['Médina Coura', 'Banconi', 'Djélibougou']
    },
    'Commune II': {
        'lat': 12.6389,
        'lon': -8.0029,
        'description': 'Centre-ville, Koulouba, Hipodrome',
        'population': 159000,
        'zones_risque': ['Niaréla', 'Bagadadji', 'Quinzambougou']
    },
    'Commune III': {
        'lat': 12.6208,
        'lon': -8.0192,
        'description': 'Zone industrielle, Point G',
        'population': 128000,
        'zones_risque': ['Point G', 'Niagabougou', 'Badialan III']
    },
    'Commune IV': {
        'lat': 12.6531,
        'lon': -8.0331,
        'description': 'Rive droite du fleuve Niger, Lafiabougou',
        'population': 200000,
        'zones_risque': ['Lafiabougou', 'Djikoroni-Para', 'Taliko']
    },
    'Commune V': {
        'lat': 12.5989,
        'lon': -8.0508,
        'description': 'Zone périurbaine, Sabalibougou',
        'population': 250000,
        'zones_risque': ['Sabalibougou', 'Daoudabougou', 'Kalaban-Coura']
    },
    'Commune VI': {
        'lat': 12.6144,
        'lon': -7.9453,
        'description': 'Rive gauche, Sogoniko, Aéroport',
        'population': 600000,
        'zones_risque': ['Sogoniko', 'Magnambougou', 'Sénou']
    }
}

# Bounding box globale pour Bamako (pour les images satellites)
BAMAKO_BBOX = {
    'lon_min': -8.10,
    'lat_min': 12.55,
    'lon_max': -7.90,
    'lat_max': 12.70
}

# Informations générales sur Bamako
BAMAKO_INFO = {
    'name': 'Bamako',
    'country': 'Mali',
    'total_population': 1672000,  # Estimation
    'elevation_min': 320,  # mètres
    'elevation_max': 350,  # mètres
    'fleuve': 'Niger',
    'saison_pluies': {
        'debut': 'Mai',
        'fin': 'Octobre',
        'pics': ['Août', 'Septembre']
    },
    'risque_inondation': 'Élevé pendant la saison des pluies'
}


def get_commune_coords(commune_name):
    """Récupère les coordonnées d'une commune"""
    if commune_name in BAMAKO_COMMUNES:
        commune = BAMAKO_COMMUNES[commune_name]
        return commune['lat'], commune['lon']
    return None, None


def get_all_communes():
    """Retourne la liste de toutes les communes"""
    return list(BAMAKO_COMMUNES.keys())


def get_commune_info(commune_name):
    """Récupère toutes les informations d'une commune"""
    return BAMAKO_COMMUNES.get(commune_name, None)


def format_for_chirps():
    """Formate les communes pour extraction CHIRPS"""
    result = {}
    for commune, info in BAMAKO_COMMUNES.items():
        result[commune] = {
            'lat': info['lat'],
            'lon': info['lon']
        }
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("📍 COMMUNES DE BAMAKO")
    print("=" * 60)
    
    for commune, info in BAMAKO_COMMUNES.items():
        print(f"\n{commune}")
        print(f"  Coordonnées : {info['lat']:.4f}°N, {info['lon']:.4f}°W")
        print(f"  Population : {info['population']:,}")
        print(f"  {info['description']}")
        print(f"  Zones à risque : {', '.join(info['zones_risque'])}")
    
    print(f"\n\n📊 BAMAKO - Vue d'ensemble")
    print(f"  Population totale : {BAMAKO_INFO['total_population']:,}")
    print(f"  Saison des pluies : {BAMAKO_INFO['saison_pluies']['debut']} - {BAMAKO_INFO['saison_pluies']['fin']}")
    print(f"  Risque : {BAMAKO_INFO['risque_inondation']}")

