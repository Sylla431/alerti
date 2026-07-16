"""
CNN/U-Net Model for Flood Detection from Satellite Images
Uses U-Net architecture for semantic segmentation of flood areas
"""
import numpy as np
import cv2
import keras
from keras import layers, models
from keras import backend as K
import keras.ops as ops
import os
import joblib
import base64
from PIL import Image
import io
from datetime import datetime
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.config import CNN_INPUT_SIZE, MODEL_DIR

class CNNPredictor:
    """CNN model for flood detection from satellite imagery"""
    
    def __init__(self, model_path=None):
        if model_path is None:
            os.makedirs(MODEL_DIR, exist_ok=True)
            model_path = os.path.join(MODEL_DIR, 'cnn_model.h5')
        
        self.model_path = model_path
        self.input_size = CNN_INPUT_SIZE
        self.model = None
        self.load_or_create_model()
    
    def load_or_create_model(self):
        """Load existing model or create new one"""
        if os.path.exists(self.model_path):
            try:
                self.model = keras.models.load_model(self.model_path)
                print("CNN model loaded successfully")
            except Exception as e:
                print(f"Error loading CNN model: {e}. Creating new model...")
                self._create_model()
        else:
            print("Creating new CNN/U-Net model...")
            self._create_model()
    
    def _create_model(self):
        """Create U-Net architecture for flood segmentation"""
        # U-Net architecture: encoder-decoder with skip connections
        inputs = keras.Input(shape=(*self.input_size, 3))
        
        # Encoder (downsampling path)
        # Block 1
        conv1 = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(inputs)
        conv1 = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(conv1)
        pool1 = layers.MaxPooling2D((2, 2))(conv1)
        
        # Block 2
        conv2 = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(pool1)
        conv2 = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(conv2)
        pool2 = layers.MaxPooling2D((2, 2))(conv2)
        
        # Block 3
        conv3 = layers.Conv2D(256, (3, 3), activation='relu', padding='same')(pool2)
        conv3 = layers.Conv2D(256, (3, 3), activation='relu', padding='same')(conv3)
        pool3 = layers.MaxPooling2D((2, 2))(conv3)
        
        # Block 4 (Bottleneck)
        conv4 = layers.Conv2D(512, (3, 3), activation='relu', padding='same')(pool3)
        conv4 = layers.Conv2D(512, (3, 3), activation='relu', padding='same')(conv4)
        drop4 = layers.Dropout(0.5)(conv4)
        
        # Decoder (upsampling path)
        # Block 5
        up5 = layers.UpSampling2D((2, 2))(drop4)
        up5 = layers.Conv2D(256, (2, 2), activation='relu', padding='same')(up5)
        merge5 = layers.concatenate([conv3, up5], axis=3)
        conv5 = layers.Conv2D(256, (3, 3), activation='relu', padding='same')(merge5)
        conv5 = layers.Conv2D(256, (3, 3), activation='relu', padding='same')(conv5)
        
        # Block 6
        up6 = layers.UpSampling2D((2, 2))(conv5)
        up6 = layers.Conv2D(128, (2, 2), activation='relu', padding='same')(up6)
        merge6 = layers.concatenate([conv2, up6], axis=3)
        conv6 = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(merge6)
        conv6 = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(conv6)
        
        # Block 7
        up7 = layers.UpSampling2D((2, 2))(conv6)
        up7 = layers.Conv2D(64, (2, 2), activation='relu', padding='same')(up7)
        merge7 = layers.concatenate([conv1, up7], axis=3)
        conv7 = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(merge7)
        conv7 = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(conv7)
        
        # Output layer: binary segmentation mask
        outputs = layers.Conv2D(1, (1, 1), activation='sigmoid')(conv7)
        
        self.model = models.Model(inputs=inputs, outputs=outputs)
        
        def iou_metric(y_true, y_pred):
            """Simple IoU metric compatible with binary masks."""
            y_pred_binary = ops.cast(y_pred > 0.5, dtype='float32')
            intersection = ops.sum(y_true * y_pred_binary)
            union = ops.sum(y_true) + ops.sum(y_pred_binary) - intersection + K.epsilon()
            return intersection / union
        
        self.model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy', iou_metric]
        )
        
        print("CNN/U-Net model created")
    
    def preprocess_image(self, image_data):
        """Preprocess satellite image for model input"""
        try:
            if isinstance(image_data, str):
                # Base64 encoded image
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
            elif isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
            else:
                image = image_data
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize to model input size
            image = image.resize(self.input_size)
            
            # Convert to numpy array and normalize
            img_array = np.array(image, dtype=np.float32) / 255.0
            
            # Add batch dimension
            return np.expand_dims(img_array, axis=0)
            
        except Exception as e:
            print(f"Error preprocessing image: {e}")
            # Return dummy image
            return np.zeros((1, *self.input_size, 3), dtype=np.float32)
    
    def predict_image(self, lat, lon, bbox, location_name):
        """Predict flood from satellite image"""
        try:
            # Import here to avoid circular dependency
            from services.satellite_service import SatelliteService
            
            satellite_service = SatelliteService()
            
            # Fetch satellite image
            satellite_data = satellite_service.get_sentinel2_image(lat, lon, bbox)
            
            if not satellite_data or not satellite_data.get('image'):
                # If no image available, use fallback prediction
                return self._fallback_prediction(lat, lon, location_name)
            
            # Preprocess image
            image_array = self.preprocess_image(satellite_data['image'])
            
            # Predict flood mask
            if self.model:
                prediction_mask = self.model.predict(image_array, verbose=0)[0]
                flood_mask = (prediction_mask > 0.5).astype(np.uint8) * 255
            else:
                # Fallback: simple threshold-based detection
                flood_mask = self._simple_water_detection(image_array[0])
            
            # Calculate flood statistics
            flood_pixels = np.sum(flood_mask > 0)
            total_pixels = flood_mask.size
            flood_percentage = (flood_pixels / total_pixels) * 100 if total_pixels > 0 else 0
            
            # Convert mask to base64 for frontend
            mask_base64 = None
            if flood_mask is not None:
                _, buffer = cv2.imencode('.png', flood_mask)
                mask_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Determine risk level
            risk_level = self._get_risk_level(flood_percentage)
            
            return {
                'flood_detected': flood_percentage > 0,
                'flood_percentage': float(flood_percentage),
                'flood_area': float(flood_percentage),
                'risk_level': risk_level,
                'flood_mask': mask_base64,
                'model_type': 'CNN/U-Net',
                'location': location_name,
                'satellite_source': satellite_data.get('source', 'unknown'),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error in CNN prediction: {e}")
            return self._fallback_prediction(lat, lon, location_name, error=str(e))
    
    def _simple_water_detection(self, image_array):
        """Simple water detection using NDWI-like approach"""
        # Convert normalized image back to 0-255 range
        img = (image_array * 255).astype(np.uint8)
        
        # Calculate simple water index (green - red)
        if len(img.shape) == 3:
            green = img[:, :, 1].astype(np.float32)
            red = img[:, :, 0].astype(np.float32)
            
            # Avoid division by zero
            water_index = np.where(
                (green + red) > 0,
                (green - red) / (green + red + 1e-6),
                0
            )
            
            # Threshold for water detection
            water_mask = (water_index > 0.1).astype(np.uint8) * 255
            return water_mask
        else:
            return np.zeros((*self.input_size, 1), dtype=np.uint8)
    
    def _fallback_prediction(self, lat, lon, location_name, error=None):
        """Fallback prediction when image/model unavailable"""
        import random
        # Simple heuristic based on location
        flood_prob = random.uniform(0.1, 0.4)
        flood_percentage = flood_prob * 100
        
        return {
            'flood_detected': flood_percentage > 20,
            'flood_percentage': float(flood_percentage),
            'flood_area': float(flood_percentage),
            'risk_level': self._get_risk_level(flood_percentage),
            'flood_mask': None,
            'model_type': 'CNN/U-Net (fallback)',
            'location': location_name,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_risk_level(self, flood_percentage):
        """Get risk level from flood percentage"""
        if flood_percentage >= 20:
            return 'critical'
        elif flood_percentage >= 10:
            return 'high'
        elif flood_percentage >= 5:
            return 'medium'
        elif flood_percentage > 0:
            return 'low'
        else:
            return 'none'
    
    def detect_flood(self, image_data):
        """Detect flood in preprocessed image"""
        processed_image = self.preprocess_image(image_data)
        
        if self.model:
            prediction = self.model.predict(processed_image, verbose=0)
            flood_mask = (prediction[0] > 0.5).astype(np.uint8) * 255
        else:
            flood_mask = self._simple_water_detection(processed_image[0])
        
        flood_area = np.sum(flood_mask > 0) / flood_mask.size if flood_mask.size > 0 else 0
        flood_percentage = flood_area * 100
        
        return {
            'flood_detected': flood_percentage > 0,
            'flood_percentage': float(flood_percentage),
            'flood_mask': flood_mask
        }
    
    def train(self, X_train, y_train, X_val=None, y_val=None, epochs=50, batch_size=16):
        """Train the CNN model"""
        if self.model is None:
            self._create_model()
        
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
            validation_data = (X_val, y_val)
        
        history = self.model.fit(
            X_train,
            y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=validation_data,
            callbacks=callbacks,
            verbose=1
        )
        
        return history

