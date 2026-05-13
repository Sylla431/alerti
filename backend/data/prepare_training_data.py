"""
Script pour préparer les données d'entraînement à partir des données brutes
Combine CHIRPS + autres sources météo + labels d'inondations
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import json

class TrainingDataPreparator:
    """Prépare les données pour l'entraînement"""
    
    def __init__(self):
        self.data_dir = os.path.dirname(__file__)
        self.raw_dir = os.path.join(self.data_dir, 'raw')
        self.training_dir = os.path.join(self.data_dir, 'training')
        os.makedirs(self.training_dir, exist_ok=True)
        
        # Labels d'inondations historiques pour le Mali
        # Source : FloodList, EM-DAT, rapports locaux
        # TODO: Remplacer par vraies dates d'inondations
        self.known_floods = {
            'Bamako': [
                '2023-08-15', '2023-08-16', '2023-08-17', '2023-08-18',  # Inondations août 2023
                '2022-07-20', '2022-07-21', '2022-07-22',
                '2021-09-05', '2021-09-06', '2021-09-07', '2021-09-08',
                '2020-08-25', '2020-08-26', '2020-08-27'
            ],
            'Sikasso': [
                '2023-07-10', '2023-07-11', '2023-07-12',
                '2022-08-15', '2022-08-16',
                '2021-07-28', '2021-07-29'
            ],
            'Ségou': [
                '2023-08-20', '2023-08-21', '2023-08-22',
                '2021-08-30', '2021-08-31', '2021-09-01'
            ],
            'Mopti': [
                '2023-09-01', '2023-09-02', '2023-09-03',
                '2022-08-10', '2022-08-11'
            ],
            'Gao': [
                '2023-08-05', '2023-08-06',
                '2022-09-15', '2022-09-16'
            ],
            'Kayes': [
                '2023-07-25', '2023-07-26',
                '2021-08-12', '2021-08-13'
            ],
            'Tombouctou': [
                '2023-08-28', '2023-08-29',
                '2022-09-20', '2022-09-21'
            ],
            'Kidal': [
                '2023-09-10', '2023-09-11'
            ]
        }
    
    def load_chirps_data(self, years):
        """Charge les données CHIRPS"""
        print("📊 Chargement des données CHIRPS...")
        
        dfs = []
        for year in years:
            csv_path = os.path.join(self.data_dir, f'chirps_mali_{year}.csv')
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                dfs.append(df)
                print(f"  ✅ Chargé : {year} ({len(df)} lignes)")
            else:
                print(f"  ⚠️  Manquant : {year}")
        
        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
            combined['date'] = pd.to_datetime(combined['date'])
            print(f"\n📊 Total : {len(combined)} lignes")
            return combined
        else:
            return None
    
    def add_synthetic_features(self, df):
        """Ajoute des features synthétiques (à remplacer par vraies données)"""
        print("\n🔧 Ajout des features météo complémentaires...")
        
        np.random.seed(42)
        
        # Température (corrélée avec saison)
        df['month'] = df['date'].dt.month
        base_temp = 28  # Température moyenne au Mali
        seasonal_temp = np.sin((df['month'] - 3) * np.pi / 6) * 5  # Variation saisonnière
        df['temperature'] = base_temp + seasonal_temp + np.random.normal(0, 2, len(df))
        
        # Humidité (corrélée avec précipitations)
        df['humidity'] = np.clip(
            40 + df['precipitation'] * 2 + np.random.normal(0, 5, len(df)),
            20, 95
        )
        
        # Pression atmosphérique
        df['pressure'] = np.random.normal(1013, 3, len(df))
        
        # Humidité du sol (corrélée avec précipitations passées)
        df = df.sort_values(['location', 'date'])
        df['soil_moisture'] = 0.3  # Valeur par défaut
        
        for location in df['location'].unique():
            mask = df['location'] == location
            precip_rolling = df.loc[mask, 'precipitation'].rolling(window=7, min_periods=1).sum()
            df.loc[mask, 'soil_moisture'] = np.clip(
                0.3 + (precip_rolling / 100) + np.random.normal(0, 0.05, mask.sum()),
                0.0, 1.0
            )
        
        df = df.drop('month', axis=1)
        
        print("  ✅ Features ajoutées : temperature, humidity, pressure, soil_moisture")
        print("  ⚠️  Ces features sont SYNTHÉTIQUES. Remplacez-les par vraies données pour de meilleurs résultats.")
        return df
    
    def add_flood_labels(self, df):
        """Ajoute les labels d'inondations"""
        print("\n🏷️  Ajout des labels d'inondations...")
        
        df['flood_occurred'] = 0
        df['flood_severity'] = 0.0
        
        total_floods = 0
        
        for location, dates in self.known_floods.items():
            for date_str in dates:
                try:
                    date = pd.to_datetime(date_str)
                    mask = (df['location'] == location) & (df['date'] == date)
                    
                    if mask.sum() > 0:
                        df.loc[mask, 'flood_occurred'] = 1
                        df.loc[mask, 'flood_severity'] = np.random.uniform(0.6, 1.0)  # Sévérité élevée
                        total_floods += 1
                        
                        # Ajouter aussi les jours avant/après avec sévérité réduite
                        for delta in [-1, 1]:
                            nearby_date = date + timedelta(days=delta)
                            mask_nearby = (df['location'] == location) & (df['date'] == nearby_date)
                            if mask_nearby.sum() > 0 and df.loc[mask_nearby, 'flood_occurred'].iloc[0] == 0:
                                df.loc[mask_nearby, 'flood_occurred'] = 1
                                df.loc[mask_nearby, 'flood_severity'] = np.random.uniform(0.3, 0.6)
                                total_floods += 1
                except Exception as e:
                    print(f"  ⚠️  Erreur pour {location} - {date_str}: {e}")
        
        flood_count = df['flood_occurred'].sum()
        flood_pct = (flood_count / len(df)) * 100
        print(f"  ✅ Labels ajoutés : {flood_count} jours d'inondation ({flood_pct:.2f}%)")
        print(f"  📊 Événements uniques : {total_floods}")
        
        return df
    
    def create_sequences_for_lstm(self, df, sequence_length=30):
        """Crée les séquences pour le modèle LSTM"""
        print(f"\n📦 Création des séquences ({sequence_length} jours)...")
        
        feature_cols = ['precipitation', 'temperature', 'humidity', 'pressure', 'soil_moisture']
        
        X = []
        y = []
        metadata = []
        
        df = df.sort_values(['location', 'date'])
        
        for location in df['location'].unique():
            location_df = df[df['location'] == location].reset_index(drop=True)
            
            for i in range(len(location_df) - sequence_length - 7):  # -7 pour avoir 7 jours de prévision
                # Séquence de features
                sequence = location_df.iloc[i:i+sequence_length][feature_cols].values
                
                # Label (inondation dans les 7 jours suivants)
                future_window = location_df.iloc[i+sequence_length:i+sequence_length+7]
                flood_in_future = future_window['flood_occurred'].max()
                max_severity = future_window['flood_severity'].max()
                
                X.append(sequence)
                y.append(max_severity if flood_in_future else 0.0)
                metadata.append({
                    'location': location,
                    'end_date': location_df.iloc[i+sequence_length-1]['date'].strftime('%Y-%m-%d')
                })
        
        positive_samples = sum(1 for label in y if label > 0.3)
        positive_pct = (positive_samples / len(y)) * 100 if len(y) > 0 else 0
        
        print(f"  ✅ Créé : {len(X)} séquences")
        print(f"     Positives (inondation) : {positive_samples} ({positive_pct:.1f}%)")
        print(f"     Négatives (pas inondation) : {len(y) - positive_samples} ({100-positive_pct:.1f}%)")
        
        return np.array(X), np.array(y), metadata
    
    def save_training_data(self, X, y, metadata, split='train'):
        """Sauvegarde les données d'entraînement"""
        output_dir = os.path.join(self.training_dir, 'lstm')
        os.makedirs(output_dir, exist_ok=True)
        
        # Sauvegarder les arrays numpy
        np.save(os.path.join(output_dir, f'X_{split}.npy'), X)
        np.save(os.path.join(output_dir, f'y_{split}.npy'), y)
        
        # Sauvegarder les métadonnées
        with open(os.path.join(output_dir, f'metadata_{split}.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n✅ Données sauvegardées dans : {output_dir}/")
        print(f"   X_{split}.npy : {X.shape}")
        print(f"   y_{split}.npy : {y.shape}")


def main():
    """Fonction principale"""
    print("=" * 60)
    print("📊 PRÉPARATION DES DONNÉES D'ENTRAÎNEMENT")
    print("=" * 60)
    
    preparator = TrainingDataPreparator()
    
    # 1. Charger les données CHIRPS
    years = [2020, 2021, 2022, 2023, 2024]
    df = preparator.load_chirps_data(years)
    
    if df is None or len(df) == 0:
        print("\n❌ Aucune donnée CHIRPS trouvée !")
        print("\n📝 Lancez d'abord :")
        print("   python download_chirps.py")
        return
    
    # 2. Ajouter les features complémentaires
    df = preparator.add_synthetic_features(df)
    
    # 3. Ajouter les labels d'inondations
    df = preparator.add_flood_labels(df)
    
    # 4. Sauvegarder le dataset complet
    full_csv = os.path.join(preparator.training_dir, 'mali_weather_complete.csv')
    df.to_csv(full_csv, index=False)
    print(f"\n✅ Dataset complet sauvegardé : {full_csv}")
    print(f"   📊 {len(df)} lignes, {len(df['location'].unique())} villes")
    
    # 5. Créer les séquences pour LSTM
    X, y, metadata = preparator.create_sequences_for_lstm(df, sequence_length=30)
    
    if len(X) == 0:
        print("\n❌ Aucune séquence créée ! Vérifiez les données.")
        return
    
    # 6. Split train/validation (80/20)
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]
    meta_train, meta_val = metadata[:split_idx], metadata[split_idx:]
    
    # 7. Sauvegarder
    preparator.save_training_data(X_train, y_train, meta_train, 'train')
    preparator.save_training_data(X_val, y_val, meta_val, 'val')
    
    print("\n" + "=" * 60)
    print("✅ PRÉPARATION TERMINÉE !")
    print("=" * 60)
    print("\n📝 Prochaine étape :")
    print("   cd ..")
    print("   python -m models.model_trainer_real")
    print("\n💡 CONSEIL :")
    print("   Les features météo (température, humidité, etc.) sont synthétiques.")
    print("   Pour de meilleurs résultats, remplacez-les par vraies données (ERA5, GPM, etc.)")


if __name__ == '__main__':
    main()

