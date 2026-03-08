import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
import io
import config

class AIModel:
    def __init__(self, db_client=None, model_name="forex_ai_model"):
        self.db = db_client
        self.model_name = model_name
        self.model_path = os.path.join(config.MODEL_DIR, f"{model_name}.pkl")
        self._is_trained = False
        self.model = self._load_model()

    @property
    def is_trained(self):
        return self._is_trained

    def _load_model(self):
        # 1. Try loading from MongoDB first
        if self.db is not None:
            model_bytes = self.db.load_model(self.model_name)
            if model_bytes:
                print(f"Loading AI Model from MongoDB: {self.model_name}")
                self._is_trained = True
                return joblib.load(io.BytesIO(model_bytes))

        # 2. Try loading from local file
        if os.path.exists(self.model_path):
            print(f"Loading AI Model from Local: {self.model_path}")
            self._is_trained = True
            return joblib.load(self.model_path)

        print("Initializing new AI Model")
        self._is_trained = False
        return RandomForestClassifier(n_estimators=100, random_state=42)

    def prepare_features(self, df):
        feature_cols = []
        # Basic indicators
        for col in ['RSI', 'SMA_FAST', 'SMA_SLOW', 'ATR']:
            if col in df.columns: feature_cols.append(col)

        # Exclude metadata
        X = df[feature_cols].dropna()
        return X

    def train(self, df):
        if df is None or len(df) < 100:
            print("Not enough data to train AI model")
            return

        # 1. Generate target: 1 if close price shifted up
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)

        X = self.prepare_features(df)
        y = df['target'].loc[X.index]

        if len(X) < 100:
            print("Not enough valid feature samples to train")
            return

        print(f"Training AI Model on {len(X)} samples...")
        self.model.fit(X, y)
        self._is_trained = True

        # Save locally
        if not os.path.exists(config.MODEL_DIR): os.makedirs(config.MODEL_DIR)
        joblib.dump(self.model, self.model_path)

        # Save to MongoDB for CI persistence
        if self.db is not None:
            buffer = io.BytesIO()
            joblib.dump(self.model, buffer)
            self.db.save_model(self.model_name, buffer.getvalue())
            print(f"AI Model synced to MongoDB.")

    def predict(self, df):
        if not self._is_trained:
            return 0.5, 0.5

        X = self.prepare_features(df).tail(1)
        if X.empty:
            return 0.5, 0.5

        try:
            probs = self.model.predict_proba(X)[0]
            if len(probs) == 1:
                val = self.model.predict(X)[0]
                return (1.0, 0.0) if val == 1 else (0.0, 1.0)
            return probs[1], probs[0]
        except Exception as e:
            print(f"Prediction error: {e}")
            return 0.5, 0.5
