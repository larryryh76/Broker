import math
from typing import List, Dict, Optional

class MarkovModel:
    def __init__(self, outcomes: List[str]):
        self.outcomes = outcomes
    def predict(self) -> Dict[str, float]:
        if not self.outcomes: return {"U": 0.5, "D": 0.5}
        last = self.outcomes[-1]
        trans = {"U": 0, "D": 0, "M": 0}
        for i in range(len(self.outcomes) - 1):
            if self.outcomes[i] == last:
                next_v = self.outcomes[i+1]
                if next_v in trans: trans[next_v] += 1
        total = trans["U"] + trans["D"]
        if total == 0: return {"U": 0.5, "D": 0.5}
        return {"U": trans["U"] / total, "D": trans["D"] / total}

class StreakModel:
    def __init__(self, outcomes: List[str]):
        self.outcomes = outcomes
    def predict(self) -> Dict[str, float]:
        if not self.outcomes: return {"U": 0.5, "D": 0.5}
        cur = self.outcomes[-1]
        if cur == "M": return {"U": 0.5, "D": 0.5}
        slen = 0
        for x in reversed(self.outcomes):
            if x == cur: slen += 1
            else: break
        prob = 0.5 + (0.05 * min(slen, 5))
        return {"U": prob if cur == "U" else 1 - prob, "D": prob if cur == "D" else 1 - prob}

class MeanReversionModel:
    def __init__(self, outcomes: List[str]):
        self.outcomes = outcomes
    def predict(self) -> Dict[str, float]:
        if len(self.outcomes) < 5: return {"U": 0.5, "D": 0.5}
        last5 = self.outcomes[-5:]
        if all(x == "U" for x in last5): return {"U": 0.2, "D": 0.8}
        if all(x == "D" for x in last5): return {"U": 0.8, "D": 0.2}
        return {"U": 0.5, "D": 0.5}

class BayesianBaseline:
    def __init__(self, outcomes: List[str]):
        self.outcomes = outcomes
    def predict(self) -> Dict[str, float]:
        if not self.outcomes: return {"U": 0.5, "D": 0.5}
        u, d = self.outcomes.count("U"), self.outcomes.count("D")
        total = u + d
        if total == 0: return {"U": 0.5, "D": 0.5}
        return {"U": u / total, "D": d / total}

class EnsembleBrain:
    def __init__(self, initial_weights: Optional[Dict] = None):
        self.weights = initial_weights or {"markov": 1.0, "streak": 1.0, "reversion": 1.0, "bayesian": 1.0}
        self.lr = 0.01
    def _softmax(self, w: Dict[str, float]) -> Dict[str, float]:
        exps = {k: math.exp(v) for k, v in w.items()}
        total = sum(exps.values())
        return {k: v / total for k, v in exps.items()}
    def predict(self, outcomes: List[str]) -> Dict[str, float]:
        mods = {
            "markov": MarkovModel(outcomes).predict(),
            "streak": StreakModel(outcomes).predict(),
            "reversion": MeanReversionModel(outcomes).predict(),
            "bayesian": BayesianBaseline(outcomes).predict()
        }
        nw = self._softmax(self.weights)
        res = {"U": 0.0, "D": 0.0}
        for name, weight in nw.items():
            res["U"] += weight * mods[name]["U"]
            res["D"] += weight * mods[name]["D"]
        return res
    def update_weights(self, outcomes: List[str], actual: str):
        if not outcomes or actual == "M": return
        prev = {
            "markov": MarkovModel(outcomes).predict(),
            "streak": StreakModel(outcomes).predict(),
            "reversion": MeanReversionModel(outcomes).predict(),
            "bayesian": BayesianBaseline(outcomes).predict()
        }
        for n in self.weights:
            reward = (prev[n][actual] - 0.5) * 2.0
            self.weights[n] = max(min(self.weights[n] + self.lr * reward, 10), -10)
