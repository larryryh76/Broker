# OMNI-RECURSIVE MONEY MACHINE (V3.1 Alpha)

The **Omni-Recursive Money Machine V3.1 Alpha** is a stateful, probabilistic, and self-adaptive betting system specifically engineered for the **Spin da Bottle** game on Football.com Nigeria.

## 🧠 CORE FEATURES

### 1. 98% Accuracy Protocol (Cold Start)
- **Learning Mode:** The system is programmatically forbidden from betting until it captures 200 real-world game outcomes in MongoDB.
- **Elite Execution:** Live betting only unlocks once model confidence > 0.8 and mathematical Expected Value (EV) > 0.05.

### 2. Mobile-Native Automation
- **Emulation:** Configured for iPhone 13 device profile to ensure consistent and unambiguous UI presentation.
- **Robust Selectors:** Uses strict text-based and hierarchical selectors (e.g., `section >> input[type='password']`) to handle complex mobile layouts and duplicated fields.
- **Iframe Handling:** Directly targets the `sportygames` iframe for all game interactions (history capture, betting).

### 3. Ensemble Brain Architecture
- **Softmax Ensemble:** Combines 4 probabilistic models: Markov Chain, Streak Analysis, Mean Reversion, and Bayesian Baseline.
- **Adaptive Weighting:** Models are dynamically rewarded for correct predictions and penalized for errors.
- **House-Edge Aware:** All EV calculations include a penalty for the 'Middle' (house win) outcome.

### 4. Risk & Vault Management
- **Vault Floor:** Enforces a strict ₦500 balance floor. Automation enters observation-only mode if capital hits this threshold.
- **Kelly-Inspired Staking:** Dynamic position sizing based on edge and model confidence.
- **Drawdown Control:** Stake reduction at 15% drawdown to preserve capital.

---

## 🛠 SETUP INSTRUCTIONS

### GitHub Secrets
Configure the following secrets in your repository:
- `MONGODB_URI`: MongoDB connection string.
- `FOOTBALL_NG_LOGIN`: Your account phone/mobile.
- `FOOTBALL_NG_PASS`: Your account password.

### Artifacts & Auditing
The system prioritizes human-readable transparency:
- `artifacts/cycle_logs.txt`: Chronological audit of every execution step and model decision.
- `artifacts/status.txt`: Immediate status of the latest login attempt.
- `artifacts/error.png`: Visual evidence captured automatically on interaction failure.

---

🎯 **OPERATING PRINCIPLE:** "Responses are useless without knowing how they were requested." The system combines deep network intelligence with robust UI automation to calculate mathematical edge.
