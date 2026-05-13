"""
Push Notification Service - Sends push notifications via Firebase Cloud Messaging
Supports both iOS and Android devices
"""
import os
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict
from utils.config import FCM_SERVER_KEY, FCM_CREDENTIALS_PATH

class PushNotificationService:
    """Service for sending push notifications via Firebase Cloud Messaging"""
    
    def __init__(self):
        self.fcm_server_key = FCM_SERVER_KEY
        self.fcm_credentials_path = FCM_CREDENTIALS_PATH
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"
        self.fcm_v1_url = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        
        # Store device tokens by location/neighborhood
        self.device_tokens = defaultdict(list)  # {location: [tokens]}
        
        # Load device tokens from file if exists
        self.tokens_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data', 'device_tokens.json'
        )
        self._load_tokens()
    
    def _load_tokens(self):
        """Load device tokens from file"""
        if os.path.exists(self.tokens_file):
            try:
                with open(self.tokens_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.device_tokens = defaultdict(list, data)
            except Exception as e:
                print(f"Error loading device tokens: {e}")
    
    def _save_tokens(self):
        """Save device tokens to file"""
        try:
            os.makedirs(os.path.dirname(self.tokens_file), exist_ok=True)
            with open(self.tokens_file, 'w', encoding='utf-8') as f:
                json.dump(dict(self.device_tokens), f, indent=2)
        except Exception as e:
            print(f"Error saving device tokens: {e}")
    
    def register_device(self, device_token: str, location: str = None, neighborhood: str = None):
        """
        Register a device token for push notifications
        Args:
            device_token: FCM device token
            location: Location/neighborhood name
            neighborhood: Specific neighborhood (optional)
        """
        key = neighborhood or location or 'all'
        
        # Check if token already exists
        if device_token not in self.device_tokens[key]:
            self.device_tokens[key].append({
                'token': device_token,
                'location': location,
                'neighborhood': neighborhood,
                'registered_at': datetime.now().isoformat()
            })
            self._save_tokens()
            return True
        return False
    
    def unregister_device(self, device_token: str):
        """Unregister a device token"""
        removed = False
        for location in list(self.device_tokens.keys()):
            self.device_tokens[location] = [
                token_data for token_data in self.device_tokens[location]
                if token_data.get('token') != device_token
            ]
            if not self.device_tokens[location]:
                del self.device_tokens[location]
            removed = True
        
        if removed:
            self._save_tokens()
        return removed
    
    def send_push_notification(self, device_token: str, alert: Dict, title: str = None, body: str = None):
        """
        Send push notification to a single device
        Args:
            device_token: FCM device token
            alert: Alert data dictionary
            title: Notification title (optional)
            body: Notification body (optional)
        """
        if not self.fcm_server_key:
            print("FCM Server Key not configured")
            return False
        
        alert_level_fr = {
            'critical': 'CRITIQUE',
            'high': 'ÉLEVÉ',
            'medium': 'MOYEN',
            'low': 'FAIBLE'
        }
        
        if not title:
            title = f"🚨 Alerte Inondation {alert_level_fr.get(alert.get('alert_level', 'low'), 'low')}"
        
        if not body:
            body = (
                f"Localisation: {alert.get('location', 'Inconnue')}\n"
                f"Probabilité: {alert.get('flood_probability', 0)*100:.1f}%"
            )
        
        # Prepare notification payload
        payload = {
            'to': device_token,
            'notification': {
                'title': title,
                'body': body,
                'sound': 'default',
                'badge': '1',
                'priority': 'high' if alert.get('alert_level') in ['critical', 'high'] else 'normal'
            },
            'data': {
                'alert_id': str(alert.get('id', '')),
                'location': alert.get('location', ''),
                'alert_level': alert.get('alert_level', 'low'),
                'flood_probability': str(alert.get('flood_probability', 0)),
                'timestamp': alert.get('timestamp', datetime.now().isoformat()),
                'type': 'flood_alert'
            },
            'priority': 'high' if alert.get('alert_level') in ['critical', 'high'] else 'normal'
        }
        
        headers = {
            'Authorization': f'key={self.fcm_server_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(self.fcm_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success') == 1:
                print(f"Push notification sent to device {device_token[:20]}...")
                return True
            else:
                print(f"Failed to send push notification: {result}")
                # Remove invalid token
                if result.get('results', [{}])[0].get('error') in ['InvalidRegistration', 'NotRegistered']:
                    self.unregister_device(device_token)
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Error sending push notification: {e}")
            return False
        except Exception as e:
            print(f"Error processing push notification: {e}")
            return False
    
    def send_alert_to_location(self, alert: Dict, location: str = None, neighborhood: str = None):
        """
        Send push notification to all devices subscribed to a location/neighborhood
        Args:
            alert: Alert data dictionary
            location: Location name
            neighborhood: Neighborhood name (optional)
        """
        keys_to_notify = []
        
        if neighborhood:
            keys_to_notify.append(neighborhood)
        if location:
            keys_to_notify.append(location)
        keys_to_notify.append('all')  # Always notify global subscribers
        
        sent_count = 0
        for key in keys_to_notify:
            tokens = self.device_tokens.get(key, [])
            for token_data in tokens:
                if isinstance(token_data, dict):
                    device_token = token_data.get('token')
                else:
                    device_token = token_data
                
                if device_token:
                    if self.send_push_notification(device_token, alert):
                        sent_count += 1
        
        return sent_count
    
    def send_batch_notifications(self, device_tokens: List[str], alert: Dict):
        """
        Send push notifications to multiple devices (batch)
        Note: FCM supports up to 1000 tokens per batch
        """
        if not self.fcm_server_key:
            print("FCM Server Key not configured")
            return 0
        
        # Split into batches of 1000
        batch_size = 1000
        total_sent = 0
        
        for i in range(0, len(device_tokens), batch_size):
            batch = device_tokens[i:i+batch_size]
            
            # FCM batch format
            payload = {
                'registration_ids': batch,
                'notification': {
                    'title': f"🚨 Alerte Inondation",
                    'body': f"Localisation: {alert.get('location', 'Inconnue')}",
                    'sound': 'default'
                },
                'data': {
                    'alert_id': str(alert.get('id', '')),
                    'location': alert.get('location', ''),
                    'alert_level': alert.get('alert_level', 'low'),
                    'type': 'flood_alert'
                },
                'priority': 'high' if alert.get('alert_level') in ['critical', 'high'] else 'normal'
            }
            
            headers = {
                'Authorization': f'key={self.fcm_server_key}',
                'Content-Type': 'application/json'
            }
            
            try:
                response = requests.post(self.fcm_url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                result = response.json()
                total_sent += result.get('success', 0)
            except Exception as e:
                print(f"Error sending batch notifications: {e}")
        
        return total_sent

