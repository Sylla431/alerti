"""
Hybrid Flood Prediction Model
Combines LSTM (time series) and CNN (satellite image) predictions
"""
import numpy as np
import os
import sys
from datetime import datetime
import keras
from keras import layers, models
import joblib

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.lstm_model import LSTMPredictor
from models.cnn_model import CNNPredictor
from utils.config import MODEL_DIR

class HybridFloodPredictor:
    """Hybrid model combining LSTM and CNN predictions"""
    
    def __init__(self):
        # Initialize individual models
        self.lstm_predictor = LSTMPredictor()
        self.cnn_predictor = CNNPredictor()
        
        # Fusion model path
        os.makedirs(MODEL_DIR, exist_ok=True)
        self.fusion_model_path = os.path.join(MODEL_DIR, 'fusion_model.h5')
        self.fusion_model = None
        
        # Default fusion weights (learned weights can be used if fusion model exists)
        self.fusion_weights = {
            'lstm': 0.6,  # Time series data often more reliable
            'cnn': 0.4    # Satellite images provide visual confirmation
        }
        
        self.load_fusion_model()
    
    def load_fusion_model(self):
        """Load fusion model if exists"""
        if os.path.exists(self.fusion_model_path):
            try:
                self.fusion_model = keras.models.load_model(self.fusion_model_path)
                print("Fusion model loaded successfully")
            except Exception as e:
                print(f"Error loading fusion model: {e}. Using weighted average.")
        else:
            print("Using weighted average for fusion (no trained fusion model)")
    
    def predict(self, lat, lon, bbox, location_name, neighborhood=None, forecast_data=None):
        """
        Predict flood using hybrid approach
        Args:
            lat: Latitude
            lon: Longitude
            bbox: Bounding box for satellite image
            location_name: Name of location
            neighborhood: Optional neighborhood name for enhanced prediction
            forecast_data: Optional forecast data from WeatherForecastService
        """
        try:
            # Get predictions from both models
            # LSTM now uses forecast data if provided
            lstm_prediction = self.lstm_predictor.predict(lat, lon, location_name, forecast_data=forecast_data)
            cnn_prediction = self.cnn_predictor.predict_image(lat, lon, bbox, location_name)
            
            # Extract probabilities
            lstm_prob = lstm_prediction.get('flood_probability', 0)
            cnn_prob = cnn_prediction.get('flood_percentage', 0) / 100.0  # Convert percentage to probability
            
            # Normalize CNN probability (percentage-based)
            # CNN gives flood area percentage, which we convert to probability
            cnn_prob_normalized = min(1.0, cnn_prob * 2)  # Scale factor for conversion
            
            # Fusion: combine predictions
            if self.fusion_model:
                # Use learned fusion model
                combined_features = np.array([[lstm_prob, cnn_prob_normalized]])
                fused_probability = self.fusion_model.predict(combined_features, verbose=0)[0][0]
            else:
                # Weighted average fusion
                fused_probability = (
                    self.fusion_weights['lstm'] * lstm_prob +
                    self.fusion_weights['cnn'] * cnn_prob_normalized
                )
            
            # Ensure probability is in valid range
            fused_probability = max(0.0, min(1.0, fused_probability))
            
            # Determine risk level
            risk_level = self._get_risk_level(fused_probability)
            
            # Calculate confidence (agreement between models)
            agreement = 1.0 - abs(lstm_prob - cnn_prob_normalized)
            confidence = (agreement + (lstm_prob + cnn_prob_normalized) / 2) / 2
            
            return {
                'flood_probability': float(fused_probability),
                'risk_level': risk_level,
                'confidence': float(confidence),
                'model_type': 'Hybrid (LSTM + CNN)',
                'location': location_name,
                'coordinates': {'lat': lat, 'lon': lon},
                'timestamp': datetime.now().isoformat(),
                'predictions': {
                    'lstm': {
                        'probability': float(lstm_prob),
                        'risk_level': lstm_prediction.get('risk_level', 'none'),
                        'forecast_days': lstm_prediction.get('forecast_days', 7)
                    },
                    'cnn': {
                        'probability': float(cnn_prob_normalized),
                        'risk_level': cnn_prediction.get('risk_level', 'none'),
                        'flood_percentage': cnn_prediction.get('flood_percentage', 0),
                        'flood_mask': cnn_prediction.get('flood_mask')
                    }
                },
                'fusion_method': 'learned_model' if self.fusion_model else 'weighted_average'
            }
            
        except Exception as e:
            print(f"Error in hybrid prediction: {e}")
            # Fallback: use LSTM only
            try:
                lstm_prediction = self.lstm_predictor.predict(lat, lon, location_name)
                return {
                    'flood_probability': lstm_prediction.get('flood_probability', 0.3),
                    'risk_level': lstm_prediction.get('risk_level', 'low'),
                    'confidence': 0.5,
                    'model_type': 'Hybrid (LSTM fallback)',
                    'location': location_name,
                    'coordinates': {'lat': lat, 'lon': lon},
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e)
                }
            except:
                # Ultimate fallback
                return {
                    'flood_probability': 0.3,
                    'risk_level': 'low',
                    'confidence': 0.3,
                    'model_type': 'Hybrid (fallback)',
                    'location': location_name,
                    'coordinates': {'lat': lat, 'lon': lon},
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e)
                }
    
    def _get_risk_level(self, probability):
        """Get risk level from probability"""
        if probability >= 0.8:
            return 'critical'
        elif probability >= 0.6:
            return 'high'
        elif probability >= 0.4:
            return 'medium'
        elif probability >= 0.2:
            return 'low'
        else:
            return 'none'
    
    def create_fusion_model(self):
        """Create a neural network fusion model"""
        # Input: 2 features (LSTM prob, CNN prob)
        inputs = keras.Input(shape=(2,))
        
        # Dense layers for learning fusion weights
        dense1 = layers.Dense(16, activation='relu')(inputs)
        dropout1 = layers.Dropout(0.2)(dense1)
        dense2 = layers.Dense(8, activation='relu')(dropout1)
        dropout2 = layers.Dropout(0.2)(dense2)
        
        # Output: single fused probability
        outputs = layers.Dense(1, activation='sigmoid')(dropout2)
        
        self.fusion_model = models.Model(inputs=inputs, outputs=outputs)
        
        self.fusion_model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy', 'mae']
        )
        
        print("Fusion model created")
        return self.fusion_model
    
    def train_fusion_model(self, X_train, y_train, X_val=None, y_val=None, epochs=50, batch_size=32):
        """Train fusion model on combined predictions"""
        if self.fusion_model is None:
            self.create_fusion_model()
        
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_loss' if X_val is not None else 'loss',
                patience=10,
                restore_best_weights=True
            ),
            keras.callbacks.ModelCheckpoint(
                self.fusion_model_path,
                save_best_only=True,
                monitor='val_loss' if X_val is not None else 'loss'
            )
        ]
        
        validation_data = None
        if X_val is not None:
            validation_data = (X_val, y_val)
        
        history = self.fusion_model.fit(
            X_train,
            y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=validation_data,
            callbacks=callbacks,
            verbose=1
        )
        
        return history
    
    def update_fusion_weights(self, lstm_weight, cnn_weight):
        """Update manual fusion weights"""
        total = lstm_weight + cnn_weight
        if total > 0:
            self.fusion_weights['lstm'] = lstm_weight / total
            self.fusion_weights['cnn'] = cnn_weight / total
        else:
            self.fusion_weights = {'lstm': 0.5, 'cnn': 0.5}

