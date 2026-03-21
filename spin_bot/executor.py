from typing import List, Dict, Optional
from spin_bot.models import EnsembleBrain
from spin_bot.risk import RiskEngine

class DecisionExecutor:
    def __init__(self, brain: EnsembleBrain, risk_engine: RiskEngine):
        self.brain = brain
        self.risk = risk_engine

    def compute_edge(self, win_prob: float, stake: float) -> float:
        """EV = (P_win × payout) - (P_loss × stake)"""
        payout = stake * 1.95 # Assume 1.95x payout for 'Spin da Bottle'
        p_loss = 1.0 - win_prob
        return (win_prob * payout) - (p_loss * stake)

    def decide(self, outcomes: List[str]) -> Optional[Dict]:
        """Main decision loop: Observe -> Probability -> EV -> Decision."""
        # 1. Prediction (Ensemble Brain)
        probs = self.brain.predict(outcomes)

        # Determine best direction
        direction = "U" if probs["U"] > probs["D"] else "D"
        win_prob = probs[direction]

        # 2. Risk Calculation (Kelly + Confidence)
        confidence = abs(probs["U"] - probs["D"]) * 2.0 # Scale to 0-1
        stake = self.risk.calculate_stake(win_prob, confidence)

        # 3. Edge Calculation (EV)
        ev = self.compute_edge(win_prob, stake) if stake > 0 else 0

        # 4. Final Rule: EV > 0 AND Confidence threshold
        # Threshold: Starts at 0.1 for tuition, 0.2 for sniper
        min_conf = 0.1 if self.risk.state["mode"] == "TUITION" else 0.2

        if ev > 0 and confidence >= min_conf:
            # 5. Exploration vs Exploitation (80/20)
            import random
            if random.random() < 0.2:
                # Explore (bet on the other direction with 50% lower stake)
                alt_direction = "D" if direction == "U" else "U"
                return {
                    "action": "BET",
                    "direction": alt_direction,
                    "amount": stake / 2,
                    "prob": probs[alt_direction],
                    "confidence": confidence,
                    "ev": ev,
                    "mode": "EXPLORE"
                }

            return {
                "action": "BET",
                "direction": direction,
                "amount": stake,
                "prob": win_prob,
                "confidence": confidence,
                "ev": ev,
                "mode": "EXPLOIT"
            }

        return {
            "action": "WAIT",
            "reason": "Negative EV or low confidence",
            "confidence": confidence,
            "ev": ev
        }
