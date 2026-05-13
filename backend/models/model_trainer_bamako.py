"""
Model Training Script - Version spécifique pour Bamako
Entraîne le modèle LSTM avec toutes les features étendues
"""
import numpy as np
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.lstm_model_bamako import LSTMPredictorBamako


def load_bamako_data():
    """Charge les données préparées pour Bamako"""
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data', 'training', 'bamako_lstm'
    )
    
    print("📂 Chargement des données d'entraînement pour Bamako...")
    
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
    print(f"     Features : {X_train.shape[2]}")
    print(f"     Positifs (inondation) : {sum(y_train > 0.3)} ({sum(y_train > 0.3)/len(y_train)*100:.1f}%)")
    
    print(f"  ✅ Validation : {X_val.shape[0]} séquences")
    print(f"     Shape : {X_val.shape}")
    print(f"     Positifs (inondation) : {sum(y_val > 0.3)} ({sum(y_val > 0.3)/len(y_val)*100:.1f}%)")
    
    return X_train, y_train, X_val, y_val


def train_bamako_model(use_smote=True, use_class_weights=True):
    """Entraîne le modèle LSTM pour Bamako avec rééquilibrage anti-imbalance"""
    print("\n" + "="*60)
    print("🧠 ENTRAÎNEMENT DU MODÈLE LSTM - BAMAKO")
    print("="*60)
    print("\n⚖️  GESTION DE L'IMBALANCE (3% positifs)")
    print("   ✅ Focal Loss activé")
    print(f"   ✅ Class Weights : {'activé' if use_class_weights else 'désactivé'}")
    print(f"   ✅ SMOTE Oversampling : {'activé' if use_smote else 'désactivé'}")
    
    # Charger les données
    X_train, y_train, X_val, y_val = load_bamako_data()
    
    # Option 1 : SMOTE pour oversampling (rééquilibrage des données)
    if use_smote:
        print("\n🔄 Rééquilibrage des données avec SMOTE...")
        print(f"   Avant : {X_train.shape[0]} séquences ({sum(y_train > 0.3)} positifs, {sum(y_train > 0.3)/len(y_train)*100:.1f}%)")
        
        try:
            from imblearn.over_sampling import SMOTE
            
            # Reshape pour SMOTE (il attend 2D)
            X_train_2d = X_train.reshape(X_train.shape[0], -1)
            y_train_binary = (y_train > 0.3).astype(int)
            
            # Vérifier qu'on a assez d'exemples positifs pour SMOTE
            n_positives = sum(y_train_binary)
            k_neighbors = min(5, n_positives - 1) if n_positives > 1 else 1
            
            if n_positives > 1:
                # Appliquer SMOTE
                smote = SMOTE(random_state=42, k_neighbors=k_neighbors)
                X_train_balanced, y_train_balanced = smote.fit_resample(X_train_2d, y_train_binary)
                
                # Reshape back
                X_train_balanced = X_train_balanced.reshape(-1, X_train.shape[1], X_train.shape[2])
                y_train_balanced = y_train_balanced.astype(np.float32)
                
                print(f"   Après : {X_train_balanced.shape[0]} séquences ({sum(y_train_balanced > 0.3)} positifs, {sum(y_train_balanced > 0.3)/len(y_train_balanced)*100:.1f}%)")
                print(f"   Ratio équilibré : {sum(y_train_balanced > 0.3) / len(y_train_balanced) * 100:.1f}% positifs")
                
                X_train = X_train_balanced
                y_train = y_train_balanced
            else:
                print("   ⚠️  Pas assez d'exemples positifs pour SMOTE, passage avec class weights uniquement")
        except ImportError:
            print("   ⚠️  imbalanced-learn non installé, SMOTE désactivé")
            print("   → Installez avec : pip install imbalanced-learn")
        except Exception as e:
            print(f"   ⚠️  Erreur SMOTE : {e}, passage avec class weights uniquement")
    
    # Créer le modèle avec le bon nombre de features
    n_features = X_train.shape[2]
    print(f"\n🔧 Création du modèle LSTM avec {n_features} features...")
    lstm_model = LSTMPredictorBamako(n_features=n_features)
    
    # Entraîner
    print("\n🚀 Démarrage de l'entraînement...")
    print("   Cela peut prendre 30-60 minutes...")
    
    history = lstm_model.train(
        X_train, y_train,
        X_val, y_val,
        epochs=150,  # Plus d'époques pour modèle complexe
        batch_size=32,
        use_class_weights=use_class_weights
    )
    
    print("\n✅ Entraînement terminé !")
    
    # Afficher les résultats
    final_loss = history.history['loss'][-1]
    final_val_loss = history.history['val_loss'][-1]
    final_mae = history.history['mae'][-1]
    final_val_mae = history.history['val_mae'][-1]
    final_accuracy = history.history.get('accuracy', [0])[-1]
    final_val_accuracy = history.history.get('val_accuracy', [0])[-1]
    
    # Récupérer les métriques adaptées à l'imbalance
    final_precision = history.history.get('precision', [0])[-1]
    final_recall = history.history.get('recall', [0])[-1]
    final_auc = history.history.get('auc', [0])[-1]
    final_val_precision = history.history.get('val_precision', [0])[-1]
    final_val_recall = history.history.get('val_recall', [0])[-1]
    final_val_auc = history.history.get('val_auc', [0])[-1]
    
    print(f"\n📊 Résultats finaux :")
    print(f"\n   🔴 MÉTRIQUES ADAPTÉES À L'IMBALANCE (à privilégier) :")
    print(f"   ROC-AUC (train) : {final_auc:.4f} (idéal > 0.8)")
    print(f"   ROC-AUC (val)   : {final_val_auc:.4f} (idéal > 0.8)")
    print(f"   Precision (train) : {final_precision:.4f}")
    print(f"   Precision (val)   : {final_val_precision:.4f}")
    print(f"   Recall (train)    : {final_recall:.4f} (idéal > 0.5)")
    print(f"   Recall (val)      : {final_val_recall:.4f} (idéal > 0.5)")
    
    # Calculer F1
    if final_precision > 0 and final_recall > 0:
        final_f1 = 2 * (final_precision * final_recall) / (final_precision + final_recall)
        final_val_f1 = 2 * (final_val_precision * final_val_recall) / (final_val_precision + final_val_recall) if final_val_precision > 0 and final_val_recall > 0 else 0
        print(f"   F1-Score (train) : {final_f1:.4f} (idéal > 0.5)")
        print(f"   F1-Score (val)   : {final_val_f1:.4f} (idéal > 0.5)")
    
    print(f"\n   ⚠️  MÉTRIQUES CLASSIQUES (trompeuses avec 3% positifs) :")
    print(f"   Loss (train) : {final_loss:.4f}")
    print(f"   Loss (val) : {final_val_loss:.4f}")
    print(f"   MAE (train) : {final_mae:.4f}")
    print(f"   MAE (val) : {final_val_mae:.4f}")
    if final_accuracy and final_val_accuracy:
        print(f"   Accuracy (train) : {final_accuracy:.4f} ({final_accuracy*100:.1f}%) ⚠️ IGNORER")
        print(f"   Accuracy (val) : {final_val_accuracy:.4f} ({final_val_accuracy*100:.1f}%) ⚠️ IGNORER")
    else:
        print("   Accuracy non suivi (métrique peu pertinente pour 3% de positifs).")
    print(f"   → Un modèle naïf qui prédit toujours 'pas d'inondation' aurait 97% d'accuracy !")
    
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
    y_pred = lstm_model.predict(X_val)
    
    # Calculer les métriques adaptées à l'imbalance
    from sklearn.metrics import (
        mean_absolute_error, mean_squared_error,
        precision_recall_curve, roc_auc_score, 
        average_precision_score, classification_report,
        precision_score, recall_score, f1_score, confusion_matrix
    )
    
    y_val_binary = (y_val > 0.3).astype(int)
    
    # ROC-AUC et PR-AUC (meilleurs pour imbalance)
    roc_auc = roc_auc_score(y_val_binary, y_pred)
    pr_auc = average_precision_score(y_val_binary, y_pred)
    
    # Métriques de classification avec seuil optimal (basé sur F1)
    threshold = 0.5
    y_pred_binary = (y_pred > threshold).astype(int)
    
    precision = precision_score(y_val_binary, y_pred_binary, zero_division=0)
    recall = recall_score(y_val_binary, y_pred_binary, zero_division=0)
    f1 = f1_score(y_val_binary, y_pred_binary, zero_division=0)
    
    # Trouver le seuil optimal basé sur F1
    precision_curve, recall_curve, thresholds_curve = precision_recall_curve(y_val_binary, y_pred)
    f1_scores = 2 * (precision_curve * recall_curve) / (precision_curve + recall_curve + 1e-10)
    optimal_idx = np.argmax(f1_scores)
    optimal_threshold = thresholds_curve[optimal_idx] if len(thresholds_curve) > 0 else 0.5
    optimal_f1 = f1_scores[optimal_idx]
    
    print(f"\n🎯 MÉTRIQUES ADAPTÉES À L'IMBALANCE (à privilégier) :")
    print(f"   ROC-AUC : {roc_auc:.4f} (idéal > 0.8, excellent si > 0.9)")
    print(f"   PR-AUC  : {pr_auc:.4f} (idéal > 0.5, excellent si > 0.7)")
    print(f"   F1-Score (seuil=0.5) : {f1:.4f}")
    print(f"   F1-Score optimal (seuil={optimal_threshold:.3f}) : {optimal_f1:.4f}")
    print(f"   Precision : {precision:.4f}")
    print(f"   Recall : {recall:.4f} (idéal > 0.5, critique pour détecter les inondations)")
    
    # Métriques classiques (moins utiles avec imbalance)
    mae = mean_absolute_error(y_val, y_pred)
    mse = mean_squared_error(y_val, y_pred)
    rmse = np.sqrt(mse)
    from sklearn.metrics import accuracy_score
    accuracy = accuracy_score(y_val_binary, y_pred_binary)
    
    print(f"\n⚠️  MÉTRIQUES CLASSIQUES (trompeuses avec 3% positifs) :")
    print(f"   MAE : {mae:.4f}")
    print(f"   MSE : {mse:.4f}")
    print(f"   RMSE : {rmse:.4f}")
    print(f"   Accuracy : {accuracy:.4f} ({accuracy*100:.1f}%) ⚠️ IGNORER")
    print(f"   → Un modèle naïf aurait 97% d'accuracy !")
    
    # Matrice de confusion
    cm = confusion_matrix(y_val_binary, y_pred_binary)
    
    print(f"\n📊 Matrice de confusion :")
    print(f"   True Negatives  : {cm[0,0]}")
    print(f"   False Positives : {cm[0,1]}")
    print(f"   False Negatives : {cm[1,0]}")
    print(f"   True Positives  : {cm[1,1]}")
    
    # Rapport de classification détaillé
    print(f"\n📋 Rapport de classification détaillé :")
    print(classification_report(y_val_binary, y_pred_binary, 
                                target_names=['Pas d\'inondation', 'Inondation'],
                                zero_division=0))
    
    # Interpréter les résultats
    print(f"\n💡 Interprétation :")
    if roc_auc < 0.7:
        print("   ⚠️  ROC-AUC faible : le modèle ne distingue pas bien les classes")
        print("      → Vérifiez les features, peut-être ajouter plus de données")
    elif roc_auc > 0.9:
        print("   ✅ ROC-AUC excellent ! Le modèle distingue très bien les classes")
    
    if recall < 0.5:
        print("   ⚠️  Recall faible : le modèle manque beaucoup d'inondations (CRITIQUE)")
        print("      → Augmentez les class weights ou utilisez SMOTE")
        print("      → Ajoutez plus d'exemples d'inondations dans les données")
    elif recall > 0.7:
        print("   ✅ Recall bon : le modèle détecte bien les inondations")
    
    if precision < 0.5:
        print("   ⚠️  Precision faible : beaucoup de fausses alertes")
        print("      → Améliorez la qualité des données et des features")
        print("      → Augmentez le seuil de prédiction")
    elif precision > 0.7:
        print("   ✅ Precision bonne : peu de fausses alertes")
    
    if f1 > 0.7:
        print("   ✅ Excellent équilibre entre precision et recall !")
    elif f1 > 0.5:
        print("   ✅ Bon équilibre entre precision et recall")
    else:
        print("   ⚠️  F1 faible : le modèle a besoin d'amélioration")
    
    # Analyse par commune (si métadonnées disponibles)
    try:
        import json
        metadata_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data', 'training', 'bamako_lstm', 'metadata_val.json'
        )
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Grouper par commune
            from collections import defaultdict
            commune_stats = defaultdict(lambda: {'total': 0, 'correct': 0, 'floods': 0, 'predicted_floods': 0})
            
            for i, meta in enumerate(metadata):
                commune = meta.get('commune', 'Unknown')
                commune_stats[commune]['total'] += 1
                if y_val_binary[i] == y_pred_binary[i]:
                    commune_stats[commune]['correct'] += 1
                if y_val_binary[i] == 1:
                    commune_stats[commune]['floods'] += 1
                if y_pred_binary[i] == 1:
                    commune_stats[commune]['predicted_floods'] += 1
            
            print(f"\n📊 Performance par commune :")
            for commune, stats in sorted(commune_stats.items()):
                accuracy_commune = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
                print(f"   {commune:15s} : {accuracy_commune:.2%} ({stats['correct']}/{stats['total']}) "
                      f"| Inondations réelles: {stats['floods']}, Prédites: {stats['predicted_floods']}")
    except Exception as e:
        print(f"   ⚠️  Impossible d'analyser par commune : {e}")


def main():
    """Fonction principale"""
    print("="*60)
    print("🎓 ENTRAÎNEMENT MODÈLE BAMAKO - FEATURES ÉTENDUES")
    print("="*60)
    print("\n📝 Ce script entraîne le modèle avec :")
    print("   ✅ Features météo (précipitations, température, etc.)")
    print("   ✅ Topographie (élévation, pente, distance au fleuve)")
    print("   ✅ Infrastructure (drainage, canalisations)")
    print("   ✅ Urbanisation (imperméabilisation, densité)")
    print("   ✅ Hydrologie (nappe, ruissellement)")
    print("   ✅ Vulnérabilité (habitat précaire, pauvreté)")
    
    try:
        # Entraîner avec rééquilibrage anti-imbalance
        lstm_model, history = train_bamako_model(use_smote=True, use_class_weights=True)
        
        # Charger à nouveau les données de validation pour l'évaluation
        _, _, X_val, y_val = load_bamako_data()
        
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
        print("   2. Testez l'API : curl http://localhost:5000/api/mali/neighborhoods")
        print("   3. Améliorez en ajoutant plus de données historiques")
        
        print("\n💡 Pour améliorer le modèle :")
        print("   - Ajoutez plus d'années de données CHIRPS")
        print("   - Remplacez les features synthétiques par vraies données")
        print("   - Ajoutez des labels d'inondations plus précis")
        print("   - Expérimentez avec différents hyperparamètres")
        
    except FileNotFoundError as e:
        print(f"\n❌ Erreur : Données manquantes")
        print(f"   {e}")
        print("\n📝 Lancez d'abord :")
        print("   1. cd backend/data")
        print("   2. python read_chirps_bamako.py")
        print("   3. python prepare_bamako_data.py")
        print("   4. cd ..")
        print("   5. python -m models.model_trainer_bamako")
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

