import random
from typing import List, Dict, Optional
from spin_bot.models import EnsembleBrain
from spin_bot.risk import RiskEngine

class DecisionExecutor:
    def __init__(self, brain: EnsembleBrain, risk_engine: RiskEngine):
        self.brain = brain
        self.risk = risk_engine

    def compute_ev(self, win_prob: float, stake: float) -> float:
        """
        EV = (P_win * Net_Profit) - (P_loss * Stake)
        V3.0 Refined Math: 1.95x - 2.0x payout.
        Accounting for 'M' (Middle) as house edge.
        """
        # Assume Middle occurs with probability P_m (e.g., 2% house edge)
        p_m = 0.02
        # Probability of win is win_prob reduced by house edge occurrence
        adjusted_win_prob = win_prob * (1 - p_m)
        p_loss = 1.0 - adjusted_win_prob

        # Payout 1.95x stake (Net Profit 0.95x)
        net_profit = stake * 0.95

        ev = (adjusted_win_prob * net_profit) - (p_loss * stake)
        return ev

    def decide(self, outcomes: List[str]) -> Optional[Dict]:
        """Main decision engine: Observe -> EV -> Confidence -> Decision."""
        # 1. Prediction
        probs = self.brain.predict(outcomes)

        direction = "U" if probs["U"] > probs["D"] else "D"
        win_prob = probs[direction]

        # 2. Confidence Calculation
        confidence = abs(win_prob - 0.5) * 2.0

        # 3. Dynamic Staking
        stake = self.risk.calculate_stake(win_prob, confidence)

        # 4. Expected Value (EV) Engine
        ev = self.compute_ev(win_prob, stake) if stake > 0 else 0

        print(f"DECISION: Analysing {direction} | Prob: {win_prob:.2f} | Conf: {confidence:.2f} | EV: {ev:.2f}")

        # 5. V3.0 EXECUTION RULE: EV > 0.05 AND Confidence > 0.7
        if ev > 0.05 and win_prob >= 0.55 and confidence >= 0.7:
            print(f"EXECUTION: BET ₦{stake} on {direction}")
            return {
                "action": "BET",
                "direction": direction,
                "amount": stake,
                "prob": win_prob,
                "confidence": confidence,
                "ev": ev
            }

        reason = "Low EV (<0.05)" if ev <= 0.05 else "Low confidence (<0.7)"
        print(f"SKIP: {reason}")
        return {
            "action": "WAIT",
            "reason": reason,
            "confidence": confidence,
            "ev": ev
        }
