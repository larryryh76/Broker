from typing import Dict

class RiskEngine:
    def __init__(self, bankroll: float, state: Dict):
        self.bankroll = bankroll
        self.state = state
        self.floor = 500.0

    def calculate_stake(self, confidence: float, ev: float) -> float:
        if self.bankroll < self.floor: return 0.0
        if ev <= 0 or confidence < 0.7: return 0.0
        base = min(self.bankroll * 0.02, 50.0)
        return round(base * (confidence * 2), 0)

    def update_result(self, win: bool):
        pass
