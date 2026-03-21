import random
from trading_bot import config

class StrategyGenerator:
    def __init__(self):
        pass

    def generate_random_params(self):
        return {
            "rsi_period": random.randint(7, 21),
            "rsi_overbought": random.randint(65, 85),
            "rsi_oversold": random.randint(15, 35),
            "sma_fast": random.randint(5, 30),
            "sma_slow": random.randint(40, 100),
            "ai_threshold": round(random.uniform(0.55, 0.85), 2),
            "momentum_weight": round(random.uniform(0.1, 1.0), 2)
        }

    def generate_population(self, size):
        return [self.generate_random_params() for _ in range(size)]

    def mutate(self, params):
        new_params = params.copy()
        key_to_mutate = random.choice(list(params.keys()))

        if "rsi_period" in key_to_mutate:
            new_params[key_to_mutate] = max(5, params[key_to_mutate] + random.randint(-2, 2))
        elif "rsi_overbought" in key_to_mutate:
            new_params[key_to_mutate] = min(90, params[key_to_mutate] + random.randint(-5, 5))
        elif "rsi_oversold" in key_to_mutate:
            new_params[key_to_mutate] = max(10, params[key_to_mutate] + random.randint(-5, 5))
        elif "sma_fast" in key_to_mutate:
            new_params[key_to_mutate] = max(5, params[key_to_mutate] + random.randint(-3, 3))
        elif "sma_slow" in key_to_mutate:
            new_params[key_to_mutate] = max(35, params[key_to_mutate] + random.randint(-10, 10))
        elif "ai_threshold" in key_to_mutate:
            new_params[key_to_mutate] = round(max(0.5, min(0.95, params[key_to_mutate] + random.uniform(-0.05, 0.05))), 2)

        return new_params
