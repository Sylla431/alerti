"""
Notification Service - Sends flood alert notifications via email/SMS
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from collections import defaultdict
from utils.config import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER,
    TWILIO_WHATSAPP_NUMBER, EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD
)

class NotificationService:
    """Service for sending flood alert notifications"""
    
    def __init__(self):
        self.twilio_account_sid = TWILIO_ACCOUNT_SID
        self.twilio_auth_token = TWILIO_AUTH_TOKEN
        self.twilio_phone = TWILIO_PHONE_NUMBER
        self.twilio_whatsapp_number = TWILIO_WHATSAPP_NUMBER
        self.email_host = EMAIL_HOST
        self.email_port = EMAIL_PORT
        self.email_user = EMAIL_USER
        self.email_password = EMAIL_PASSWORD
        
        # Store subscriptions
        self.subscriptions = defaultdict(list)  # {location: [subscriptions]}
    
    def subscribe(self, email=None, phone=None, location=None, country=None):
        """Subscribe to alerts for a location"""
        subscription = {
            'id': len(self.subscriptions) + 1,
            'email': email,
            'phone': phone,
            'location': location,
            'country': country,
            'created_at': datetime.now().isoformat()
        }
        
        key = location or country or 'all'
        self.subscriptions[key].append(subscription)
        
        return subscription
    
    def send_alert_notifications(self, alert):
        """Send notifications for an alert"""
        if not alert:
            return
        
        location = alert.get('location', '')
        alert_level = alert.get('alert_level', 'low')
        
        # Only send notifications for high-level alerts
        if alert_level not in ['high', 'critical']:
            return
        
        # Get subscribers for this location
        subscribers = self.subscriptions.get(location, [])
        subscribers += self.subscriptions.get('all', [])
        
        for subscriber in subscribers:
            if subscriber.get('email'):
                self.send_email_alert(subscriber['email'], alert)
            
            if subscriber.get('phone'):
                # Check if subscriber wants WhatsApp
                if subscriber.get('whatsapp', False):
                    self.send_whatsapp_alert(subscriber['phone'], alert)
                    # Also send voice message for critical alerts
                    if alert_level == 'critical':
                        self.send_whatsapp_voice_alert(subscriber['phone'], alert)
                else:
                    self.send_sms_alert(subscriber['phone'], alert)
    
    def send_email_alert(self, email, alert):
        """Send email alert"""
        try:
            if not self.email_user or not self.email_password:
                print(f"Email not configured. Would send to {email}")
                return
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🚨 Alerte Inondation - {alert['alert_level'].upper()}: {alert['location']}"
            msg['From'] = self.email_user
            msg['To'] = email
            
            # Create email body
            alert_level_fr = {
                'critical': 'CRITIQUE',
                'high': 'ÉLEVÉ',
                'medium': 'MOYEN',
                'low': 'FAIBLE'
            }
            
            recommendations_text = '\n'.join([f"- {rec}" for rec in alert.get('recommendations', [])])
            
            text = f"""
Alerte d'Inondation

Niveau: {alert_level_fr.get(alert['alert_level'], alert['alert_level'])}
Localisation: {alert['location']}
Probabilité: {alert['flood_probability']*100:.1f}%
Date: {alert['timestamp']}

Recommandations:
{recommendations_text}

Restez en sécurité!
Système de Prédiction d'Inondations pour l'Afrique
"""
            
            html = f"""
<html>
<body>
<h2>🚨 Alerte d'Inondation</h2>
<p><strong>Niveau:</strong> {alert_level_fr.get(alert['alert_level'], alert['alert_level'])}</p>
<p><strong>Localisation:</strong> {alert['location']}</p>
<p><strong>Probabilité:</strong> {alert['flood_probability']*100:.1f}%</p>
<p><strong>Date:</strong> {alert['timestamp']}</p>
<h3>Recommandations:</h3>
<ul>
{''.join([f'<li>{rec}</li>' for rec in alert.get('recommendations', [])])}
</ul>
<p>Restez en sécurité!</p>
<p><em>Système de Prédiction d'Inondations pour l'Afrique</em></p>
</body>
</html>
"""
            
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            server = smtplib.SMTP(self.email_host, self.email_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.sendmail(self.email_user, email, msg.as_string())
            server.quit()
            
            print(f"Email alert sent to {email}")
            
        except Exception as e:
            print(f"Error sending email alert: {e}")
    
    def send_sms_alert(self, phone, alert):
        """Send SMS alert via Twilio"""
        try:
            if not self.twilio_account_sid or not self.twilio_auth_token:
                print(f"SMS not configured. Would send to {phone}")
                return
            
            from twilio.rest import Client
            
            client = Client(self.twilio_account_sid, self.twilio_auth_token)
            
            alert_level_fr = {
                'critical': 'CRITIQUE',
                'high': 'ÉLEVÉ',
                'medium': 'MOYEN',
                'low': 'FAIBLE'
            }
            
            message = (
                f"🚨 Alerte Inondation {alert_level_fr.get(alert['alert_level'], alert['alert_level'])}\n"
                f"Localisation: {alert['location']}\n"
                f"Probabilité: {alert['flood_probability']*100:.1f}%\n"
                f"Restez en sécurité!"
            )
            
            client.messages.create(
                body=message,
                from_=self.twilio_phone,
                to=phone
            )
            
            print(f"SMS alert sent to {phone}")
            
        except Exception as e:
            print(f"Error sending SMS alert: {e}")
    
    def send_whatsapp_alert(self, phone, alert):
        """Send WhatsApp text message alert via Twilio"""
        try:
            if not self.twilio_account_sid or not self.twilio_auth_token:
                print(f"WhatsApp not configured. Would send to {phone}")
                return
            
            if not self.twilio_whatsapp_number:
                print("Twilio WhatsApp number not configured")
                return
            
            from twilio.rest import Client
            
            client = Client(self.twilio_account_sid, self.twilio_auth_token)
            
            alert_level_fr = {
                'critical': 'CRITIQUE',
                'high': 'ÉLEVÉ',
                'medium': 'MOYEN',
                'low': 'FAIBLE'
            }
            
            message = (
                f"🚨 *Alerte Inondation {alert_level_fr.get(alert['alert_level'], alert['alert_level'])}*\n\n"
                f"📍 Localisation: {alert['location']}\n"
                f"📊 Probabilité: {alert['flood_probability']*100:.1f}%\n"
                f"⏰ Date: {alert['timestamp']}\n\n"
                f"Recommandations:\n"
            )
            
            # Add recommendations
            for rec in alert.get('recommendations', [])[:3]:  # First 3 recommendations
                message += f"• {rec}\n"
            
            message += "\nRestez en sécurité!"
            
            # Format phone number for WhatsApp (must include country code)
            whatsapp_phone = f"whatsapp:{phone}" if not phone.startswith('whatsapp:') else phone
            
            client.messages.create(
                body=message,
                from_=f"whatsapp:{self.twilio_whatsapp_number}",
                to=whatsapp_phone
            )
            
            print(f"WhatsApp alert sent to {phone}")
            
        except Exception as e:
            print(f"Error sending WhatsApp alert: {e}")
    
    def send_whatsapp_voice_alert(self, phone, alert):
        """Send WhatsApp voice message alert via Twilio Voice API"""
        try:
            if not self.twilio_account_sid or not self.twilio_auth_token:
                print(f"WhatsApp Voice not configured. Would send to {phone}")
                return
            
            from twilio.rest import Client
            from twilio.twiml.voice_response import VoiceResponse, Say
            
            client = Client(self.twilio_account_sid, self.twilio_auth_token)
            
            alert_level_fr = {
                'critical': 'CRITIQUE',
                'high': 'ÉLEVÉ',
                'medium': 'MOYEN',
                'low': 'FAIBLE'
            }
            
            # Create voice message text
            voice_text = (
                f"Alerte inondation {alert_level_fr.get(alert['alert_level'], alert['alert_level'])}. "
                f"Localisation: {alert['location']}. "
                f"Probabilité d'inondation: {alert['flood_probability']*100:.0f} pour cent. "
                f"Restez en sécurité et suivez les recommandations des autorités."
            )
            
            # For WhatsApp, we use Twilio Voice API with a TwiML URL
            # In production, you would host a TwiML endpoint that returns the voice message
            # For now, we'll use Twilio's TwiML Bins or create a call
            
            # Note: WhatsApp voice messages via Twilio require:
            # 1. A verified WhatsApp Business number
            # 2. A TwiML endpoint that returns the voice message
            # 3. Using Twilio Voice API to initiate the call
            
            # Alternative: Use Twilio's text-to-speech in a call
            # This is a simplified implementation - in production, you'd need a webhook endpoint
            
            print(f"WhatsApp voice alert would be sent to {phone}: {voice_text}")
            print("Note: WhatsApp voice requires Twilio Voice API setup with TwiML endpoint")
            
            # Example implementation (requires TwiML endpoint):
            # call = client.calls.create(
            #     url='https://your-server.com/twiml/voice-alert',  # TwiML endpoint
            #     to=f"whatsapp:{phone}",
            #     from_=f"whatsapp:{self.twilio_whatsapp_number}"
            # )
            
        except Exception as e:
            print(f"Error sending WhatsApp voice alert: {e}")

