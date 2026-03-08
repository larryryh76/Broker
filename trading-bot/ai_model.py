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
        self.model = self._load_model()

    def _load_model(self):
        # 1. Try loading from MongoDB first
        if self.db:
            model_bytes = self.db.load_model(self.model_name)
            if model_bytes:
                print(f"Loading AI Model from MongoDB: {self.model_name}")
                return joblib.load(io.BytesIO(model_bytes))

        # 2. Try loading from local file
        if os.path.exists(self.model_path):
            print(f"Loading AI Model from Local: {self.model_path}")
            return joblib.load(self.model_path)

        print("Initializing new AI Model")
        return RandomForestClassifier(n_estimators=100, random_state=42)

    def prepare_features(self, df):
        feature_cols = [col for col in df.columns if col not in ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume', 'target', 'RSI', 'SMA_FAST', 'SMA_SLOW', 'BB_UPPER', 'BB_LOWER', 'ATR']]
        # Use simple indicators if present
        for col in ['RSI', 'SMA_FAST', 'SMA_SLOW', 'ATR']:
            if col in df.columns: feature_cols.append(col)

        X = df[feature_cols].dropna()
        return X

    def train(self, df):
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        X = self.prepare_features(df)
        y = df['target'].loc[X.index]

        if len(X) < 100:
            print("Not enough data to train AI model")
            return

        self.model.fit(X, y)

        # Save locally
        if not os.path.exists(config.MODEL_DIR): os.makedirs(config.MODEL_DIR)
        joblib.dump(self.model, self.model_path)

        # Save to MongoDB
        if self.db:
            buffer = io.BytesIO()
            joblib.dump(self.model, buffer)
            self.db.save_model(self.model_name, buffer.getvalue())
            print(f"AI Model trained and synced to MongoDB.")

    def predict(self, df):
        X = self.prepare_features(df).tail(1)
        if X.empty:
            return 0.5, 0.5

        try:
            probs = self.model.predict_proba(X)[0]
            # Handle single class models
            if len(probs) == 1:
                val = self.model.predict(X)[0]
                return (1.0, 0.0) if val == 1 else (0.0, 1.0)
            return probs[1], probs[0]
        except:
            return 0.5, 0.5
