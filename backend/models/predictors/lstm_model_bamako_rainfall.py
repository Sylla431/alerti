"""
LSTM Bamako — variante PLUVIOMÉTRIE SEULE.

Réseau plus léger que LSTMPredictorBamako (5 features au lieu de 29), pensé pour
un signal de risque RÉGIONAL (Bamako-ville) fondé uniquement sur la dynamique de
la pluie. Utilise des fichiers modèle/scaler dédiés pour ne jamais écraser le
modèle 29 features existant.
"""
import os
import sys

import joblib
import keras
import numpy as np
import tensorflow as tf
from keras import layers, models
from sklearn.preprocessing import MinMaxScaler

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.config import LSTM_FORECAST_DAYS, LSTM_SEQUENCE_LENGTH, MODEL_DIR

RAINFALL_FEATURE_COLS = [
    "precipitation",
    "antecedent_precip_3d",
    "antecedent_precip_7d",
    "antecedent_precip_14d",
    "soil_saturation_index",
]


def _focal_loss(gamma=2.0, alpha=0.25):
    """Focal Loss pour données déséquilibrées (identique au pipeline 29-feat)."""
    def focal_loss_fixed(y_true, y_pred):
        epsilon = tf.keras.backend.epsilon()
        y_pred = tf.clip_by_value(y_pred, epsilon, 1 - epsilon)
        p_t = y_true * y_pred + (1 - y_true) * (1 - y_pred)
        alpha_factor = tf.ones_like(y_true) * alpha
        alpha_t = y_true * alpha_factor + (1 - y_true) * (1 - alpha_factor)
        cross_entropy = -tf.keras.backend.log(p_t)
        weight = alpha_t * tf.pow((1 - p_t), gamma)
        loss = weight * cross_entropy
        return tf.reduce_mean(tf.reduce_sum(loss, axis=1))

    return focal_loss_fixed


class LSTMPredictorBamakoRainfall:
    """LSTM léger pluie-seule pour un risque d'inondation régional à Bamako."""

    def __init__(self, model_path=None, n_features=None):
        os.makedirs(MODEL_DIR, exist_ok=True)
        if model_path is None:
            model_path = os.path.join(MODEL_DIR, "lstm_model_bamako_rainfall.h5")

        self.model_path = model_path
        self.scaler_path = os.path.join(MODEL_DIR, "lstm_scaler_bamako_rainfall.pkl")
        self.scaler = MinMaxScaler()
        self.model = None
        self.sequence_length = LSTM_SEQUENCE_LENGTH
        self.forecast_days = LSTM_FORECAST_DAYS
        # Longueur d'entrée = 30 jours observés + 7 jours de prévision de pluie.
        # Le modèle voit ainsi le déclencheur (pluie annoncée) et pas seulement
        # les antécédents. Adapté automatiquement aux données à l'entraînement.
        self.input_length = LSTM_SEQUENCE_LENGTH + LSTM_FORECAST_DAYS

        self.feature_names = list(RAINFALL_FEATURE_COLS)
        if n_features is not None:
            self.feature_names = self.feature_names[:n_features]

        self.load_or_create_model()

    def load_or_create_model(self):
        """Charge un modèle existant, sinon en crée un nouveau."""
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            try:
                self.model = keras.models.load_model(self.model_path, compile=False)
                self.scaler = joblib.load(self.scaler_path)
                self._compile_model()
                print(
                    f"LSTM pluie-seule chargé ({len(self.feature_names)} features)"
                )
            except Exception as e:
                print(f"Erreur chargement modèle : {e}. Création d'un nouveau modèle...")
                self._create_model()
        else:
            print("Création d'un nouveau modèle LSTM pluie-seule...")
            self._create_model()

    def _create_model(self):
        """Réseau réduit : 2 couches Bi-LSTM (64→32) + Dense, sortie sigmoid."""
        input_shape = (self.input_length, len(self.feature_names))
        inputs = keras.Input(shape=input_shape)

        lstm1 = layers.Bidirectional(
            layers.LSTM(64, return_sequences=True, dropout=0.2)
        )(inputs)
        lstm2 = layers.Bidirectional(
            layers.LSTM(32, return_sequences=False, dropout=0.2)
        )(lstm1)

        dense1 = layers.Dense(32, activation="relu")(lstm2)
        dropout1 = layers.Dropout(0.3)(dense1)
        dense2 = layers.Dense(16, activation="relu")(dropout1)

        outputs = layers.Dense(1, activation="sigmoid")(dense2)

        self.model = models.Model(inputs=inputs, outputs=outputs)
        self._compile_model()
        print(
            f"LSTM pluie-seule créé ({len(self.feature_names)} features, "
            f"{self.model.count_params()} paramètres)"
        )

    def _compile_model(self, use_focal_loss=True):
        loss_fn = _focal_loss(gamma=2.0, alpha=0.25) if use_focal_loss else "binary_crossentropy"
        self.model.compile(
            optimizer="adam",
            loss=loss_fn,
            metrics=[
                "mae",
                keras.metrics.Precision(name="precision"),
                keras.metrics.Recall(name="recall"),
                keras.metrics.AUC(name="auc"),
            ],
        )

    def train(self, X_train, y_train, X_val=None, y_val=None, epochs=100,
              batch_size=32, use_class_weights=True):
        """Entraîne le modèle avec class weights pour gérer le déséquilibre."""
        if self.model is None:
            self._create_model()

        actual_length = X_train.shape[1]
        actual_features = X_train.shape[2]

        # Forme réelle du modèle courant (peut avoir été chargé depuis un ancien
        # artefact 30 pas) : on la compare aux données pour décider d'un rebuild.
        model_length = model_features = None
        if self.model is not None:
            try:
                _, model_length, model_features = self.model.input_shape
            except (ValueError, TypeError):
                model_length = model_features = None

        needs_rebuild = False
        if len(self.feature_names) != actual_features or model_features != actual_features:
            print(
                f"⚠️  Ajustement : {actual_features} features dans les données, "
                f"{len(self.feature_names)} attendues"
            )
            self.feature_names = [f"feature_{i}" for i in range(actual_features)]
            needs_rebuild = True
        if self.input_length != actual_length or model_length != actual_length:
            print(
                f"⚠️  Ajustement : longueur d'entrée {actual_length} pas "
                f"(30 observés + prévision), modèle courant={model_length}"
            )
            self.input_length = actual_length
            needs_rebuild = True
        if needs_rebuild:
            self._create_model()

        class_weights = None
        if use_class_weights:
            from sklearn.utils.class_weight import compute_class_weight

            y_binary = (y_train > 0.5).astype(int)
            classes = np.unique(y_binary)
            if len(classes) == 2:
                weights = compute_class_weight("balanced", classes=classes, y=y_binary)
                class_weights = {0: float(weights[0]), 1: float(weights[1])}
                print(f"\n⚖️  Class weights : {class_weights}")
            else:
                print("  ⚠️  Une seule classe présente, class weights désactivés")

        X_train_reshaped = X_train.reshape(-1, X_train.shape[-1])
        self.scaler.fit(X_train_reshaped)
        X_train_scaled = self.scaler.transform(X_train_reshaped).reshape(X_train.shape)

        validation_data = None
        if X_val is not None:
            X_val_scaled = self.scaler.transform(
                X_val.reshape(-1, X_val.shape[-1])
            ).reshape(X_val.shape)
            validation_data = (X_val_scaled, y_val)

        monitor = "val_auc" if X_val is not None else "auc"
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor=monitor, patience=20, restore_best_weights=True, mode="max"
            ),
            keras.callbacks.ModelCheckpoint(
                self.model_path, save_best_only=True, monitor=monitor, mode="max"
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss" if X_val is not None else "loss",
                factor=0.5,
                patience=7,
                min_lr=1e-7,
            ),
        ]

        history = self.model.fit(
            X_train_scaled,
            y_train,
            validation_data=validation_data,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            class_weight=class_weights,
            verbose=1,
        )

        joblib.dump(self.scaler, self.scaler_path)
        return history

    def predict(self, X):
        if self.model is None:
            raise ValueError("Modèle non chargé ou non créé")
        X_scaled = self.scaler.transform(X.reshape(-1, X.shape[-1])).reshape(X.shape)
        return self.model.predict(X_scaled, verbose=0).flatten()

    def _get_risk_level(self, probability):
        if probability >= 0.8:
            return "critical"
        elif probability >= 0.6:
            return "high"
        elif probability >= 0.4:
            return "medium"
        elif probability >= 0.2:
            return "low"
        return "none"
