"""
LSTM Model for Flood Prediction - Version spécifique pour Bamako
Utilise toutes les features étendues (topographie, infrastructure, urbanisation, etc.)
"""
import numpy as np
import pandas as pd
import os
import joblib
from datetime import datetime, timedelta
import keras
from keras import layers, models
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.config import LSTM_SEQUENCE_LENGTH, LSTM_FORECAST_DAYS, MODEL_DIR


class LSTMPredictorBamako:
    """LSTM model spécifique pour prédiction d'inondations à Bamako avec features étendues"""
    
    def __init__(self, model_path=None, n_features=None):
        if model_path is None:
            os.makedirs(MODEL_DIR, exist_ok=True)
            model_path = os.path.join(MODEL_DIR, 'lstm_model_bamako.h5')
        
        self.model_path = model_path
        self.scaler_path = os.path.join(MODEL_DIR, 'lstm_scaler_bamako.pkl')
        self.scaler = MinMaxScaler()
        self.model = None
        self.sequence_length = LSTM_SEQUENCE_LENGTH
        self.forecast_days = LSTM_FORECAST_DAYS
        
        # Features étendues pour Bamako
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
        
        # Si n_features est fourni, ajuster (pour compatibilité avec données réelles)
        if n_features is not None:
            # Prendre seulement les n_features premières
            self.feature_names = self.feature_names[:n_features]
        
        self.load_or_create_model()
    
    def load_or_create_model(self):
        """Load existing model or create new one"""
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            try:
                # Try loading with compile=False first (safer for custom loss functions)
                try:
                    self.model = keras.models.load_model(self.model_path, compile=False)
                    print(f"  ✅ Modèle chargé (sans compilation)")
                except Exception as e1:
                    # If that fails, try with custom_objects for Focal Loss
                    def focal_loss(gamma=2.0, alpha=0.25):
                        def focal_loss_fixed(y_true, y_pred):
                            epsilon = tf.keras.backend.epsilon()
                            y_pred = tf.clip_by_value(y_pred, epsilon, 1 - epsilon)
                            p_t = y_true * y_pred + (1 - y_true) * (1 - y_pred)
                            alpha_factor = tf.ones_like(y_true) * alpha
                            alpha_t = y_true * alpha_factor + (1 - y_true) * (1 - alpha_factor)
                            cross_entropy = -tf.keras.backend.log(p_t)
                            weight = alpha_t * tf.pow((1 - p_t), gamma)
                            loss = weight * cross_entropy
                            return tf.reduce_mean(tf.reduce_sum(loss, axis=1))
                        return focal_loss_fixed
                    
                    custom_objects = {'focal_loss_fixed': focal_loss()}
                    self.model = keras.models.load_model(self.model_path, custom_objects=custom_objects, compile=False)
                    print(f"  ✅ Modèle chargé avec custom_objects")
                
                # Load scaler
                self.scaler = joblib.load(self.scaler_path)
                
                # Recompile with current metrics (needed after compile=False)
                self._compile_model()
                print(f"LSTM model Bamako loaded successfully ({len(self.feature_names)} features)")
            except Exception as e:
                print(f"Error loading LSTM model: {e}. Creating new model...")
                import traceback
                traceback.print_exc()
                self._create_model()
        else:
            print("Creating new LSTM model for Bamako...")
            self._create_model()
    
    def _create_model(self):
        """Create bidirectional LSTM model architecture avec features étendues"""
        # Input: sequence of features over time
        # Output: flood probability for next N days
        input_shape = (self.sequence_length, len(self.feature_names))
        
        inputs = keras.Input(shape=input_shape)
        
        # Bidirectional LSTM layers (plus grandes pour gérer plus de features)
        lstm1 = layers.Bidirectional(
            layers.LSTM(128, return_sequences=True, dropout=0.2)
        )(inputs)
        
        lstm2 = layers.Bidirectional(
            layers.LSTM(64, return_sequences=True, dropout=0.2)
        )(lstm1)
        
        lstm3 = layers.Bidirectional(
            layers.LSTM(32, return_sequences=False, dropout=0.2)
        )(lstm2)
        
        # Attention mechanism
        attention = layers.Dense(32, activation='tanh')(lstm3)
        attention = layers.Dense(1, activation='softmax')(attention)
        
        # Dense layers for prediction (plus profondes)
        dense1 = layers.Dense(128, activation='relu')(lstm3)
        dropout1 = layers.Dropout(0.3)(dense1)
        dense2 = layers.Dense(64, activation='relu')(dropout1)
        dropout2 = layers.Dropout(0.3)(dense2)
        dense3 = layers.Dense(32, activation='relu')(dropout2)
        
        # Output: single flood probability value
        outputs = layers.Dense(1, activation='sigmoid')(dense3)
        
        self.model = models.Model(inputs=inputs, outputs=outputs)
        self._compile_model()
        
        print(f"LSTM model Bamako created ({len(self.feature_names)} features, {self.model.count_params()} parameters)")
    
    def _compile_model(self, use_focal_loss=True):
        """Compile model with Focal Loss for imbalanced data."""
        if use_focal_loss:
            # Focal Loss pour gérer l'imbalance (se concentre sur les exemples difficiles)
            def focal_loss(gamma=2.0, alpha=0.25):
                def focal_loss_fixed(y_true, y_pred):
                    epsilon = tf.keras.backend.epsilon()
                    # Utiliser tf.clip_by_value au lieu de keras.backend.clip
                    y_pred = tf.clip_by_value(y_pred, epsilon, 1 - epsilon)
                    p_t = y_true * y_pred + (1 - y_true) * (1 - y_pred)
                    alpha_factor = tf.ones_like(y_true) * alpha
                    alpha_t = y_true * alpha_factor + (1 - y_true) * (1 - alpha_factor)
                    cross_entropy = -tf.keras.backend.log(p_t)
                    weight = alpha_t * tf.pow((1 - p_t), gamma)
                    loss = weight * cross_entropy
                    return tf.reduce_mean(tf.reduce_sum(loss, axis=1))
                return focal_loss_fixed
            
            loss_fn = focal_loss(gamma=2.0, alpha=0.25)
            print("  ✅ Focal Loss activé (gamma=2.0, alpha=0.25)")
        else:
            loss_fn = 'binary_crossentropy'
            print("  ⚠️  Binary Crossentropy (non recommandé pour imbalance)")
        
        # Métriques adaptées à l'imbalance (ne pas utiliser accuracy seul !)
        self.model.compile(
            optimizer='adam',
            loss=loss_fn,
            metrics=[
                'mae',
                keras.metrics.Precision(name='precision'),
                keras.metrics.Recall(name='recall'),
                keras.metrics.AUC(name='auc'),
            ]
        )
    
    def train(self, X_train, y_train, X_val=None, y_val=None, epochs=100, batch_size=32, use_class_weights=True):
        """Train the LSTM model with class weights for imbalanced data"""
        if self.model is None:
            self._create_model()
        
        # Vérifier que le nombre de features correspond
        expected_features = len(self.feature_names)
        actual_features = X_train.shape[2]
        
        if expected_features != actual_features:
            print(f"⚠️  Ajustement : {actual_features} features dans les données, {expected_features} attendues")
            # Ajuster les feature_names
            self.feature_names = [f'feature_{i}' for i in range(actual_features)]
            # Recréer le modèle avec le bon nombre de features
            self._create_model()
        
        # Calculer les class weights pour rééquilibrer l'imbalance
        class_weights = None
        if use_class_weights:
            from sklearn.utils.class_weight import compute_class_weight
            y_train_binary = (y_train > 0.3).astype(int)
            classes = np.unique(y_train_binary)
            
            if len(classes) == 2:  # Les deux classes sont présentes
                weights = compute_class_weight('balanced', classes=classes, y=y_train_binary)
                class_weights = {0: float(weights[0]), 1: float(weights[1])}
                print(f"\n⚖️  Class weights calculés : {class_weights}")
                print(f"   Ratio négatif/positif : {weights[0]:.2f}:{weights[1]:.2f}")
                print(f"   → Les erreurs sur les inondations seront pénalisées {weights[1]:.1f}x plus")
            else:
                print(f"  ⚠️  Une seule classe présente, class weights désactivés")
        
        # Fit scaler on training data
        X_train_reshaped = X_train.reshape(-1, X_train.shape[-1])
        self.scaler.fit(X_train_reshaped)
        
        # Scale data
        X_train_scaled = self.scaler.transform(X_train_reshaped).reshape(X_train.shape)
        
        # Callbacks avec monitoring adapté à l'imbalance
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_auc' if X_val is not None else 'auc',  # AUC meilleur que loss pour imbalance
                patience=20,
                restore_best_weights=True,
                mode='max'
            ),
            keras.callbacks.ModelCheckpoint(
                self.model_path,
                save_best_only=True,
                monitor='val_auc' if X_val is not None else 'auc',  # Sauvegarder le meilleur AUC
                mode='max'
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss' if X_val is not None else 'loss',
                factor=0.5,
                patience=7,
                min_lr=1e-7
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
            validation_data=validation_data,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            class_weight=class_weights,  # ← AJOUTER ICI pour rééquilibrer
            verbose=1
        )
        
        # Sauvegarder le scaler
        joblib.dump(self.scaler, self.scaler_path)
        
        return history
    
    def predict(self, X):
        """Predict flood probability"""
        if self.model is None:
            raise ValueError("Model not loaded or created")
        
        # Scale data
        X_reshaped = X.reshape(-1, X.shape[-1])
        X_scaled = self.scaler.transform(X_reshaped).reshape(X.shape)
        
        # Predict
        predictions = self.model.predict(X_scaled, verbose=0)
        
        return predictions.flatten()
    
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

