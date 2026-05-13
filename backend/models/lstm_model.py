"""
LSTM Model for Flood Prediction using Time Series Data
Predicts floods based on meteorological time series (precipitation, etc.)
"""
import numpy as np
import pandas as pd
import os
import joblib
from datetime import datetime, timedelta
import keras
from keras import layers, models
from sklearn.preprocessing import MinMaxScaler
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.config import LSTM_SEQUENCE_LENGTH, LSTM_FORECAST_DAYS, MODEL_DIR

class LSTMPredictor:
    """LSTM model for time series flood prediction"""
    
    def __init__(self, model_path=None):
        if model_path is None:
            os.makedirs(MODEL_DIR, exist_ok=True)
            model_path = os.path.join(MODEL_DIR, 'lstm_model.h5')
        
        self.model_path = model_path
        self.scaler_path = os.path.join(MODEL_DIR, 'lstm_scaler.pkl')
        self.scaler = MinMaxScaler()
        self.model = None
        self.sequence_length = LSTM_SEQUENCE_LENGTH
        self.forecast_days = LSTM_FORECAST_DAYS
        # Features étendues pour prédiction d'inondations urbaines
        self.feature_names = [
            # Météo (temporelles)
            'precipitation', 'temperature', 'humidity', 'pressure', 'soil_moisture',
            'antecedent_precip_3d', 'antecedent_precip_7d', 'antecedent_precip_14d',
            'soil_saturation_index',
            # Topographie (statiques)
            'elevation', 'slope', 'distance_to_river', 'in_flood_plain', 'depression_depth',
            # Infrastructure drainage (statiques)
            'drainage_density', 'drainage_state', 'drainage_coverage', 'blocked_drainage_pct',
            # Urbanisation (statiques)
            'impermeable_surface', 'building_density', 'population_density',
            # Hydrologie (statiques)
            'groundwater_level', 'runoff_coefficient', 'infiltration_rate', 'soil_permeability',
            # Végétation (statiques)
            'vegetation_cover', 'ndvi_avg',
            # Vulnérabilité (statiques)
            'informal_settlement_pct', 'poverty_index', 'flood_preparedness'
        ]
        self.load_or_create_model()
    
    def load_or_create_model(self):
        """Load existing model or create new one"""
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            try:
                self.model = keras.models.load_model(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                self._compile_model()
                print("LSTM model loaded successfully")
            except Exception as e:
                print(f"Error loading LSTM model: {e}. Creating new model...")
                self._create_model()
        else:
            print("Creating new LSTM model...")
            self._create_model()
    
    def _create_model(self):
        """Create bidirectional LSTM model architecture"""
        # Input: sequence of features over time
        # Output: flood probability for next N days
        input_shape = (self.sequence_length, len(self.feature_names))
        
        inputs = keras.Input(shape=input_shape)
        
        # Bidirectional LSTM layers
        lstm1 = layers.Bidirectional(
            layers.LSTM(64, return_sequences=True, dropout=0.2)
        )(inputs)
        
        lstm2 = layers.Bidirectional(
            layers.LSTM(32, return_sequences=False, dropout=0.2)
        )(lstm1)
        
        # Attention mechanism (simple implementation)
        attention = layers.Dense(32, activation='tanh')(lstm2)
        attention = layers.Dense(1, activation='softmax')(attention)
        
        # Dense layers for prediction
        dense1 = layers.Dense(64, activation='relu')(lstm2)
        dropout = layers.Dropout(0.3)(dense1)
        dense2 = layers.Dense(32, activation='relu')(dropout)
        
        # Output: single flood probability value
        outputs = layers.Dense(1, activation='sigmoid')(dense2)
        
        self.model = models.Model(inputs=inputs, outputs=outputs)
        self._compile_model()
        
        print("LSTM model created")
    
    def _compile_model(self):
        """Compile model with default optimizer/loss/metrics."""
        self.model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy', 'mae']
        )
    
    def prepare_time_series(self, meteo_data):
        """Prepare time series data from meteorological service"""
        # Extract daily precipitation data
        daily_data = meteo_data.get('chirps', {}).get('daily_data', [])
        
        if not daily_data:
            # Generate synthetic data for prediction
            return self._generate_synthetic_sequence()
        
        # Convert to DataFrame
        df = pd.DataFrame(daily_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Create feature matrix
        sequences = []
        for i in range(len(df) - self.sequence_length + 1):
            seq = df.iloc[i:i + self.sequence_length]['precipitation'].values
            
            # Pad with synthetic features (in production, use real data)
            features = []
            for precip in seq:
                features.append([
                    precip,  # precipitation
                    25.0,    # temperature (simulated)
                    65.0,    # humidity (simulated)
                    1013.0,  # pressure (simulated)
                    0.5      # soil_moisture (simulated)
                ])
            
            sequences.append(features)
        
        if sequences:
            return np.array(sequences[-1])  # Use most recent sequence
        else:
            return self._generate_synthetic_sequence()
    
    def _generate_synthetic_sequence(self):
        """Generate synthetic sequence when data unavailable"""
        # Generate realistic sequence for Africa
        np.random.seed(int(datetime.now().timestamp()))
        sequence = []
        
        for _ in range(self.sequence_length):
            # Simulate precipitation with some variability
            precip = max(0, np.random.exponential(2.0))
            temp = np.random.normal(25, 3)
            humidity = np.random.uniform(50, 80)
            pressure = np.random.normal(1013, 5)
            soil_moisture = np.random.uniform(0.3, 0.7)
            
            sequence.append([precip, temp, humidity, pressure, soil_moisture])
        
        return np.array(sequence)
    
    def predict(self, lat, lon, location_name, forecast_data=None):
        """
        Predict flood probability for location
        Args:
            lat: Latitude
            lon: Longitude
            location_name: Name of location
            forecast_data: Optional forecast data from WeatherForecastService
        """
        try:
            # Import here to avoid circular dependency
            from services.africa_data_service import AfricaDataService
            from services.weather_forecast_service import WeatherForecastService
            
            data_service = AfricaDataService()
            
            # Get historical meteorological data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.sequence_length)
            meteo_data = data_service.get_comprehensive_meteo_data(lat, lon, days_back=self.sequence_length)
            
            # Get forecast data if not provided
            if forecast_data is None:
                forecast_service = WeatherForecastService()
                forecast_data = forecast_service.get_forecast_for_lstm(lat, lon, days=self.forecast_days)
            
            # Prepare time series with historical data
            sequence = self.prepare_time_series(meteo_data)
            
            # Enhance sequence with forecast data if available
            if forecast_data and len(forecast_data) > 0:
                # Combine historical and forecast data for better prediction
                # Use forecast data to extend the sequence
                for forecast_day in forecast_data[:min(7, len(forecast_data))]:
                    forecast_features = [
                        forecast_day.get('precipitation', 0),
                        forecast_day.get('temperature', 25),
                        forecast_day.get('humidity', 60),
                        forecast_day.get('pressure', 1013),
                        0.5  # Estimated soil moisture (could be improved)
                    ]
                    # Append forecast to sequence (sliding window approach)
                    sequence = np.append(sequence[1:], [forecast_features], axis=0)
            
            # Normalize
            sequence_reshaped = sequence.reshape(1, self.sequence_length, len(self.feature_names))
            sequence_scaled = self.scaler.fit_transform(
                sequence_reshaped.reshape(-1, len(self.feature_names))
            ).reshape(1, self.sequence_length, len(self.feature_names))
            
            # Predict
            if self.model:
                prediction = self.model.predict(sequence_scaled, verbose=0)[0][0]
            else:
                # Fallback if model not loaded
                total_precip = sum(seq[0] for seq in sequence)
                prediction = min(1.0, total_precip / 100)  # Simple heuristic
            
            # Determine risk level
            risk_level = self._get_risk_level(prediction)
            
            return {
                'flood_probability': float(prediction),
                'risk_level': risk_level,
                'forecast_days': self.forecast_days,
                'model_type': 'LSTM',
                'location': location_name,
                'timestamp': datetime.now().isoformat(),
                'features_used': self.feature_names
            }
            
        except Exception as e:
            print(f"Error in LSTM prediction: {e}")
            # Return default prediction
            return {
                'flood_probability': 0.3,
                'risk_level': 'low',
                'forecast_days': self.forecast_days,
                'model_type': 'LSTM',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
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
    
    def train(self, X_train, y_train, X_val=None, y_val=None, epochs=50, batch_size=32):
        """Train the LSTM model"""
        if self.model is None:
            self._create_model()
        
        # Fit scaler on training data
        X_train_reshaped = X_train.reshape(-1, X_train.shape[-1])
        self.scaler.fit(X_train_reshaped)
        
        # Scale data
        X_train_scaled = self.scaler.transform(X_train_reshaped).reshape(X_train.shape)
        
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_loss' if X_val is not None else 'loss',
                patience=10,
                restore_best_weights=True
            ),
            keras.callbacks.ModelCheckpoint(
                self.model_path,
                save_best_only=True,
                monitor='val_loss' if X_val is not None else 'loss'
            )
        ]
        
        validation_data = None
        if X_val is not None:
            X_val_reshaped = X_val.reshape(-1, X_val.shape[-1])
            X_val_scaled = self.scaler.transform(X_val_reshaped).reshape(X_val.shape)
            validation_data = (X_val_scaled, y_val)
        
        history = self.model.fit(
            X_train_scaled,
            y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=validation_data,
            callbacks=callbacks,
            verbose=1
        )
        
        # Save scaler
        joblib.dump(self.scaler, self.scaler_path)
        
        return history

