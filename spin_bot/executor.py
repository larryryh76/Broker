from typing import List, Dict
from spin_bot.models import EnsembleBrain
from spin_bot.risk import RiskEngine

class DecisionExecutor:
    def __init__(self, brain: EnsembleBrain, risk: RiskEngine):
        self.brain = brain
        self.risk = risk

    def decide(self, outcomes: List[str]) -> Dict:
        probs = self.brain.predict(outcomes)
        conf_u = abs(probs["U"] - 0.5) * 2.0
        conf_d = abs(probs["D"] - 0.5) * 2.0

        # Simple EV: P(win) * 0.95 - P(loss)
        ev_u = probs["U"] * 0.95 - (1 - probs["U"])
        ev_d = probs["D"] * 0.95 - (1 - probs["D"])

        if ev_u > ev_d and ev_u > 0.05:
            return {"action": "BET", "direction": "U", "amount": self.risk.calculate_stake(conf_u, ev_u), "ev": ev_u}
        elif ev_d > ev_u and ev_d > 0.05:
            return {"action": "BET", "direction": "D", "amount": self.risk.calculate_stake(conf_d, ev_d), "ev": ev_d}

        return {"action": "SKIP", "ev": max(ev_u, ev_d)}
