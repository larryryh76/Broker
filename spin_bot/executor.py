import random
from typing import List, Dict, Optional
from spin_bot.models import EnsembleBrain
from spin_bot.risk import RiskEngine

class DecisionExecutor:
    def __init__(self, brain: EnsembleBrain, risk_engine: RiskEngine):
        self.brain = brain
        self.risk = risk_engine

    def compute_ev(self, win_prob: float, stake: float) -> float:
        """EV = (prob_win * payout) - (prob_loss * stake)"""
        # Football.com Spin da Bottle payout is 1.95x stake (profit is 0.95x)
        payout = stake * 1.95
        prob_loss = 1.0 - win_prob
        ev = (win_prob * payout) - (prob_loss * stake)
        return ev

    def decide(self, outcomes: List[str]) -> Optional[Dict]:
        """Main decision logic: Calculate prob -> EV -> Thresholds -> Execution."""
        # 1. Prediction (Ensemble Brain)
        probs = self.brain.predict(outcomes)

        # Determine best direction
        direction = "U" if probs["U"] > probs["D"] else "D"
        win_prob = probs[direction]

        # 2. Confidence Calculation (Normalized)
        # 0.5 is no information, 1.0 is full information
        confidence = abs(probs["U"] - probs["D"]) * 2.0

        # 3. Dynamic Threshold Calculation
        # The dynamic threshold decreases as we get more history, or based on mode
        min_prob_threshold = 0.55
        dynamic_conf_threshold = 0.15 if self.risk.state["mode"] == "TUITION" else 0.25

        # 4. Stake Calculation (Risk Engine)
        stake = self.risk.calculate_stake(win_prob, confidence)

        # 5. Strict Expected Value (EV) Check
        ev = self.compute_ev(win_prob, stake) if stake > 0 else 0

        print(f"Decision Engine Analysis: {direction} | Prob: {win_prob:.2f} | Conf: {confidence:.2f} | EV: {ev:.2f}")

        # 6. Final Execution Decision
        if ev > 0 and win_prob >= min_prob_threshold and confidence >= dynamic_conf_threshold:
            print(f"DECISION: EXECUTE BET ({direction})")

            # Exploration logic (20% explore other directions or wait)
            if random.random() < 0.2:
                # 20% explore wait or alt direction
                if random.random() < 0.5:
                    print("Exploration Mode: Skipping Bet")
                    return {"action": "WAIT", "reason": "Exploration SKIP", "confidence": confidence, "ev": ev}

                alt_direction = "D" if direction == "U" else "U"
                print(f"Exploration Mode: ALT BET ({alt_direction})")
                return {
                    "action": "BET",
                    "direction": alt_direction,
                    "amount": 10.0, # Explore with minimum stake
                    "prob": probs[alt_direction],
                    "confidence": confidence,
                    "ev": self.compute_ev(probs[alt_direction], 10.0),
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

        # SKIP LOGIC
        reason = "EV <= 0" if ev <= 0 else "Low Confidence/Prob"
        print(f"DECISION: SKIP ({reason})")
        return {
            "action": "WAIT",
            "reason": reason,
            "confidence": confidence,
            "ev": ev
        }
