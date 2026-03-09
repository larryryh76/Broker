import subprocess
import time
import os
import sys

# SECTION 9 — Runner Watchdog
def run_watchdog():
    print("--- GHOST RUNNER WATCHDOG ACTIVE ---")

    # Path to the main bot script
    script_path = os.path.join(os.path.dirname(__file__), "bot.py")

    while True:
        print(f"[{time.strftime('%H:%M:%S')}] Starting trading bot engine...")

        # Launch bot.py as a subprocess
        process = subprocess.Popen([sys.executable, script_path])

        # Wait for the process to terminate
        process.wait()

        print(f"[{time.strftime('%H:%M:%S')}] Bot engine stopped (Exit Code: {process.returncode}).")

        # If running on GitHub Actions, the bot handles its own restart via API
        # but the watchdog provides local resilience.
        print("Restarting engine in 10 seconds...")
        time.sleep(10)

if __name__ == "__main__":
    run_watchdog()
