"""
Script de vérification de l'installation et de la configuration
Vérifie que tous les outils nécessaires sont disponibles
"""
import sys
import os

def check_dependencies():
    """Vérifie les dépendances Python"""
    print("=" * 60)
    print("🔍 VÉRIFICATION DES DÉPENDANCES")
    print("=" * 60)
    
    dependencies = {
        'numpy': 'NumPy',
        'pandas': 'Pandas',
        'requests': 'Requests',
        'sklearn': 'Scikit-learn',
        'tensorflow': 'TensorFlow',
        'keras': 'Keras'
    }
    
    optional_deps = {
        'gdal': 'GDAL (pour extraction CHIRPS)',
        'rasterio': 'Rasterio (alternative à GDAL)',
        'sentinelsat': 'SentinelSat (téléchargement Sentinel)'
    }
    
    print("\n📦 Dépendances requises :")
    all_ok = True
    for module, name in dependencies.items():
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} - MANQUANT")
            all_ok = False
    
    print("\n📦 Dépendances optionnelles :")
    for module, name in optional_deps.items():
        try:
            if module == 'gdal':
                from osgeo import gdal
            else:
                __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ⚠️  {name} - Non installé (optionnel)")
    
    return all_ok


def check_directories():
    """Vérifie la structure des dossiers"""
    print("\n" + "=" * 60)
    print("📁 VÉRIFICATION DES DOSSIERS")
    print("=" * 60)
    
    base_dir = os.path.dirname(__file__)
    
    required_dirs = [
        'raw',
        'raw/chirps',
        'raw/sentinel',
        'training',
        'training/lstm',
        'training/cnn'
    ]
    
    all_ok = True
    for dir_name in required_dirs:
        dir_path = os.path.join(base_dir, dir_name)
        if os.path.exists(dir_path):
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ - MANQUANT")
            all_ok = False
    
    return all_ok


def check_scripts():
    """Vérifie que les scripts sont présents"""
    print("\n" + "=" * 60)
    print("📄 VÉRIFICATION DES SCRIPTS")
    print("=" * 60)
    
    base_dir = os.path.dirname(__file__)
    
    scripts = [
        'download_chirps.py',
        'download_sentinel.py',
        'prepare_training_data.py'
    ]
    
    all_ok = True
    for script in scripts:
        script_path = os.path.join(base_dir, script)
        if os.path.exists(script_path):
            print(f"  ✅ {script}")
        else:
            print(f"  ❌ {script} - MANQUANT")
            all_ok = False
    
    return all_ok


def check_data():
    """Vérifie les données disponibles"""
    print("\n" + "=" * 60)
    print("📊 VÉRIFICATION DES DONNÉES")
    print("=" * 60)
    
    base_dir = os.path.dirname(__file__)
    
    # Vérifier CHIRPS
    chirps_dir = os.path.join(base_dir, 'raw', 'chirps')
    if os.path.exists(chirps_dir):
        tif_files = [f for f in os.listdir(chirps_dir) if f.endswith('.tif')]
        print(f"\n  📥 Fichiers CHIRPS : {len(tif_files)}")
        if len(tif_files) > 0:
            print(f"     Exemple : {tif_files[0]}")
    else:
        print("\n  ⚠️  Aucun fichier CHIRPS téléchargé")
    
    # Vérifier CSV
    csv_files = [f for f in os.listdir(base_dir) if f.startswith('chirps_mali_') and f.endswith('.csv')]
    print(f"\n  📄 CSV CHIRPS extraits : {len(csv_files)}")
    for csv in csv_files:
        print(f"     • {csv}")
    
    # Vérifier données d'entraînement
    training_dir = os.path.join(base_dir, 'training', 'lstm')
    if os.path.exists(training_dir):
        npy_files = [f for f in os.listdir(training_dir) if f.endswith('.npy')]
        print(f"\n  🎓 Données d'entraînement : {len(npy_files)} fichiers")
        for npy in npy_files:
            npy_path = os.path.join(training_dir, npy)
            size_mb = os.path.getsize(npy_path) / (1024 * 1024)
            print(f"     • {npy} ({size_mb:.1f} MB)")


def check_models():
    """Vérifie les modèles entraînés"""
    print("\n" + "=" * 60)
    print("🤖 VÉRIFICATION DES MODÈLES")
    print("=" * 60)
    
    models_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'models'
    )
    
    model_files = ['lstm_model.h5', 'cnn_model.h5', 'fusion_model.h5']
    
    for model_file in model_files:
        model_path = os.path.join(models_dir, model_file)
        if os.path.exists(model_path):
            size_mb = os.path.getsize(model_path) / (1024 * 1024)
            print(f"  ✅ {model_file} ({size_mb:.1f} MB)")
        else:
            print(f"  ⚠️  {model_file} - Non entraîné")


def print_next_steps(deps_ok, dirs_ok, scripts_ok):
    """Affiche les prochaines étapes"""
    print("\n" + "=" * 60)
    print("📝 PROCHAINES ÉTAPES")
    print("=" * 60)
    
    if not deps_ok:
        print("\n❌ Installez les dépendances manquantes :")
        print("   pip install -r requirements.txt")
        return
    
    if not dirs_ok:
        print("\n❌ Créez les dossiers manquants :")
        print("   mkdir -p backend/data/raw/chirps backend/data/raw/sentinel")
        print("   mkdir -p backend/data/training/lstm backend/data/training/cnn")
        return
    
    if not scripts_ok:
        print("\n❌ Scripts manquants ! Vérifiez votre installation.")
        return
    
    print("\n✅ Tout est prêt ! Suivez ces étapes :")
    print("\n1️⃣  Télécharger les données CHIRPS :")
    print("   python download_chirps.py")
    print("\n2️⃣  Préparer les données d'entraînement :")
    print("   python prepare_training_data.py")
    print("\n3️⃣  Entraîner les modèles :")
    print("   cd ..")
    print("   python -m models.model_trainer_real")
    print("\n4️⃣  Lancer l'application :")
    print("   python app.py")
    
    print("\n💡 Pour plus de détails, consultez :")
    print("   • README_DATA.md (données réelles)")
    print("   • GUIDE_ENTRAINEMENT.md (entraînement)")


def main():
    """Fonction principale"""
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "VÉRIFICATION DE L'INSTALLATION" + " " * 17 + "║")
    print("╚" + "═" * 58 + "╝")
    
    deps_ok = check_dependencies()
    dirs_ok = check_directories()
    scripts_ok = check_scripts()
    check_data()
    check_models()
    
    print_next_steps(deps_ok, dirs_ok, scripts_ok)
    
    print("\n" + "=" * 60)
    if deps_ok and dirs_ok and scripts_ok:
        print("✅ INSTALLATION COMPLÈTE !")
    else:
        print("⚠️  INSTALLATION INCOMPLÈTE")
    print("=" * 60)


if __name__ == '__main__':
    main()

