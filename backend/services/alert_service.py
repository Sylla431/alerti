"""
Alert Service - Manages flood alerts and recommendations
"""
from datetime import datetime, timedelta
from collections import deque
from utils.config import ALERT_THRESHOLDS

class AlertService:
    """Service for managing flood alerts"""
    
    def __init__(self):
        self.alerts = deque(maxlen=100)  # Store last 100 alerts
    
    def check_alert_level(self, prediction):
        """Determine alert level from prediction probability"""
        probability = prediction.get('flood_probability', 0)
        
        if probability >= ALERT_THRESHOLDS['critical']:
            return 'critical'
        elif probability >= ALERT_THRESHOLDS['high']:
            return 'high'
        elif probability >= ALERT_THRESHOLDS['medium']:
            return 'medium'
        elif probability >= ALERT_THRESHOLDS['low']:
            return 'low'
        else:
            return 'none'
    
    def get_recommendations(self, alert_level):
        """Get recommendations based on alert level"""
        recommendations = {
            'critical': [
                '🚨 Évacuation immédiate requise',
                'Déplacez-vous vers des zones élevées',
                'Évitez toutes les zones inondées',
                'Restez à l\'écoute des émissions d\'urgence',
                'Contactez les services d\'urgence locaux',
                'Préparez un kit d\'urgence'
            ],
            'high': [
                '⚠️ Préparez un plan d\'évacuation',
                'Sécurisez vos documents importants',
                'Déplacez les objets de valeur aux étages supérieurs',
                'Surveillez de près les niveaux d\'eau',
                'Remplissez les réservoirs d\'eau potable',
                'Informez vos voisins de la situation'
            ],
            'medium': [
                '⚠️ Soyez vigilant',
                'Surveillez les mises à jour météorologiques',
                'Préparez une trousse d\'urgence',
                'Vérifiez les systèmes de drainage',
                'Planifiez les itinéraires d\'évacuation',
                'Restez informé des conditions locales'
            ],
            'low': [
                'ℹ️ Conditions normales',
                'Restez informé des conditions météorologiques',
                'Gardez vos coordonnées d\'urgence à portée de main'
            ],
            'none': [
                '✅ Aucun risque d\'inondation détecté',
                'Continuez à surveiller les conditions'
            ]
        }
        return recommendations.get(alert_level, [])
    
    def create_alert(self, location, alert_level, prediction, lat=None, lon=None):
        """Create and store alert"""
        alert = {
            'id': len(self.alerts) + 1,
            'location': location,
            'alert_level': alert_level,
            'flood_probability': prediction.get('flood_probability', 0),
            'coordinates': {'lat': lat, 'lon': lon} if lat and lon else None,
            'timestamp': datetime.now().isoformat(),
            'recommendations': self.get_recommendations(alert_level),
            'prediction_details': prediction
        }
        self.alerts.append(alert)
        return alert
    
    def get_active_alerts(self, country=None, min_risk='low'):
        """Get all active alerts (within last 24 hours)"""
        cutoff = datetime.now() - timedelta(hours=24)
        risk_levels = ['none', 'low', 'medium', 'high', 'critical']
        min_risk_index = risk_levels.index(min_risk) if min_risk in risk_levels else 0
        
        active = []
        for alert in self.alerts:
            alert_time = datetime.fromisoformat(alert['timestamp'])
            
            # Filter by time
            if alert_time <= cutoff:
                continue
            
            # Filter by risk level
            alert_risk_index = risk_levels.index(alert['alert_level'])
            if alert_risk_index < min_risk_index:
                continue
            
            # Filter by country if specified
            if country:
                location_lower = alert['location'].lower()
                if country.lower() not in location_lower:
                    continue
            
            active.append(alert)
        
        # Sort by flood probability (highest first)
        return sorted(active, key=lambda x: x['flood_probability'], reverse=True)
    
    def get_alert_by_id(self, alert_id):
        """Get specific alert by ID"""
        for alert in self.alerts:
            if alert['id'] == alert_id:
                return alert
        return None
    
    def get_alerts_by_location(self, location):
        """Get alerts for specific location"""
        location_lower = location.lower()
        return [
            alert for alert in self.alerts
            if location_lower in alert['location'].lower()
        ]

