"""
Script principal pour télécharger toutes les données des nouvelles features
Lance tous les téléchargements nécessaires
"""
import os
import sys
import subprocess

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Lance tous les téléchargements"""
    print("=" * 60)
    print("📊 TÉLÉCHARGEMENT DE TOUTES LES DONNÉES")
    print("=" * 60)
    
    print("\n📝 Ce script va télécharger :")
    print("   1. Topographie (SRTM) - Élévation, Pente")
    print("   2. Urbanisation (OSM) - Bâtiments, Drainage")
    print("   3. Précipitations (CHIRPS) - Déjà fait")
    
    print("\n⚠️  Note : Certains téléchargements nécessitent :")
    print("   - Compte NASA Earthdata (pour SRTM)")
    print("   - Connexion internet stable")
    print("   - 30-60 minutes de temps")
    
    response = input("\nContinuer ? (o/n) : ")
    if response.lower() != 'o':
        print("❌ Annulé")
        return
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Topographie
    print("\n" + "=" * 60)
    print("🗻 1/2 : TOPOGRAPHIE (SRTM)")
    print("=" * 60)
    try:
        topo_script = os.path.join(script_dir, 'download_topography.py')
        result = subprocess.run([sys.executable, topo_script], 
                              cwd=script_dir, 
                              check=False)
        if result.returncode != 0:
            print("⚠️  Erreur lors de l'exécution du script topographie")
            print("   Continuez avec téléchargement manuel (voir GUIDE_DONNEES_FEATURES.md)")
    except Exception as e:
        print(f"⚠️  Erreur topographie : {e}")
        print("   Continuez avec téléchargement manuel (voir GUIDE_DONNEES_FEATURES.md)")
    
    # 2. Urbanisation
    print("\n" + "=" * 60)
    print("🏙️  2/2 : URBANISATION (OpenStreetMap)")
    print("=" * 60)
    try:
        urban_script = os.path.join(script_dir, 'download_urbanization.py')
        result = subprocess.run([sys.executable, urban_script], 
                              cwd=script_dir, 
                              check=False)
        if result.returncode != 0:
            print("⚠️  Erreur lors de l'exécution du script urbanisation")
            print("   Vérifiez votre connexion internet")
    except Exception as e:
        print(f"⚠️  Erreur urbanisation : {e}")
        print("   Vérifiez votre connexion internet")
    
    print("\n" + "=" * 60)
    print("✅ TÉLÉCHARGEMENT TERMINÉ !")
    print("=" * 60)
    
    print("\n📝 Prochaines étapes :")
    print("   1. Vérifiez les fichiers dans backend/data/raw/")
    print("   2. Mettez à jour bamako_features.py avec les vraies valeurs")
    print("   3. Relancez prepare_bamako_data.py")
    print("   4. Entraînez le modèle : python -m models.model_trainer_bamako")


if __name__ == '__main__':
    main()

