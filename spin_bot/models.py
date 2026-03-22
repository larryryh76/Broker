import random
import math
from typing import List, Dict, Optional

class MarkovModel:
    def __init__(self, outcomes: List[str]):
        self.outcomes = outcomes

    def predict(self) -> Dict[str, float]:
        """Calculates probabilities based on the last outcome's history."""
        if not self.outcomes: return {"U": 0.5, "D": 0.5}
        last_move = self.outcomes[-1]

        transitions = {"U": 0, "D": 0}
        for i in range(len(self.outcomes) - 1):
            if self.outcomes[i] == last_move:
                transitions[self.outcomes[i+1]] += 1

        total = sum(transitions.values())
        if total == 0: return {"U": 0.5, "D": 0.5}
        return {"U": transitions["U"] / total, "D": transitions["D"] / total}

class StreakModel:
    def __init__(self, outcomes: List[str]):
        self.outcomes = outcomes

    def predict(self) -> Dict[str, float]:
        """Streak continuation logic: Bet in the direction of the current streak."""
        if not self.outcomes: return {"U": 0.5, "D": 0.5}
        current_streak = self.outcomes[-1]

        streak_len = 0
        for x in reversed(self.outcomes):
            if x == current_streak: streak_len += 1
            else: break

        prob = 0.5 + (0.05 * min(streak_len, 5))
        return {
            "U": prob if current_streak == "U" else 1 - prob,
            "D": prob if current_streak == "D" else 1 - prob
        }

class MeanReversionModel:
    def __init__(self, outcomes: List[str]):
        self.outcomes = outcomes

    def predict(self) -> Dict[str, float]:
        """Bet against long streaks (e.g., 5 counts)."""
        if len(self.outcomes) < 5: return {"U": 0.5, "D": 0.5}
        last_5 = self.outcomes[-5:]
        if all(x == "U" for x in last_5): return {"U": 0.2, "D": 0.8}
        if all(x == "D" for x in last_5): return {"U": 0.8, "D": 0.2}
        return {"U": 0.5, "D": 0.5}

class BayesianBaseline:
    def __init__(self, outcomes: List[str]):
        self.outcomes = outcomes

    def predict(self) -> Dict[str, float]:
        """Global frequency model."""
        if not self.outcomes: return {"U": 0.5, "D": 0.5}
        total = len(self.outcomes)
        u_count = self.outcomes.count("U")
        return {"U": u_count / total, "D": (total - u_count) / total}

class EnsembleBrain:
    def __init__(self, initial_weights: Optional[Dict] = None):
        # Softmax Weighting initialized
        self.weights = initial_weights or {
            "markov": 1.0,
            "streak": 1.0,
            "reversion": 1.0,
            "bayesian": 1.0
        }

    def _softmax(self, weights: Dict[str, float]) -> Dict[str, float]:
        exp_weights = {k: math.exp(v) for k, v in weights.items()}
        total = sum(exp_weights.values())
        return {k: v / total for k, v in exp_weights.items()}

    def predict(self, outcomes: List[str]) -> Dict[str, float]:
        models = {
            "markov": MarkovModel(outcomes).predict(),
            "streak": StreakModel(outcomes).predict(),
            "reversion": MeanReversionModel(outcomes).predict(),
            "bayesian": BayesianBaseline(outcomes).predict()
        }

        # Apply Softmax to weights for final contribution
        normalized_weights = self._softmax(self.weights)

        final_prob = {"U": 0.0, "D": 0.0}
        for name, weight in normalized_weights.items():
            final_prob["U"] += weight * models[name]["U"]
            final_prob["D"] += weight * models[name]["D"]

        return final_prob

    def update_weights(self, outcomes: List[str], actual_outcome: str):
        """Reward correct models and penalize incorrect ones."""
        # 'outcomes' is the history BEFORE the current 'actual_outcome'
        if not outcomes: return

        lr = 0.1 # Learning rate
        models_prev = {
            "markov": MarkovModel(outcomes).predict(),
            "streak": StreakModel(outcomes).predict(),
            "reversion": MeanReversionModel(outcomes).predict(),
            "bayesian": BayesianBaseline(outcomes).predict()
        }

        for name in self.weights:
            # Score based on confidence in the correct direction
            prob_correct = models_prev[name][actual_outcome]
            reward = (prob_correct - 0.5) * 2.0 # Range -1 to 1
            self.weights[name] += lr * reward

            # Prevent weights from growing indefinitely
            self.weights[name] = max(min(self.weights[name], 10), -10)

        print(f"Updated Model Weights: {self.weights}")
