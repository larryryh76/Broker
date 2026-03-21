import random
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
        return {"U": 0.6 if current_streak == "U" else 0.4, "D": 0.6 if current_streak == "D" else 0.4}

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

class RandomControl:
    def predict(self) -> Dict[str, float]:
        return {"U": 0.5, "D": 0.5}

class EnsembleBrain:
    def __init__(self, initial_weights: Optional[Dict] = None):
        self.weights = initial_weights or {
            "markov": 0.25,
            "streak": 0.25,
            "reversion": 0.25,
            "bayesian": 0.20,
            "random": 0.05
        }

    def predict(self, outcomes: List[str]) -> Dict[str, float]:
        models = {
            "markov": MarkovModel(outcomes).predict(),
            "streak": StreakModel(outcomes).predict(),
            "reversion": MeanReversionModel(outcomes).predict(),
            "bayesian": BayesianBaseline(outcomes).predict(),
            "random": RandomControl().predict()
        }

        final_prob = {"U": 0.0, "D": 0.0}
        for name, weight in self.weights.items():
            final_prob["U"] += weight * models[name]["U"]
            final_prob["D"] += weight * models[name]["D"]

        return final_prob

    def update_weights(self, outcomes: List[str], actual_outcome: str):
        """Simple adaptive weighting (reward correctness)."""
        lr = 0.05 # learning rate
        performance = {
            "markov": 1.0 if MarkovModel(outcomes[:-1]).predict()[actual_outcome] > 0.5 else 0.0,
            "streak": 1.0 if StreakModel(outcomes[:-1]).predict()[actual_outcome] > 0.5 else 0.0,
            "reversion": 1.0 if MeanReversionModel(outcomes[:-1]).predict()[actual_outcome] > 0.5 else 0.0,
            "bayesian": 1.0 if BayesianBaseline(outcomes[:-1]).predict()[actual_outcome] > 0.5 else 0.0,
            "random": 0.5 # random model neutral
        }

        # Update and normalize
        for name in self.weights:
            self.weights[name] = self.weights[name] * (1 - lr) + lr * performance[name]

        total = sum(self.weights.values())
        for name in self.weights:
            self.weights[name] /= total
