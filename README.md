# OMNI-RECURSIVE MONEY MACHINE (V3.5) - PRODUCTION GRADE

The **Omni-Recursive Money Machine V3.5** is a production-grade, stateful, probabilistic, and self-adaptive betting system specifically engineered for the **Spin da Bottle** game on Football.com Nigeria.

## 🧠 PRODUCTION UPGRADES (V3.5)

### 1. Hardened Anti-Detection (Playwright)
- **Stealth Integration:** Fixed `playwright-stealth` to bypass modern bot detection (Failsafe `stealth(page)` logic).
- **Fingerprint Randomization:** Randomized User-Agents, realistic viewport settings, and `--disable-blink-features=AutomationControlled` browser flags.
- **Human Emulation:** Implemented timing jitter (0.8s-2.5s), non-instant clicks, and random hover/click offsets.

### 2. True Probabilistic Ensemble Brain
- **Softmax Weighting:** Replaced heuristic weights with a Softmax Ensemble (Markov, Streak, Mean Reversion, Bayesian Baseline).
- **Adaptive Learning:** Models are rewarded for correct predictions and penalized for errors, with weights updated dynamically via a back-propagation inspired loop.

### 3. Strict Expected Value (EV) Engine
- **Edge Calculation:** EV = (prob_win * payout) - (prob_loss * stake).
- **Enforcement:** The system NEVER places a bet unless EV > 0, probability > 0.55, and dynamic confidence thresholds are met.
- **Detailed Logging:** Full decision-making process is logged, showing win probability, confidence, and expected value.

### 4. Advanced Risk Management (Kelly-Inspired)
- **Dynamic Staking:** stake = bankroll * edge * confidence_factor.
- **Drawdown Protection:** If the system detects a drawdown > 15% from its peak equity, stake size is automatically reduced by 50% to preserve capital.
- **Circuit Breaker:** Session automatically halts after 4 consecutive losses or 15% drawdown to allow model recalibration.

### 5. Failsafe Architecture
- **Persistent State:** All data (spins, sequences, models, sessions) is persisted in MongoDB Atlas to handle stateless CI/CD runners.
- **Graceful Error Handling:** Comprehensive `try/except` wrapping around critical browser and database operations ensures the bot saves its state even upon crash.

---

## 🛠 SETUP INSTRUCTIONS

### GitHub Secrets
Configure the following secrets in your repository:
- `MONGODB_URI`: MongoDB connection string.
- `SPIN_URL`: Target game URL (Football.com NG).
- `FOOTBALL_NG_LOGIN`: Your account login.
- `FOOTBALL_NG_PASS`: Your account password.
- `SELECTOR_HISTORY`: CSS selector for spin history results.
- `SELECTOR_AMOUNT`: CSS selector for the bet amount input.
- `SELECTOR_UP`: CSS selector for the 'Up' button.
- `SELECTOR_DOWN`: CSS selector for the 'Down' button.
- `SELECTOR_LOGIN`: CSS selector for the login username field.
- `SELECTOR_PASS`: CSS selector for the login password field.
- `SELECTOR_SUBMIT`: CSS selector for the login submit button.

### Selector Discovery & Debugging
Since web interfaces are dynamic, the bot includes a built-in discovery engine. If the bot fails to interact with the game:
1. Check the `artifacts` directory in your GitHub Action run.
2. Review the screenshots (`initial_load.png`, `post_login.png`, `scraping_error.png`, `bet_error.png`).
3. Identify the correct CSS selectors from the screenshots or browser DevTools.
4. Update the corresponding GitHub Secrets to restore functionality without code changes.

### Execution
The system is automated via GitHub Actions to run every 15 minutes. It takes screenshots on any interaction failure and uploads them as artifacts for debugging.

---

🎯 **OPERATING PRINCIPLE:** The system is a probabilistic decision engine. It does not guess. It calculates edge and acts ONLY when edge exists.
