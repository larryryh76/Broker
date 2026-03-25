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

        # V3.1 Fixed KeyError: Support U, D, and M (Middle)
        transitions = {"U": 0, "D": 0, "M": 0}
        for i in range(len(self.outcomes) - 1):
            if self.outcomes[i] == last_move:
                next_val = self.outcomes[i+1]
                if next_val in transitions:
                    transitions[next_val] += 1

        total = sum(transitions.values())
        if total == 0: return {"U": 0.5, "D": 0.5}
        # We only bet on U/D, so we normalize those
        ud_total = transitions["U"] + transitions["D"]
        if ud_total == 0: return {"U": 0.5, "D": 0.5}

        return {"U": transitions["U"] / ud_total, "D": transitions["D"] / ud_total}

class StreakModel:
    def __init__(self, outcomes: List[str]):
        self.outcomes = outcomes

    def predict(self) -> Dict[str, float]:
        """Streak continuation logic."""
        if not self.outcomes: return {"U": 0.5, "D": 0.5}
        current_streak = self.outcomes[-1]
        if current_streak == "M": return {"U": 0.5, "D": 0.5}

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
        """Bet against long streaks."""
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
        # Only count U/D for betting baseline
        u_count = self.outcomes.count("U")
        d_count = self.outcomes.count("D")
        total = u_count + d_count
        if total == 0: return {"U": 0.5, "D": 0.5}
        return {"U": u_count / total, "D": d_count / total}

class EnsembleBrain:
    def __init__(self, initial_weights: Optional[Dict] = None):
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

        normalized_weights = self._softmax(self.weights)
        final_prob = {"U": 0.0, "D": 0.0}
        for name, weight in normalized_weights.items():
            final_prob["U"] += weight * models[name]["U"]
            final_prob["D"] += weight * models[name]["D"]

        return final_prob

    def update_weights(self, outcomes: List[str], actual_outcome: str):
        if not outcomes or actual_outcome == "M": return

        lr = 0.1
        models_prev = {
            "markov": MarkovModel(outcomes).predict(),
            "streak": StreakModel(outcomes).predict(),
            "reversion": MeanReversionModel(outcomes).predict(),
            "bayesian": BayesianBaseline(outcomes).predict()
        }

        for name in self.weights:
            prob_correct = models_prev[name][actual_outcome]
            reward = (prob_correct - 0.5) * 2.0
            self.weights[name] += lr * reward
            self.weights[name] = max(min(self.weights[name], 10), -10)
