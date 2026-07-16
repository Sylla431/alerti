"""
Préparation des données d'entraînement — variante PLUVIOMÉTRIE SEULE (Bamako-ville).

Contrairement à prepare_bamako_data.py (29 features, niveau commune), ce script :
  - Traite Bamako comme UNE seule série journalière (la pluie de la source
    OpenWeather/Agence est identique dans les 6 communes, donc on la déduplique).
  - N'utilise QUE des features dérivées de la pluie (5 au total).
  - Assume explicitement une prédiction de risque RÉGIONAL (toute la ville),
    sans chercher à différencier les communes/quartiers.

Sortie : backend/data/training/bamako_rainfall_only/{X,y}_{train,val}.npy + metadata.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

# Ajouter le chemin backend pour les imports internes
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.prepare_bamako_data import BamakoDataPreparator
from utils.config import LSTM_FORECAST_DAYS, LSTM_SEQUENCE_LENGTH

# Les 5 features dérivées de la pluie (cohérentes avec add_temporal_features())
RAINFALL_FEATURE_COLS = [
    "precipitation",
    "antecedent_precip_3d",
    "antecedent_precip_7d",
    "antecedent_precip_14d",
    "soil_saturation_index",
]


def _subset(items, mask):
    """Filtre une liste Python selon un masque booléen numpy."""
    return [item for item, keep in zip(items, mask) if keep]


class BamakoRainfallOnlyPreparator:
    """Prépare des séquences LSTM pluie-seule pour Bamako (série ville unique)."""

    def __init__(self):
        self.data_dir = os.path.dirname(__file__)
        self.raw_dir = os.path.join(self.data_dir, "raw")
        self.training_dir = os.path.join(self.data_dir, "training")
        self.output_dir = os.path.join(self.training_dir, "bamako_rainfall_only")
        os.makedirs(self.output_dir, exist_ok=True)

        # Réutilise le calendrier d'inondations connu du pipeline existant
        # pour rester cohérent (mêmes événements réels).
        self._known_floods = BamakoDataPreparator().known_floods

    # ------------------------------------------------------------------ #
    # 1. Chargement de la série pluie unique (Bamako-ville)
    # ------------------------------------------------------------------ #
    def load_city_rainfall(self, source="auto"):
        """Charge une série journalière unique de pluie pour Bamako-ville.

        source :
          - "chirps"      : pluie satellitaire RÉELLE (bamako_chirps_daily.csv),
                            générée par build_bamako_chirps_daily.py ;
          - "openweather" : CSV OpenWeather/Agence (dédupliqué en série ville) ;
          - "auto"        : CHIRPS si disponible, sinon OpenWeather.
        """
        chirps_csv = os.path.join(self.raw_dir, "chirps", "bamako_chirps_daily.csv")
        openweather_csv = os.path.join(
            self.raw_dir, "openweather", "bamako_communes_meteo_agence.csv"
        )

        use_chirps = source == "chirps" or (
            source == "auto" and os.path.exists(chirps_csv)
        )

        if use_chirps:
            if not os.path.exists(chirps_csv):
                raise FileNotFoundError(
                    f"Série CHIRPS introuvable : {chirps_csv}\n"
                    "Générez-la d'abord : python data/build_bamako_chirps_daily.py"
                )
            city = pd.read_csv(chirps_csv, parse_dates=["date"])
            city = city[["date", "precipitation"]].sort_values("date").reset_index(drop=True)
            city["precipitation"] = city["precipitation"].fillna(0.0).clip(lower=0.0)
            print("📊 Série pluie Bamako-ville chargée (CHIRPS RÉEL)")
            print(f"  ✅ Fichier : {chirps_csv}")
            print(f"  📅 Période : {city['date'].min().date()} → {city['date'].max().date()}")
            print(f"  📊 Jours : {len(city)}")
            return city

        if not os.path.exists(openweather_csv):
            raise FileNotFoundError(
                f"Aucune source météo trouvée.\n"
                f"  - CHIRPS attendu : {chirps_csv} "
                "(python data/build_bamako_chirps_daily.py)\n"
                f"  - OpenWeather attendu : {openweather_csv}"
            )

        df = pd.read_csv(openweather_csv, parse_dates=["date"])

        # La pluie est identique dans les 6 communes → une valeur par date suffit.
        city = (
            df.groupby("date", as_index=False)["precipitation"]
            .mean()
            .sort_values("date")
            .reset_index(drop=True)
        )
        city["precipitation"] = city["precipitation"].fillna(0.0).clip(lower=0.0)

        print("📊 Série pluie Bamako-ville chargée (OpenWeather/Agence)")
        print(f"  ✅ Fichier : {openweather_csv}")
        print(f"  📅 Période : {city['date'].min().date()} → {city['date'].max().date()}")
        print(f"  📊 Jours : {len(city)}")
        return city

    # ------------------------------------------------------------------ #
    # 2. Features dérivées de la pluie (mêmes formules que le pipeline 29-feat)
    # ------------------------------------------------------------------ #
    def add_rainfall_features(self, df):
        """Ajoute les 5 features temporelles dérivées de la pluie."""
        print("\n⏰ Calcul des features pluie (accumulations + saturation)...")
        df = df.sort_values("date").reset_index(drop=True)
        precip = df["precipitation"].astype(float)

        df["antecedent_precip_3d"] = precip.rolling(window=3, min_periods=1).sum()
        df["antecedent_precip_7d"] = precip.rolling(window=7, min_periods=1).sum()
        df["antecedent_precip_14d"] = precip.rolling(window=14, min_periods=1).sum()
        df["soil_saturation_index"] = np.clip(
            precip.rolling(window=30, min_periods=1).sum() / 200.0, 0.0, 1.0
        )

        print(f"  ✅ Features ajoutées : {', '.join(RAINFALL_FEATURE_COLS)}")
        return df

    # ------------------------------------------------------------------ #
    # 3. Calendrier d'inondation unique pour Bamako
    # ------------------------------------------------------------------ #
    def add_flood_labels(self, df, label_mode="hybrid", threshold=20.0):
        """Marque flood_occurred=1 selon le mode de labellisation choisi.

        label_mode :
          - "known"     : uniquement les dates d'inondation documentées ;
          - "threshold" : tout jour avec pluie ≥ `threshold` mm (règle terrain :
                          au-delà de ~20 mm/j, certaines zones de Bamako sont
                          inondées) ;
          - "hybrid"    : union des deux (recommandé) — combine les événements
                          documentés et la règle physique de seuil.
        """
        print(f"\n🏷️  Labels d'inondation (mode={label_mode}, seuil={threshold} mm)...")

        # Dates documentées (union ville, toutes communes confondues).
        all_dates = set()
        for dates in self._known_floods.values():
            all_dates.update(dates)
        flood_dates = pd.to_datetime(sorted(all_dates))
        known_mask = df["date"].isin(flood_dates)

        # Règle de seuil pluviométrique.
        threshold_mask = df["precipitation"].astype(float) >= float(threshold)

        if label_mode == "known":
            label = known_mask
        elif label_mode == "threshold":
            label = threshold_mask
        elif label_mode == "hybrid":
            label = known_mask | threshold_mask
        else:
            raise ValueError(f"label_mode inconnu : {label_mode}")

        df["flood_occurred"] = label.astype(int)

        n_known = int(known_mask.sum())
        n_thr = int(threshold_mask.sum())
        n_known_in_range = int((known_mask).sum())

        # Étendre à J-1 / J+1 pour lisser (comme le pipeline existant).
        base = df["flood_occurred"].copy()
        for shift in (-1, 1):
            shifted = base.shift(shift, fill_value=0)
            df["flood_occurred"] = np.maximum(df["flood_occurred"], shifted)

        n_flood = int(df["flood_occurred"].sum())
        pct = (n_flood / len(df)) * 100 if len(df) else 0.0
        print(f"  📊 Jours ≥ {threshold} mm : {n_thr} | dates documentées présentes : {n_known_in_range}")
        print(f"  ✅ {n_flood} jours d'inondation labellisés ({pct:.2f}%) sur {len(df)} jours "
              f"(après lissage ±1j)")
        return df

    # ------------------------------------------------------------------ #
    # 4. Séquences glissantes 30 j → inondation dans les 7 j suivants
    # ------------------------------------------------------------------ #
    def create_sequences(self, df, sequence_length=LSTM_SEQUENCE_LENGTH,
                         forecast_days=LSTM_FORECAST_DAYS):
        """Séquences ANTÉCÉDENTS + PRÉVISION.

        Chaque échantillon couvre `sequence_length` jours observés suivis des
        `forecast_days` jours de l'horizon de prévision (37 pas au total). Le
        modèle voit ainsi la pluie du déclencheur. Le label = inondation sur ces
        `forecast_days` jours. À l'entraînement, la pluie CHIRPS observée tient
        lieu de « prévision parfaite » ; à l'inférence on injecte la prévision
        OpenWeather.
        """
        total_len = sequence_length + forecast_days
        print(
            f"\n📦 Création des séquences ({sequence_length} j observés + "
            f"{forecast_days} j prévus = {total_len} pas)..."
        )
        df = df.sort_values("date").reset_index(drop=True)

        X, y, metadata = [], [], []
        feature_values = df[RAINFALL_FEATURE_COLS].values.astype(np.float32)

        for i in range(len(df) - total_len + 1):
            # 30 jours observés + 7 jours de l'horizon de prévision
            sequence = feature_values[i:i + total_len]

            # Fenêtre de prévision = les 7 derniers pas de la séquence
            future = df.iloc[i + sequence_length:i + total_len]
            flood_in_future = int(future["flood_occurred"].max())

            X.append(sequence)
            y.append(1.0 if flood_in_future else 0.0)
            metadata.append(
                # end_date = jour d'émission (dernier jour observé, "aujourd'hui")
                {"end_date": df.iloc[i + sequence_length - 1]["date"].strftime("%Y-%m-%d")}
            )

        X_array = np.nan_to_num(np.array(X, dtype=np.float32))
        y_array = np.array(y, dtype=np.float32)

        n_pos = int((y_array > 0.5).sum())
        pct = (n_pos / len(y_array)) * 100 if len(y_array) else 0.0
        print(f"  ✅ {len(X_array)} séquences de {total_len} pas | positives : {n_pos} ({pct:.1f}%)")
        return X_array, y_array, metadata

    # ------------------------------------------------------------------ #
    # 5. Split chronologique (hold-out de la dernière année labellisée) + save
    # ------------------------------------------------------------------ #
    def split_and_save(self, X, y, metadata):
        """
        Forward-chaining sans fuite temporelle :
          - la traîne finale sans aucune inondation labellisée (ex. saison des
            pluies non encore renseignée) est écartée : elle rendrait la
            validation dégénérée (0 positif) et n'apporte aucun signal positif ;
          - la DERNIÈRE année contenant des inondations sert de validation ;
          - toutes les années antérieures servent d'entraînement.
        """
        years = np.array([int(m["end_date"][:4]) for m in metadata])
        y_bin = (y > 0.5).astype(int)

        years_with_pos = sorted({int(yr) for yr, pos in zip(years, y_bin) if pos})
        if not years_with_pos:
            raise ValueError("Aucune année ne contient d'inondation labellisée.")

        val_year = years_with_pos[-1]
        print(
            f"\n📐 Split chronologique : validation = {val_year}, "
            f"entraînement = années < {val_year}"
        )
        dropped = sorted({int(yr) for yr in years if int(yr) > val_year})
        if dropped:
            n_drop = int((years > val_year).sum())
            print(
                f"  ⚠️  {n_drop} séquences des années {dropped} écartées "
                "(aucune inondation labellisée — traîne non renseignée)"
            )

        train_mask = years < val_year
        val_mask = years == val_year

        splits = {
            "train": (X[train_mask], y[train_mask], _subset(metadata, train_mask)),
            "val": (X[val_mask], y[val_mask], _subset(metadata, val_mask)),
        }

        for split, (X_s, y_s, meta_s) in splits.items():
            np.save(os.path.join(self.output_dir, f"X_{split}.npy"), X_s)
            np.save(os.path.join(self.output_dir, f"y_{split}.npy"), y_s)
            with open(
                os.path.join(self.output_dir, f"metadata_{split}.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(meta_s, f, indent=2)
            n_pos = int((y_s > 0.5).sum())
            print(f"\n✅ {split} : X={X_s.shape}, positives={n_pos}")

        # Manifeste léger pour tracer les features + le split utilisés.
        with open(
            os.path.join(self.output_dir, "features.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(
                {"feature_names": RAINFALL_FEATURE_COLS, "val_year": val_year},
                f,
                indent=2,
            )


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Prépare les séquences LSTM pluie-seule (Bamako-ville)"
    )
    parser.add_argument(
        "--source",
        choices=["auto", "chirps", "openweather"],
        default="auto",
        help="Source pluie : chirps (réel), openweather, ou auto (CHIRPS si dispo)",
    )
    parser.add_argument(
        "--label-mode",
        choices=["known", "threshold", "hybrid"],
        default="hybrid",
        help="Labellisation : known (dates docs), threshold (pluie≥seuil), hybrid (union)",
    )
    parser.add_argument(
        "--flood-threshold",
        type=float,
        default=20.0,
        help="Seuil de pluie (mm/j) au-delà duquel on labellise inondation (défaut 20)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🌧️  PRÉPARATION DONNÉES — LSTM PLUIE-SEULE (BAMAKO-VILLE)")
    print("=" * 60)

    prep = BamakoRainfallOnlyPreparator()

    df = prep.load_city_rainfall(source=args.source)
    df = prep.add_rainfall_features(df)
    df = prep.add_flood_labels(df, label_mode=args.label_mode, threshold=args.flood_threshold)

    X, y, metadata = prep.create_sequences(df)
    if len(X) == 0:
        print("\n❌ Aucune séquence créée. Vérifiez la série météo.")
        return

    prep.split_and_save(X, y, metadata)

    print("\n" + "=" * 60)
    print("✅ PRÉPARATION TERMINÉE")
    print("=" * 60)
    print(f"\n📁 Données : {prep.output_dir}")
    print("\n📝 Prochaine étape :")
    print("   cd .. && python -m models.trainers.model_trainer_bamako_rainfall")


if __name__ == "__main__":
    main()
