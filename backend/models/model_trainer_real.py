"""
Model Training Script - Version avec Vraies Données
Entraîne les modèles avec les données réelles préparées
"""
import numpy as np
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.lstm_model import LSTMPredictor
from models.cnn_model import CNNPredictor
from models.hybrid_model import HybridFloodPredictor


def load_real_data():
    """Charge les données réelles préparées"""
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data', 'training', 'lstm'
    )
    
    print("📂 Chargement des données réelles...")
    
    # Vérifier que les fichiers existent
    required_files = ['X_train.npy', 'y_train.npy', 'X_val.npy', 'y_val.npy']
    for filename in required_files:
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Fichier manquant : {filepath}")
    
    # Charger train
    X_train = np.load(os.path.join(data_dir, 'X_train.npy'))
    y_train = np.load(os.path.join(data_dir, 'y_train.npy'))
    
    # Charger validation
    X_val = np.load(os.path.join(data_dir, 'X_val.npy'))
    y_val = np.load(os.path.join(data_dir, 'y_val.npy'))
    
    print(f"  ✅ Train : {X_train.shape[0]} séquences")
    print(f"     Shape : {X_train.shape}")
    print(f"     Positifs (inondation) : {sum(y_train > 0.3)} ({sum(y_train > 0.3)/len(y_train)*100:.1f}%)")
    
    print(f"  ✅ Validation : {X_val.shape[0]} séquences")
    print(f"     Shape : {X_val.shape}")
    print(f"     Positifs (inondation) : {sum(y_val > 0.3)} ({sum(y_val > 0.3)/len(y_val)*100:.1f}%)")
    
    return X_train, y_train, X_val, y_val


def train_lstm_with_real_data():
    """Entraîne le modèle LSTM avec les données réelles"""
    print("\n" + "="*60)
    print("🧠 ENTRAÎNEMENT DU MODÈLE LSTM")
    print("="*60)
    
    # Charger les données
    X_train, y_train, X_val, y_val = load_real_data()
    
    # Créer le modèle
    print("\n🔧 Création du modèle LSTM...")
    lstm_model = LSTMPredictor()
    
    # Entraîner
    print("\n🚀 Démarrage de l'entraînement...")
    print("   Cela peut prendre 20-30 minutes...")
    
    history = lstm_model.train(
        X_train, y_train,
        X_val, y_val,
        epochs=100,  # Plus d'époques pour vraies données
        batch_size=32
    )
    
    print("\n✅ Entraînement LSTM terminé !")
    
    # Afficher les résultats
    final_loss = history.history['loss'][-1]
    final_val_loss = history.history['val_loss'][-1]
    final_mae = history.history['mae'][-1]
    final_val_mae = history.history['val_mae'][-1]
    
    print(f"\n📊 Résultats finaux :")
    print(f"   Loss (train) : {final_loss:.4f}")
    print(f"   Loss (val) : {final_val_loss:.4f}")
    print(f"   MAE (train) : {final_mae:.4f}")
    print(f"   MAE (val) : {final_val_mae:.4f}")
    
    # Vérifier le surapprentissage
    if final_val_loss > final_loss * 1.5:
        print("\n⚠️  Avertissement : Possible surapprentissage (overfitting)")
        print("   Suggestions :")
        print("   - Ajouter plus de données d'entraînement")
        print("   - Augmenter le dropout")
        print("   - Réduire la complexité du modèle")
    else:
        print("\n✅ Le modèle généralise bien !")
    
    return lstm_model, history


def evaluate_model(X_val, y_val, lstm_model):
    """Évalue le modèle sur des métriques supplémentaires"""
    print("\n" + "="*60)
    print("📊 ÉVALUATION DU MODÈLE")
    print("="*60)
    
    # Faire des prédictions
    y_pred = lstm_model.model.predict(X_val, verbose=0).flatten()
    
    # Calculer les métriques
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    
    mae = mean_absolute_error(y_val, y_pred)
    mse = mean_squared_error(y_val, y_pred)
    rmse = np.sqrt(mse)
    
    print(f"\n📈 Métriques de régression :")
    print(f"   MAE : {mae:.4f}")
    print(f"   MSE : {mse:.4f}")
    print(f"   RMSE : {rmse:.4f}")
    
    # Métriques de classification (seuil à 0.5)
    threshold = 0.5
    y_pred_binary = (y_pred > threshold).astype(int)
    y_val_binary = (y_val > threshold).astype(int)
    
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    
    accuracy = accuracy_score(y_val_binary, y_pred_binary)
    precision = precision_score(y_val_binary, y_pred_binary, zero_division=0)
    recall = recall_score(y_val_binary, y_pred_binary, zero_division=0)
    f1 = f1_score(y_val_binary, y_pred_binary, zero_division=0)
    
    print(f"\n🎯 Métriques de classification (seuil={threshold}) :")
    print(f"   Accuracy : {accuracy:.4f} ({accuracy*100:.1f}%)")
    print(f"   Precision : {precision:.4f}")
    print(f"   Recall : {recall:.4f}")
    print(f"   F1-Score : {f1:.4f}")
    
    # Matrice de confusion
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_val_binary, y_pred_binary)
    
    print(f"\n📊 Matrice de confusion :")
    print(f"   True Negatives  : {cm[0,0]}")
    print(f"   False Positives : {cm[0,1]}")
    print(f"   False Negatives : {cm[1,0]}")
    print(f"   True Positives  : {cm[1,1]}")
    
    # Interpréter les résultats
    print(f"\n💡 Interprétation :")
    if recall < 0.5:
        print("   ⚠️  Recall faible : le modèle manque beaucoup d'inondations")
        print("      → Ajoutez plus d'exemples d'inondations dans les données")
    if precision < 0.5:
        print("   ⚠️  Precision faible : beaucoup de fausses alertes")
        print("      → Améliorez la qualité des données et des features")
    if f1 > 0.7:
        print("   ✅ Bon équilibre entre precision et recall !")


def main():
    """Fonction principale"""
    print("="*60)
    print("🎓 ENTRAÎNEMENT AVEC DONNÉES RÉELLES")
    print("="*60)
    print("\n📝 Ce script entraîne les modèles avec les données CHIRPS")
    print("   préparées dans backend/data/training/")
    
    try:
        # Entraîner LSTM
        lstm_model, history = train_lstm_with_real_data()
        
        # Charger à nouveau les données de validation pour l'évaluation
        _, _, X_val, y_val = load_real_data()
        
        # Évaluer
        evaluate_model(X_val, y_val, lstm_model)
        
        print("\n" + "="*60)
        print("✅ ENTRAÎNEMENT TERMINÉ !")
        print("="*60)
        
        print("\n📝 Modèle sauvegardé dans :")
        print(f"   {lstm_model.model_path}")
        print(f"   {lstm_model.scaler_path}")
        
        print("\n📝 Prochaines étapes :")
        print("   1. Testez les prédictions : python app.py")
        print("   2. Testez l'API : curl http://localhost:5000/api/locations")
        print("   3. Améliorez en ajoutant plus de données historiques")
        
        print("\n💡 Pour améliorer le modèle :")
        print("   - Ajoutez plus d'années de données CHIRPS")
        print("   - Remplacez les features synthétiques par vraies données (ERA5)")
        print("   - Ajoutez des labels d'inondations plus précis")
        print("   - Expérimentez avec différents hyperparamètres")
        
    except FileNotFoundError as e:
        print(f"\n❌ Erreur : Données manquantes")
        print(f"   {e}")
        print("\n📝 Lancez d'abord :")
        print("   1. cd backend/data")
        print("   2. python download_chirps.py")
        print("   3. python prepare_training_data.py")
        print("   4. cd ..")
        print("   5. python -m models.model_trainer_real")
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

