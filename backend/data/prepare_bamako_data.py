"""
Script pour préparer les données d'entraînement pour les 6 communes de Bamako
Version adaptée et simplifiée pour Bamako
"""
import argparse
import glob
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
import json

# Ajouter le chemin backend
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.bamako_communes import BAMAKO_COMMUNES
from utils.bamako_features import get_static_features, get_risk_factors


class BamakoDataPreparator:
    """Prépare les données pour l'entraînement - Communes de Bamako"""
    
    def __init__(self):
        self.data_dir = os.path.dirname(__file__)
        self.raw_dir = os.path.join(self.data_dir, 'raw')
        self.training_dir = os.path.join(self.data_dir, 'training')
        os.makedirs(self.training_dir, exist_ok=True)
        
        # Labels d'inondations historiques pour Bamako par commune
        # Source : FloodList, rapports locaux, médias maliens
        # TODO: Compléter avec dates réelles d'inondations
        self.known_floods = {
            'Commune I': [
                '2024-10-08', '2024-08-17', '2024-07-22',  # Nouveaux événements 2024
                '2023-08-15', '2023-08-16', '2023-08-17',  # Inondations août 2023
                '2022-09-10', '2022-09-11',  # Médina Coura inondée
                '2021-08-20', '2021-08-21'
            ],
            'Commune II': [
                '2024-10-08', '2024-08-17', '2024-07-22',
                '2023-08-15', '2023-08-16',  # Centre-ville touché
                '2022-09-10', '2022-09-11',
                '2021-08-20'
            ],
            'Commune III': [
                '2024-10-08', '2024-08-17', '2024-07-22',
                '2023-07-28', '2023-07-29',  # Point G
                '2022-08-25', '2022-08-26',
                '2021-09-05'
            ],
            'Commune IV': [
                '2024-10-08', '2024-08-17', '2024-07-22',
                '2023-08-15', '2023-08-16', '2023-08-17', '2023-08-18',  # Lafiabougou très touchée
                '2022-09-10', '2022-09-11', '2022-09-12',
                '2021-08-20', '2021-08-21', '2021-08-22'
            ],
            'Commune V': [
                '2024-10-08', '2024-08-17', '2024-07-22',
                '2023-08-15', '2023-08-16', '2023-08-17', '2023-08-18',  # Zone périurbaine, risque élevé
                '2022-09-10', '2022-09-11', '2022-09-12',
                '2021-08-20', '2021-08-21', '2021-08-22',
                '2020-09-01', '2020-09-02'
            ],
            'Commune VI': [
                '2024-10-08', '2024-08-17', '2024-07-22',
                '2023-08-16', '2023-08-17',  # Sogoniko
                '2022-09-11', '2022-09-12',
                '2021-08-21', '2021-08-22'
            ]
        }
    
    def _detect_available_years(self):
        """Détecte automatiquement les fichiers CHIRPS déjà extraits."""
        pattern = os.path.join(self.raw_dir, 'bamako_communes_*.csv')
        detected_years = []
        for filepath in glob.glob(pattern):
            filename = os.path.basename(filepath)
            year_part = filename.replace('bamako_communes_', '').replace('.csv', '')
            if year_part.isdigit():
                detected_years.append(int(year_part))
        return sorted(set(detected_years))
    
    def load_bamako_data(self, years=None, preferred_source='auto'):
        """Charge les données météo pour Bamako (OpenWeather prioritaire)."""
        # Chercher les fichiers journaliers possibles
        openweather_dir = os.path.join(self.raw_dir, 'openweather')
        possible_files = [
            os.path.join(openweather_dir, 'bamako_communes_openweather_daily.csv'),
            os.path.join(openweather_dir, 'bamako_communes_meteo_agence.csv'),
        ]
        
        openweather_csv = None
        for csv_path in possible_files:
            if os.path.exists(csv_path):
                openweather_csv = csv_path
                break
        
        if preferred_source in ('openweather', 'auto') and openweather_csv:
            df = pd.read_csv(openweather_csv, parse_dates=['date'])
            df = df.sort_values('date')
            print("📊 Chargement des données journalières (OpenWeather/Agence Météo)")
            print(f"  ✅ Fichier : {openweather_csv}")
            print(f"  📅 Période : {df['date'].min().date()} → {df['date'].max().date()}")
            print(f"  📊 Lignes : {len(df)}")
            return df
        elif preferred_source == 'openweather':
            print("  ⚠️  Aucun fichier journalier trouvé, fallback CHIRPS.")
        
        print("📊 Chargement des données CHIRPS pour Bamako...")
        
        if not years:
            years = self._detect_available_years()
            if not years:
                print("  ❌ Aucun fichier bamako_communes_YYYY.csv disponible dans raw/")
                return None
        
        dfs = []
        for year in years:
            csv_path = os.path.join(self.raw_dir, f'bamako_communes_{year}.csv')
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                dfs.append(df)
                print(f"  ✅ Chargé : {year} ({len(df)} lignes)")
            else:
                print(f"  ⚠️  Manquant : {year}")
        
        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
            combined['date'] = pd.to_datetime(combined['date'])
            print(f"\n📊 Total : {len(combined)} lignes, {len(combined['commune'].unique())} communes")
            return combined
        else:
            return None
    
    def add_synthetic_features(self, df):
        """Ajoute des features météo complémentaires"""
        print("\n🔧 Ajout des features météo complémentaires...")
        
        np.random.seed(42)
        df['month'] = df['date'].dt.month
        used_real_temp = False
        used_real_humidity = False
        used_real_pressure = False
        
        # Température : utiliser OpenWeather si disponible, sinon synthétique
        if 'temperature_mean' in df.columns and df['temperature_mean'].notna().any():
            df['temperature'] = df['temperature_mean'].ffill().bfill()
            used_real_temp = True
        else:
            base_temp = 30  # Température moyenne à Bamako
            seasonal_temp = np.sin((df['month'] - 3) * np.pi / 6) * 4
            df['temperature'] = base_temp + seasonal_temp + np.random.normal(0, 2, len(df))
        
        # Humidité : OpenWeather si dispo
        if 'humidity_mean' in df.columns and df['humidity_mean'].notna().any():
            df['humidity'] = df['humidity_mean'].clip(0, 100).ffill().bfill()
            used_real_humidity = True
        else:
            df['humidity'] = np.clip(
                45 + df['precipitation'] * 3 + np.random.normal(0, 5, len(df)),
                25, 95
            )
        
        # Pression : OpenWeather si dispo
        if 'pressure_mean' in df.columns and df['pressure_mean'].notna().any():
            df['pressure'] = df['pressure_mean'].ffill().bfill()
            used_real_pressure = True
        else:
            df['pressure'] = np.random.normal(1011, 3, len(df))
        
        # Humidité du sol (corrélée avec précipitations passées)
        df = df.sort_values(['commune', 'date'])
        df['soil_moisture'] = 0.25  # Valeur par défaut
        
        for commune in df['commune'].unique():
            mask = df['commune'] == commune
            precip_rolling = df.loc[mask, 'precipitation'].rolling(window=7, min_periods=1).sum()
            df.loc[mask, 'soil_moisture'] = np.clip(
                0.25 + (precip_rolling / 120) + np.random.normal(0, 0.05, mask.sum()),
                0.0, 1.0
            )
        
        df = df.drop('month', axis=1)
        
        real_sources = []
        if used_real_temp:
            real_sources.append("température OpenWeather")
        if used_real_humidity:
            real_sources.append("humidité OpenWeather")
        if used_real_pressure:
            real_sources.append("pression OpenWeather")
        
        if real_sources:
            print(f"  ✅ Features météo ajoutées (avec {', '.join(real_sources)})")
        else:
            print("  ✅ Features météo ajoutées : temperature, humidity, pressure, soil_moisture")
        return df
    
    def add_static_features(self, df):
        """Ajoute les features statiques (topographie, infrastructure, etc.)"""
        print("\n🏗️  Ajout des features statiques (topographie, infrastructure, urbanisation)...")
        
        # Ajouter features statiques pour chaque commune
        for commune in df['commune'].unique():
            mask = df['commune'] == commune
            static_features = get_static_features(commune)
            
            if static_features:
                # Topographie
                df.loc[mask, 'elevation'] = static_features['elevation']
                df.loc[mask, 'slope'] = static_features['slope']
                df.loc[mask, 'distance_to_river'] = static_features['distance_to_river']
                df.loc[mask, 'in_flood_plain'] = static_features['in_flood_plain']
                df.loc[mask, 'depression_depth'] = static_features['depression_depth']
                
                # Infrastructure drainage
                df.loc[mask, 'drainage_density'] = static_features['drainage_density']
                df.loc[mask, 'drainage_state'] = static_features['drainage_state']
                df.loc[mask, 'drainage_coverage'] = static_features['drainage_coverage']
                df.loc[mask, 'blocked_drainage_pct'] = static_features['blocked_drainage_pct']
                
                # Urbanisation
                df.loc[mask, 'impermeable_surface'] = static_features['impermeable_surface']
                df.loc[mask, 'building_density'] = static_features['building_density']
                df.loc[mask, 'population_density'] = static_features['population_density']
                
                # Hydrologie
                df.loc[mask, 'groundwater_level'] = static_features['groundwater_level']
                df.loc[mask, 'runoff_coefficient'] = static_features['runoff_coefficient']
                df.loc[mask, 'infiltration_rate'] = static_features['infiltration_rate']
                df.loc[mask, 'soil_permeability'] = static_features['soil_permeability']
                
                # Végétation
                df.loc[mask, 'vegetation_cover'] = static_features['vegetation_cover']
                df.loc[mask, 'ndvi_avg'] = static_features['ndvi_avg']
                
                # Vulnérabilité
                df.loc[mask, 'informal_settlement_pct'] = static_features['informal_settlement_pct']
                df.loc[mask, 'poverty_index'] = static_features['poverty_index']
                df.loc[mask, 'flood_preparedness'] = static_features['flood_preparedness']
        
        print("  ✅ Features statiques ajoutées : 20+ features (topographie, drainage, urbanisation, etc.)")
        return df
    
    def add_temporal_features(self, df):
        """Ajoute les features temporelles (précipitations accumulées)"""
        print("\n⏰ Ajout des features temporelles (précipitations accumulées)...")
        
        df = df.sort_values(['commune', 'date'])
        
        for commune in df['commune'].unique():
            mask = df['commune'] == commune
            commune_df = df.loc[mask].copy()
            
            # Précipitations accumulées sur 3 jours
            df.loc[mask, 'antecedent_precip_3d'] = (
                commune_df['precipitation'].rolling(window=3, min_periods=1).sum()
            )
            
            # Précipitations accumulées sur 7 jours
            df.loc[mask, 'antecedent_precip_7d'] = (
                commune_df['precipitation'].rolling(window=7, min_periods=1).sum()
            )
            
            # Précipitations accumulées sur 14 jours
            df.loc[mask, 'antecedent_precip_14d'] = (
                commune_df['precipitation'].rolling(window=14, min_periods=1).sum()
            )
            
            # Indice de saturation du sol (basé sur précipitations récentes)
            precip_30d = commune_df['precipitation'].rolling(window=30, min_periods=1).sum()
            df.loc[mask, 'soil_saturation_index'] = np.clip(
                precip_30d / 200,  # Normalisé sur 200mm
                0.0, 1.0
            )
        
        print("  ✅ Features temporelles ajoutées : antecedent_precip_3d, antecedent_precip_7d, antecedent_precip_14d, soil_saturation_index")
        return df
    
    def add_flood_labels(self, df):
        """Ajoute les labels d'inondations"""
        print("\n🏷️  Ajout des labels d'inondations...")
        
        df['flood_occurred'] = 0
        df['flood_severity'] = 0.0
        
        total_floods = 0
        
        for commune, dates in self.known_floods.items():
            if commune not in df['commune'].values:
                continue
                
            for date_str in dates:
                try:
                    date = pd.to_datetime(date_str)
                    mask = (df['commune'] == commune) & (df['date'] == date)
                    
                    if mask.sum() > 0:
                        # Sévérité basée sur la commune (Commune V et IV plus à risque)
                        if commune in ['Commune IV', 'Commune V']:
                            severity = np.random.uniform(0.7, 1.0)
                        else:
                            severity = np.random.uniform(0.5, 0.8)
                        
                        df.loc[mask, 'flood_occurred'] = 1
                        df.loc[mask, 'flood_severity'] = severity
                        total_floods += 1
                        
                        # Ajouter jours avant/après
                        for delta in [-1, 1]:
                            nearby_date = date + timedelta(days=delta)
                            mask_nearby = (df['commune'] == commune) & (df['date'] == nearby_date)
                            if mask_nearby.sum() > 0 and df.loc[mask_nearby, 'flood_occurred'].iloc[0] == 0:
                                df.loc[mask_nearby, 'flood_occurred'] = 1
                                df.loc[mask_nearby, 'flood_severity'] = severity * 0.5
                                total_floods += 1
                except Exception as e:
                    print(f"  ⚠️  Erreur pour {commune} - {date_str}: {e}")
        
        flood_count = df['flood_occurred'].sum()
        flood_pct = (flood_count / len(df)) * 100
        print(f"  ✅ Labels ajoutés : {flood_count} jours d'inondation ({flood_pct:.2f}%)")
        print(f"  📊 Événements uniques : {total_floods}")
        
        # Statistiques par commune
        print(f"\n  📊 Jours d'inondation par commune:")
        for commune in sorted(df['commune'].unique()):
            commune_floods = df[df['commune'] == commune]['flood_occurred'].sum()
            print(f"     • {commune:15s} : {commune_floods:3d} jours")
        
        return df
    
    def create_sequences_for_lstm(self, df, sequence_length=30):
        """Crée les séquences pour le modèle LSTM avec toutes les features"""
        print(f"\n📦 Création des séquences ({sequence_length} jours)...")
        
        # Features météo (temporelles)
        feature_cols = [
            'precipitation', 'temperature', 'humidity', 'pressure', 'soil_moisture',
            'antecedent_precip_3d', 'antecedent_precip_7d', 'antecedent_precip_14d',
            'soil_saturation_index'
        ]
        
        # Features statiques (ajoutées à chaque timestep)
        static_cols = [
            'elevation', 'slope', 'distance_to_river', 'in_flood_plain', 'depression_depth',
            'drainage_density', 'drainage_state', 'drainage_coverage', 'blocked_drainage_pct',
            'impermeable_surface', 'building_density', 'population_density',
            'groundwater_level', 'runoff_coefficient', 'infiltration_rate', 'soil_permeability',
            'vegetation_cover', 'ndvi_avg',
            'informal_settlement_pct', 'poverty_index', 'flood_preparedness'
        ]
        
        # Vérifier que toutes les colonnes existent
        all_cols = feature_cols + static_cols
        missing_cols = [col for col in all_cols if col not in df.columns]
        if missing_cols:
            print(f"  ⚠️  Colonnes manquantes : {missing_cols}")
            # Utiliser seulement les colonnes disponibles
            feature_cols = [col for col in feature_cols if col in df.columns]
            static_cols = [col for col in static_cols if col in df.columns]
        
        print(f"  📊 Features utilisées : {len(feature_cols)} temporelles + {len(static_cols)} statiques = {len(feature_cols) + len(static_cols)} total")
        
        X = []
        y = []
        metadata = []
        
        df = df.sort_values(['commune', 'date'])
        
        for commune in df['commune'].unique():
            commune_df = df[df['commune'] == commune].reset_index(drop=True)
            
            for i in range(len(commune_df) - sequence_length - 7):
                # Séquence de features temporelles
                temporal_seq = commune_df.iloc[i:i+sequence_length][feature_cols].values
                temporal_seq = temporal_seq.astype(np.float32)
                
                # Features statiques (mêmes valeurs pour toute la séquence)
                static_vals = commune_df.iloc[i][static_cols].values if static_cols else np.array([])
                static_vals = static_vals.astype(np.float32)
                
                # Combiner (répéter les statiques pour chaque timestep)
                if static_vals.size > 0:
                    static_seq = np.tile(static_vals, (sequence_length, 1))
                    sequence = np.concatenate([temporal_seq, static_seq], axis=1)
                else:
                    sequence = temporal_seq
                
                # S'assurer que la séquence est en float32
                sequence = sequence.astype(np.float32)
                
                # Label (inondation dans les 7 jours suivants)
                future_window = commune_df.iloc[i+sequence_length:i+sequence_length+7]
                flood_in_future = future_window['flood_occurred'].max()
                max_severity = future_window['flood_severity'].max()
                
                X.append(sequence)
                y.append(max_severity if flood_in_future else 0.0)
                metadata.append({
                    'commune': commune,
                    'end_date': commune_df.iloc[i+sequence_length-1]['date'].strftime('%Y-%m-%d')
                })
        
        positive_samples = sum(1 for label in y if label > 0.3)
        positive_pct = (positive_samples / len(y)) * 100 if len(y) > 0 else 0
        
        print(f"  ✅ Créé : {len(X)} séquences")
        print(f"     Positives (inondation) : {positive_samples} ({positive_pct:.1f}%)")
        print(f"     Négatives : {len(y) - positive_samples} ({100-positive_pct:.1f}%)")
        
        # Convertir en arrays numpy avec types explicites
        X_array = np.array(X, dtype=np.float32)
        y_array = np.array(y, dtype=np.float32)
        
        # Remplacer les NaN par 0 (ou moyenne si nécessaire)
        if np.isnan(X_array).any():
            print(f"  ⚠️  {np.isnan(X_array).sum()} valeurs NaN détectées, remplacement par 0")
            X_array = np.nan_to_num(X_array, nan=0.0, posinf=0.0, neginf=0.0)
        
        if np.isnan(y_array).any():
            print(f"  ⚠️  {np.isnan(y_array).sum()} labels NaN détectés, remplacement par 0")
            y_array = np.nan_to_num(y_array, nan=0.0, posinf=0.0, neginf=0.0)
        
        return X_array, y_array, metadata
    
    def save_training_data(self, X, y, metadata, split='train'):
        """Sauvegarde les données d'entraînement"""
        output_dir = os.path.join(self.training_dir, 'bamako_lstm')
        os.makedirs(output_dir, exist_ok=True)
        
        # Sauvegarder les arrays numpy
        np.save(os.path.join(output_dir, f'X_{split}.npy'), X)
        np.save(os.path.join(output_dir, f'y_{split}.npy'), y)
        
        # Sauvegarder les métadonnées
        with open(os.path.join(output_dir, f'metadata_{split}.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n✅ Données sauvegardées : {output_dir}/")
        print(f"   X_{split}.npy : {X.shape}")
        print(f"   y_{split}.npy : {y.shape}")


def parse_args():
    parser = argparse.ArgumentParser(description="Prépare les données d'entraînement pour Bamako.")
    parser.add_argument(
        '--source',
        choices=['auto', 'openweather', 'chirps'],
        default='auto',
        help="Source principale des précipitations (par défaut auto : OpenWeather si dispo, sinon CHIRPS)."
    )
    parser.add_argument(
        '--years',
        nargs='+',
        type=int,
        help="Années CHIRPS à utiliser (format YYYY). Ignoré si source=openweather et fichier dispo."
    )
    return parser.parse_args()


def main():
    """Fonction principale"""
    print("=" * 60)
    print("📊 PRÉPARATION DES DONNÉES - 6 COMMUNES DE BAMAKO")
    print("=" * 60)
    
    args = parse_args()
    preparator = BamakoDataPreparator()
    
    # 1. Charger les données météo
    df = preparator.load_bamako_data(years=args.years, preferred_source=args.source)
    
    if df is None or len(df) == 0:
        print("\n❌ Aucune donnée météo disponible !")
        print("\n📝 Étapes possibles :")
        print("   • python download_openweather_precip.py --days 90")
        print("   • ou python read_chirps_bamako.py (pour générer les CSV CHIRPS)")
        return
    
    # 2. Ajouter les features météo complémentaires
    df = preparator.add_synthetic_features(df)
    
    # 3. Ajouter les features statiques (topographie, infrastructure, etc.)
    df = preparator.add_static_features(df)
    
    # 4. Ajouter les features temporelles (précipitations accumulées)
    df = preparator.add_temporal_features(df)
    
    # 5. Ajouter les labels d'inondations
    df = preparator.add_flood_labels(df)
    
    # 4. Sauvegarder le dataset complet
    full_csv = os.path.join(preparator.training_dir, 'bamako_weather_complete.csv')
    df.to_csv(full_csv, index=False)
    print(f"\n✅ Dataset complet sauvegardé : {full_csv}")
    print(f"   📊 {len(df)} lignes, {len(df['commune'].unique())} communes")
    
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
    print("   python -m models.model_trainer_bamako")
    
    print("\n💡 CONSEIL :")
    print("   Les données sont prêtes pour entraîner un modèle spécifique à Bamako")
    print("   Le modèle pourra prédire les inondations par commune !")


if __name__ == '__main__':
    main()

