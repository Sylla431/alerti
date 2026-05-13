#!/usr/bin/env python3
"""
Script simplifié pour entraîner les modèles IA
Pour débutants - Lancez simplement: python train_models.py
"""
import sys
import os

# Ajouter le backend au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def main():
    print("=" * 70)
    print("🌊 ENTRAÎNEMENT DES MODÈLES IA - SYSTÈME DE PRÉDICTION D'INONDATIONS")
    print("=" * 70)
    print()
    print("Ce script va entraîner 3 modèles :")
    print("  1. LSTM (prédictions météorologiques)")
    print("  2. CNN (détection sur images satellites)")
    print("  3. Fusion (combinaison des deux)")
    print()
    print("⏱️  Temps estimé : 20-30 minutes")
    print()
    
    response = input("Voulez-vous continuer ? (o/n): ").lower()
    if response not in ['o', 'oui', 'y', 'yes']:
        print("Entraînement annulé.")
        return
    
    print()
    print("🚀 Démarrage de l'entraînement...")
    print()
    
    try:
        from backend.models.model_trainer import main as train_main
        train_main()
        
        print()
        print("=" * 70)
        print("✅ ENTRAÎNEMENT TERMINÉ AVEC SUCCÈS !")
        print("=" * 70)
        print()
        print("Les modèles ont été sauvegardés dans :")
        print("  - backend/models/lstm_model.h5")
        print("  - backend/models/cnn_model.h5")
        print("  - backend/models/fusion_model.h5")
        print()
        print("Vous pouvez maintenant utiliser l'API pour faire des prédictions !")
        print()
        
    except ImportError as e:
        print(f"❌ Erreur d'importation : {e}")
        print()
        print("Assurez-vous que :")
        print("  1. L'environnement virtuel est activé (source venv/bin/activate)")
        print("  2. Toutes les dépendances sont installées (pip install -r requirements.txt)")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Erreur pendant l'entraînement : {e}")
        print()
        print("Consultez GUIDE_ENTRAINEMENT.md pour plus d'aide.")
        sys.exit(1)

if __name__ == '__main__':
    main()

