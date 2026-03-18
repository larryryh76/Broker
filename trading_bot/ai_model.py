import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
import joblib
import os
import io
from trading_bot import config

class AIModel:
    def __init__(self, db_client=None, model_name="forex_ai_machine"):
        self.db = db_client
        self.model_name = model_name
        self.model_path = os.path.join(config.MODEL_DIR, f"{model_name}.pkl")
        self._is_trained = False
        self.model = self._load_model()

    @property
    def is_trained(self):
        return self._is_trained

    def _load_model(self):
        if self.db is not None:
            model_bytes = self.db.load_model(self.model_name)
            if model_bytes:
                print(f"Loading AI Machine from MongoDB: {self.model_name}")
                self._is_trained = True
                return joblib.load(io.BytesIO(model_bytes))

        if os.path.exists(self.model_path):
            print(f"Loading AI Machine from Local: {self.model_path}")
            self._is_trained = True
            return joblib.load(self.model_path)

        print("Initializing new AI Machine (Gradient Boosting)")
        self._is_trained = False
        return GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, max_depth=5, random_state=42)

    def prepare_features(self, df):
        df = df.copy()
        df['ROC'] = df['close'].pct_change(periods=5)
        df['STD'] = df['close'].rolling(window=20).std()
        df['MA_DIFF'] = (df['SMA_FAST'] - df['SMA_SLOW']) / df['SMA_SLOW']
        df['DIST_SMA'] = (df['close'] - df['SMA_SLOW']) / df['SMA_SLOW']

        feature_cols = ['RSI', 'MA_DIFF', 'DIST_SMA', 'ROC', 'STD', 'ATR']
        X = df[feature_cols].dropna()
        return X

    def train(self, df):
        if df is None or len(df) < 500:
            print("Not enough data to train AI machine")
            return

        df['target'] = (df['close'].shift(-3) > df['close']).astype(int)
        X = self.prepare_features(df)
        y = df['target'].loc[X.index]

        if len(X) < 400: return

        print(f"Training AI Machine on {len(X)} samples...")
        self.model.fit(X, y)
        self._is_trained = True

        if not os.path.exists(config.MODEL_DIR): os.makedirs(config.MODEL_DIR)
        joblib.dump(self.model, self.model_path)

        if self.db is not None:
            buffer = io.BytesIO()
            joblib.dump(self.model, buffer)
            self.db.save_model(self.model_name, buffer.getvalue())

    def predict(self, df):
        if not self._is_trained: return 0.5, 0.5
        X = self.prepare_features(df).tail(1)
        if X.empty: return 0.5, 0.5

        try:
            probs = self.model.predict_proba(X)[0]
            return probs[1], probs[0]
        except Exception:
            return 0.5, 0.5
