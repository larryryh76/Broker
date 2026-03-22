import random
from typing import List, Dict, Optional
from spin_bot.models import EnsembleBrain
from spin_bot.risk import RiskEngine

class DecisionExecutor:
    def __init__(self, brain: EnsembleBrain, risk_engine: RiskEngine):
        self.brain = brain
        self.risk = risk_engine

    def compute_ev(self, win_prob: float, stake: float) -> float:
        """EV = (P_win * payout) - (P_loss * stake)"""
        p_loss = 1.0 - win_prob
        # Football.com payout assumed 1.95x stake (profit 0.95x)
        payout = stake * 1.95
        ev = (win_prob * payout) - (p_loss * stake)
        return ev

    def decide(self, outcomes: List[str]) -> Optional[Dict]:
        """Main decision engine: Observe -> EV -> Confidence -> Decision."""
        # 1. Prediction (Ensemble Brain)
        probs = self.brain.predict(outcomes)

        # Determine best direction
        direction = "U" if probs["U"] > probs["D"] else "D"
        win_prob = probs[direction]

        # 2. Confidence Calculation (Normalized)
        # 0.5 is no info, 1.0 is full info
        confidence = abs(win_prob - 0.5) * 2.0

        # 3. Dynamic Staking (Kelly-inspired)
        stake = self.risk.calculate_stake(win_prob, confidence)

        # 4. Expected Value (EV) Engine
        ev = self.compute_ev(win_prob, stake) if stake > 0 else 0

        print(f"DECISION: Analysing {direction} | Prob: {win_prob:.2f} | Conf: {confidence:.2f} | EV: {ev:.2f}")

        # 5. EXECUTION RULE: EV > 0 AND Prob > 0.55 AND confidence > dynamic threshold
        # Threshold: 0.15 for tuition, 0.25 for sniper
        dynamic_threshold = 0.15 if self.risk.state["mode"] == "TUITION" else 0.25

        if ev > 0 and win_prob >= 0.55 and confidence >= dynamic_threshold:
            print(f"EXECUTION: BET ₦{stake} on {direction}")
            return {
                "action": "BET",
                "direction": direction,
                "amount": stake,
                "prob": win_prob,
                "confidence": confidence,
                "ev": ev
            }

        # Observation/Skip mode
        reason = "EV <= 0" if ev <= 0 else "Low confidence/probability"
        print(f"SKIP: {reason}")
        return {
            "action": "WAIT",
            "reason": reason,
            "confidence": confidence,
            "ev": ev
        }
