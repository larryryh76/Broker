# OMNI-RECURSIVE MONEY MACHINE (V3.5)

The **Omni-Recursive Money Machine V3.5** is a stateful, probabilistic, self-adaptive betting system specifically engineered for the **Spin da Bottle** game on Football.com Nigeria. It utilizes a multi-model ensemble and a structured intelligence layer (MongoDB) to identify and exploit statistical edges in real-time.

---

## 🧠 System Architecture

### 1. Intelligence Layer (Memory Graph)
- **Pattern Learning:** Reconstructs full system state on each run from MongoDB.
- **Sequence Intelligence:** Stores patterns (e.g., `UUDUD`) with win/loss rates to calculate transition probabilities.
- **Persistence:** All session data (bankroll, model weights, streaking history) persists across stateless GitHub Actions runs.

### 2. Ensemble Brain
- **Multi-Model Support:** Integrates Markov Chains, Streak Continuation, Mean Reversion (5-count switch), and Bayesian Baselines.
- **Dynamic Adaptation:** Weights each model based on its recent performance. Models that predict accurately are rewarded; failing models are penalized.
- **Exploration Engine:** Dedicated 20% of bets for exploration to prevent overfitting and pattern locking.

### 3. Financial & Risk Engine
- **Tuition Mode:** Initial phase focused on model calibration with flat ₦10 stakes.
- **Sniper Mode:** Advanced phase using Kelly-inspired staking logic based on edge and confidence.
- **Vault Protection:** Automatically locks ₦500 once the bankroll reaches ₦800.
- **Drawdown Control:** Reduces aggression or pauses execution if drawdown exceeds 15% from the peak.

### 4. Stealth Execution Layer
- **Headless Browser:** Uses Playwright with `playwright-stealth` to bypass bot detection.
- **Human Simulation:** Implements random jitter, variable click offsets, and timing randomization.

---

## 🛠 Setup Instructions

### GitHub Secrets
To deploy the system, configure the following secrets in your repository:
- `MONGODB_URI`: Connection string for your MongoDB Atlas cluster.
- `SPIN_URL`: The URL for the Football.com Nigeria Spin da Bottle game.
- `FOOTBALL_NG_LOGIN`: Your account login.
- `FOOTBALL_NG_PASS`: Your account password.

### Selector Configuration (Last Mile Optimization)
Due to the dynamic nature of web applications, you may need to configure the following environment variables if the default selectors fail:
- `SELECTOR_HISTORY`: Selector for spin history circles (e.g., `.history-circle`).
- `SELECTOR_AMOUNT`: Selector for the bet amount input field.
- `SELECTOR_UP`: Selector for the 'Up' button.
- `SELECTOR_DOWN`: Selector for the 'Down' button.

**Tip:** Check the `artifacts` directory in your GitHub Action run for screenshots (`initial_load.png`, `scraping_error.png`) to debug and identify the correct selectors.

### MongoDB Configuration
Ensure the following collections are created in a database named `omni_v35`:
- `spins`: Raw spin outcomes.
- `sequences`: Pattern intelligence nodes.
- `models`: Ensemble model weights and performance metrics.
- `sessions`: Global bankroll and session state.

---

## ⚙️ Deployment (GitHub Actions)
The system is automated via GitHub Actions to run every 15 minutes.
1. Each cycle begins by loading the session state from MongoDB.
2. The browser observes the latest spin history.
3. The Ensemble Brain calculates probabilities and the Edge Calculator computes Expected Value (EV).
4. If a positive EV and sufficient confidence exist, a bet is executed.
5. Post-cycle, the results are logged, and the state is persisted back to MongoDB.

---

## 📁 Folder Structure
- `spin_bot/`
  - `bot.py`: Main orchestrator and system lifecycle manager.
  - `models.py`: Ensemble model implementations and weight adaptation logic.
  - `memory.py`: MongoDB interaction layer and state persistence.
  - `risk.py`: Financial engine, drawdown controls, and vault logic.
  - `executor.py`: Probability-to-decision engine and EV calculation.
  - `playwright_client.py`: Browser automation and stealth layer.
- `.github/workflows/spin-bot.yml`: GitHub Actions execution workflow.
- `legacy_mt5/`: Archived MetaTrader 5 bot infrastructure (PAUSED).

---

## ⚠️ Risk Disclaimer
This system is an experimental probabilistic tool. Betting involves significant financial risk. The developers are not responsible for any financial losses incurred through the use of this software. **Never risk more than you can afford to lose.**

---

🎯 **Operating Principle:** Identify the edge, act only when confirmed, preserve capital aggressively, and survive the long term.
