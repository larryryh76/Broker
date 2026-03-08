import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
import config

class AIModel:
    def __init__(self, model_name="forex_ai_model"):
        self.model_path = os.path.join(config.MODEL_DIR, f"{model_name}.pkl")
        self.model = self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            return joblib.load(self.model_path)
        return RandomForestClassifier(n_estimators=100, random_state=42)

    def prepare_features(self, df):
        # Assuming df has technical indicators already calculated
        # We'll use a subset of columns as features
        feature_cols = [col for col in df.columns if col not in ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume', 'target']]
        X = df[feature_cols].dropna()
        return X

    def train(self, df):
        # Simple target: 1 if close price in next period is higher, else 0
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)

        X = self.prepare_features(df)
        y = df['target'].loc[X.index]

        if len(X) < 100:
            print("Not enough data to train AI model")
            return

        self.model.fit(X, y)
        joblib.dump(self.model, self.model_path)
        print(f"Model trained and saved to {self.model_path}")

    def predict(self, df):
        X = self.prepare_features(df).tail(1)
        if X.empty:
            return 0.5, 0.5 # Neutral

        probs = self.model.predict_proba(X)[0]
        # Probs: [prob_of_0, prob_of_1]
        bearish_prob = probs[0]
        bullish_prob = probs[1]

        return bullish_prob, bearish_prob
