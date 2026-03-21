from trading_bot import config
from strategy_generator import StrategyGenerator
from backtest_engine import BacktestEngine

class GeneticOptimizer:
    def __init__(self, data, ai_model):
        self.generator = StrategyGenerator()
        self.backtester = BacktestEngine(data)
        self.ai_model = ai_model

    def evolve(self):
        print(f"Starting Genetic Evolution (Pop: {config.POPULATION_SIZE}, Gen: {config.GENERATIONS})...")

        # 1. Initial population
        population = self.generator.generate_population(config.POPULATION_SIZE)
        best_strategy = None

        for gen in range(config.GENERATIONS):
            results = []
            for params in population:
                res = self.backtester.run_backtest(params, self.ai_model)
                results.append(res)

            # Rank by score
            results.sort(key=lambda x: x['score'], reverse=True)

            current_best = results[0]
            if best_strategy is None or current_best['score'] > best_strategy['score']:
                best_strategy = current_best

            print(f"Gen {gen+1} | Best Score: {current_best['score']:.4f} | WinRate: {current_best['win_rate']:.2%}")

            # Selection (Elite %)
            elite_count = int(config.POPULATION_SIZE * config.ELITE_PERCENT)
            elites = [r['params'] for r in results[:elite_count]]

            # New population through mutation
            new_population = elites.copy()
            while len(new_population) < config.POPULATION_SIZE:
                parent = elites[0] # Aggressive: mutate only from the best
                new_population.append(self.generator.mutate(parent))

            population = new_population

        print(f"OPTIMIZATION COMPLETE. Best win rate: {best_strategy['win_rate']:.2%}")
        return best_strategy['params']
