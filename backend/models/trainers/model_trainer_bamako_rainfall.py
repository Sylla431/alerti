"""
Entraînement + évaluation — LSTM Bamako PLUVIOMÉTRIE SEULE.

Entraîne LSTMPredictorBamakoRainfall sur les séquences générées par
data/prepare_bamako_rainfall_only.py, l'évalue avec des métriques adaptées à
l'imbalance (ROC-AUC, PR-AUC, F1) et propose une comparaison directe avec les
métriques du modèle 29 features existant (si fournies) pour vérifier
empiriquement l'apport réel des features statiques.
"""
import json
import os
import sys

import numpy as np

# backend/ (models/trainers/ -> models/ -> backend/)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from models.predictors.lstm_model_bamako_rainfall import LSTMPredictorBamakoRainfall

# Métriques connues du modèle 29 features (à compléter si un run de référence
# existe). None => la comparaison est simplement omise.
REFERENCE_29FEAT_METRICS = {
    "roc_auc": None,
    "pr_auc": None,
    "f1": None,
}


def load_rainfall_data():
    """Charge les séquences pluie-seule préparées."""
    data_dir = os.path.join(
        BACKEND_DIR, "data", "training", "bamako_rainfall_only",
    )
    print("📂 Chargement des données pluie-seule...")

    required = ["X_train.npy", "y_train.npy", "X_val.npy", "y_val.npy"]
    for filename in required:
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Fichier manquant : {filepath}")

    X_train = np.load(os.path.join(data_dir, "X_train.npy"))
    y_train = np.load(os.path.join(data_dir, "y_train.npy"))
    X_val = np.load(os.path.join(data_dir, "X_val.npy"))
    y_val = np.load(os.path.join(data_dir, "y_val.npy"))

    print(f"  ✅ Train : {X_train.shape} | positives : {int((y_train > 0.5).sum())}")
    print(f"  ✅ Val   : {X_val.shape} | positives : {int((y_val > 0.5).sum())}")
    return X_train, y_train, X_val, y_val


def train_rainfall_model(use_smote=True, use_class_weights=True):
    print("\n" + "=" * 60)
    print("🌧️  ENTRAÎNEMENT — LSTM PLUIE-SEULE (BAMAKO-VILLE)")
    print("=" * 60)

    X_train, y_train, X_val, y_val = load_rainfall_data()

    if use_smote:
        print("\n🔄 Rééquilibrage SMOTE...")
        try:
            from imblearn.over_sampling import SMOTE

            X_train_2d = X_train.reshape(X_train.shape[0], -1)
            y_binary = (y_train > 0.5).astype(int)
            n_pos = int(y_binary.sum())

            if n_pos > 1:
                k_neighbors = min(5, n_pos - 1)
                smote = SMOTE(random_state=42, k_neighbors=k_neighbors)
                X_bal, y_bal = smote.fit_resample(X_train_2d, y_binary)
                X_train = X_bal.reshape(-1, X_train.shape[1], X_train.shape[2])
                y_train = y_bal.astype(np.float32)
                print(
                    f"   Après SMOTE : {X_train.shape[0]} séquences "
                    f"({int((y_train > 0.5).sum())} positives)"
                )
            else:
                print("   ⚠️  Pas assez de positifs pour SMOTE")
        except ImportError:
            print("   ⚠️  imbalanced-learn non installé, SMOTE désactivé")
        except Exception as e:
            print(f"   ⚠️  Erreur SMOTE : {e}")

    n_features = X_train.shape[2]
    print(f"\n🔧 Création du modèle ({n_features} features pluie)...")
    model = LSTMPredictorBamakoRainfall(n_features=n_features)

    print("\n🚀 Entraînement...")
    history = model.train(
        X_train, y_train, X_val, y_val,
        epochs=100, batch_size=32, use_class_weights=use_class_weights,
    )
    print("\n✅ Entraînement terminé !")
    return model, history


def evaluate_model(X_val, y_val, model):
    print("\n" + "=" * 60)
    print("📊 ÉVALUATION")
    print("=" * 60)

    from sklearn.metrics import (
        average_precision_score,
        classification_report,
        confusion_matrix,
        f1_score,
        precision_recall_curve,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    y_pred = model.predict(X_val)
    y_binary = (y_val > 0.5).astype(int)

    if len(np.unique(y_binary)) < 2:
        print("⚠️  Une seule classe dans la validation, métriques limitées.")
        roc_auc = pr_auc = f1 = precision = recall = float("nan")
    else:
        roc_auc = roc_auc_score(y_binary, y_pred)
        pr_auc = average_precision_score(y_binary, y_pred)

        y_pred_binary = (y_pred > 0.5).astype(int)
        precision = precision_score(y_binary, y_pred_binary, zero_division=0)
        recall = recall_score(y_binary, y_pred_binary, zero_division=0)
        f1 = f1_score(y_binary, y_pred_binary, zero_division=0)

        prec_c, rec_c, thr_c = precision_recall_curve(y_binary, y_pred)
        f1_curve = 2 * (prec_c * rec_c) / (prec_c + rec_c + 1e-10)
        opt_idx = int(np.argmax(f1_curve))
        opt_thr = thr_c[opt_idx] if len(thr_c) > 0 else 0.5

        print(f"\n🎯 MÉTRIQUES ADAPTÉES À L'IMBALANCE :")
        print(f"   ROC-AUC : {roc_auc:.4f} (idéal > 0.8)")
        print(f"   PR-AUC  : {pr_auc:.4f} (idéal > 0.5)")
        print(f"   F1 (seuil=0.5)        : {f1:.4f}")
        print(f"   F1 optimal (seuil={opt_thr:.3f}) : {f1_curve[opt_idx]:.4f}")
        print(f"   Precision : {precision:.4f}")
        print(f"   Recall    : {recall:.4f}")

        cm = confusion_matrix(y_binary, y_pred_binary)
        print(f"\n📊 Matrice de confusion :")
        print(f"   TN={cm[0, 0]}  FP={cm[0, 1]}")
        print(f"   FN={cm[1, 0]}  TP={cm[1, 1]}")

        print(f"\n📋 Rapport de classification :")
        print(
            classification_report(
                y_binary, y_pred_binary,
                target_names=["Pas d'inondation", "Inondation"],
                zero_division=0,
            )
        )

    _compare_with_reference(roc_auc, pr_auc, f1)
    return {"roc_auc": roc_auc, "pr_auc": pr_auc, "f1": f1,
            "precision": precision, "recall": recall}


def _compare_with_reference(roc_auc, pr_auc, f1):
    """Comparaison directe avec le modèle 29 features (si métriques connues)."""
    ref = REFERENCE_29FEAT_METRICS
    if not any(v is not None for v in ref.values()):
        print("\nℹ️  Comparaison 29-features : aucune métrique de référence fournie.")
        print("   Renseignez REFERENCE_29FEAT_METRICS pour activer la comparaison.")
        return

    print("\n" + "=" * 60)
    print("🔬 COMPARAISON : pluie-seule (5 feat) vs modèle 29 features")
    print("=" * 60)
    rows = [
        ("ROC-AUC", roc_auc, ref.get("roc_auc")),
        ("PR-AUC", pr_auc, ref.get("pr_auc")),
        ("F1", f1, ref.get("f1")),
    ]
    print(f"   {'Métrique':10s} {'Pluie-seule':>14s} {'29 features':>14s} {'Δ':>10s}")
    for name, rain, refv in rows:
        if refv is None:
            print(f"   {name:10s} {rain:14.4f} {'n/a':>14s} {'n/a':>10s}")
        else:
            print(f"   {name:10s} {rain:14.4f} {refv:14.4f} {rain - refv:+10.4f}")
    print(
        "\n💡 Si Δ ≈ 0, les 24 features supplémentaires (statiques + météo) "
        "n'apportent quasiment rien avec les données actuelles."
    )


def main():
    print("=" * 60)
    print("🎓 PIPELINE LSTM PLUIE-SEULE — BAMAKO")
    print("=" * 60)

    try:
        model, _ = train_rainfall_model(use_smote=True, use_class_weights=True)
        _, _, X_val, y_val = load_rainfall_data()
        metrics = evaluate_model(X_val, y_val, model)

        # Sauvegarde des métriques pour réutilisation.
        out = os.path.join(
            BACKEND_DIR, "data", "training", "bamako_rainfall_only", "metrics.json",
        )
        with open(out, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print("\n" + "=" * 60)
        print("✅ TERMINÉ")
        print("=" * 60)
        print(f"\n📝 Modèle : {model.model_path}")
        print(f"📝 Scaler : {model.scaler_path}")
        print(f"📝 Métriques : {out}")

    except FileNotFoundError as e:
        print(f"\n❌ Données manquantes : {e}")
        print("\n📝 Lancez d'abord :")
        print("   cd backend/data && python prepare_bamako_rainfall_only.py")
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
