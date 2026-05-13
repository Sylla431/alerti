"""
Model Training Script
Trains LSTM, CNN, and Hybrid models using historical data
"""
import numpy as np
import os
import sys
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.lstm_model import LSTMPredictor
from models.cnn_model import CNNPredictor
from models.hybrid_model import HybridFloodPredictor

def generate_synthetic_training_data_lstm(n_samples=1000, sequence_length=30):
    """Generate synthetic training data for LSTM"""
    print(f"Generating {n_samples} synthetic LSTM training samples...")
    
    np.random.seed(42)
    X_train = []
    y_train = []
    
    for _ in range(n_samples):
        # Generate sequence
        sequence = []
        total_precip = 0
        
        for _ in range(sequence_length):
            # Simulate realistic precipitation pattern
            precip = max(0, np.random.exponential(2.0))
            temp = np.random.normal(25, 3)
            humidity = np.random.uniform(50, 80)
            pressure = np.random.normal(1013, 5)
            soil_moisture = np.random.uniform(0.3, 0.7)
            
            sequence.append([precip, temp, humidity, pressure, soil_moisture])
            total_precip += precip
        
        X_train.append(sequence)
        
        # Generate target: flood probability based on conditions
        flood_prob = min(1.0, (
            (total_precip > 60) * 0.3 +
            (total_precip > 80) * 0.3 +
            (sequence[-1][4] > 0.7) * 0.2 +  # High soil moisture
            np.random.normal(0, 0.1)
        ))
        y_train.append(flood_prob)
    
    return np.array(X_train), np.array(y_train)

def generate_synthetic_training_data_cnn(n_samples=500, img_size=(256, 256)):
    """Generate synthetic training data for CNN"""
    print(f"Generating {n_samples} synthetic CNN training samples...")
    
    np.random.seed(42)
    X_train = []
    y_train = []
    
    for _ in range(n_samples):
        # Generate random image (3 channels RGB)
        image = np.random.rand(*img_size, 3).astype(np.float32)
        
        # Simulate water areas (darker blue regions)
        if np.random.random() > 0.5:  # 50% chance of flood
            # Create flood regions
            n_floods = np.random.randint(1, 5)
            for _ in range(n_floods):
                center_x = np.random.randint(50, img_size[0] - 50)
                center_y = np.random.randint(50, img_size[1] - 50)
                radius = np.random.randint(20, 80)
                
                y_coords, x_coords = np.ogrid[:img_size[0], :img_size[1]]
                mask = (x_coords - center_x)**2 + (y_coords - center_y)**2 <= radius**2
                
                # Make water regions blue and darker
                image[mask, 0] *= 0.5  # Less red
                image[mask, 1] *= 0.7  # Less green
                image[mask, 2] = np.minimum(1.0, image[mask, 2] * 1.2)  # More blue
        
        X_train.append(image)
        
        # Generate target mask
        # Simple threshold-based flood mask
        water_index = (image[:, :, 2] - image[:, :, 0] - image[:, :, 1]) / 3
        flood_mask = (water_index > 0.1).astype(np.float32)
        y_train.append(flood_mask)
    
    return np.array(X_train), np.array(y_train)

def train_lstm_model():
    """Train LSTM model"""
    print("\n=== Training LSTM Model ===")
    
    # Generate training data
    X_train, y_train = generate_synthetic_training_data_lstm(n_samples=1000)
    
    # Split into train/val
    split_idx = int(0.8 * len(X_train))
    X_train_split = X_train[:split_idx]
    y_train_split = y_train[:split_idx]
    X_val = X_train[split_idx:]
    y_val = y_train[split_idx:]
    
    # Initialize model
    lstm_model = LSTMPredictor()
    
    # Train
    print("Starting LSTM training...")
    history = lstm_model.train(
        X_train_split, y_train_split,
        X_val=X_val, y_val=y_val,
        epochs=50,
        batch_size=32
    )
    
    print(f"LSTM training completed. Final loss: {history.history['loss'][-1]:.4f}")
    return lstm_model

def train_cnn_model():
    """Train CNN model"""
    print("\n=== Training CNN Model ===")
    
    # Generate training data (reduced for faster synthetic training)
    X_train, y_train = generate_synthetic_training_data_cnn(n_samples=120)
    
    # Add channel dimension to masks
    y_train = np.expand_dims(y_train, axis=-1)
    
    # Split into train/val
    split_idx = int(0.8 * len(X_train))
    X_train_split = X_train[:split_idx]
    y_train_split = y_train[:split_idx]
    X_val = X_train[split_idx:]
    y_val = y_train[split_idx:]
    
    # Initialize model
    cnn_model = CNNPredictor()
    
    # Train
    print("Starting CNN training...")
    history = cnn_model.train(
        X_train_split, y_train_split,
        X_val=X_val, y_val=y_val,
        epochs=8,
        batch_size=4
    )
    
    print(f"CNN training completed. Final loss: {history.history['loss'][-1]:.4f}")
    return cnn_model

def train_hybrid_fusion_model():
    """Train fusion model for hybrid predictor"""
    print("\n=== Training Hybrid Fusion Model ===")
    
    # Generate synthetic predictions from both models
    np.random.seed(42)
    n_samples = 500
    
    X_train = []
    y_train = []
    
    for _ in range(n_samples):
        # Simulate LSTM and CNN predictions
        true_flood_prob = np.random.random()
        
        # Add some noise to simulate real predictions
        lstm_pred = np.clip(true_flood_prob + np.random.normal(0, 0.1), 0, 1)
        cnn_pred = np.clip(true_flood_prob + np.random.normal(0, 0.15), 0, 1)
        
        X_train.append([lstm_pred, cnn_pred])
        y_train.append(true_flood_prob)
    
    X_train = np.array(X_train)
    y_train = np.array(y_train)
    
    # Split
    split_idx = int(0.8 * len(X_train))
    X_train_split = X_train[:split_idx]
    y_train_split = y_train[:split_idx]
    X_val = X_train[split_idx:]
    y_val = y_train[split_idx:]
    
    # Initialize hybrid model
    hybrid_model = HybridFloodPredictor()
    
    # Train fusion model
    print("Starting fusion model training...")
    history = hybrid_model.train_fusion_model(
        X_train_split, y_train_split,
        X_val=X_val, y_val=y_val,
        epochs=50,
        batch_size=32
    )
    
    print(f"Fusion model training completed. Final loss: {history.history['loss'][-1]:.4f}")
    return hybrid_model

def main():
    """Main training function"""
    print("=" * 60)
    print("Flood Prediction Model Training")
    print("=" * 60)
    
    # Train individual models
    try:
        lstm_model = train_lstm_model()
    except Exception as e:
        print(f"Error training LSTM: {e}")
        lstm_model = None
    
    # try:
    #     cnn_model = train_cnn_model()
    # except Exception as e:
    #     print(f"Error training CNN: {e}")
    #     cnn_model = None
    
    # # Train fusion model
    # try:
    #     hybrid_model = train_hybrid_fusion_model()
    # except Exception as e:
    #     print(f"Error training fusion model: {e}")
    #     hybrid_model = None
    
    print("\n" + "=" * 60)
    print("Training Summary:")
    print(f"  - LSTM Model: {'✓ Trained' if lstm_model else '✗ Failed'}")
    # print(f"  - CNN Model: {'✓ Trained' if cnn_model else '✗ Failed'}")
    # print(f"  - Fusion Model: {'✓ Trained' if hybrid_model else '✗ Failed'}")
    print("=" * 60)

if __name__ == '__main__':
    main()

