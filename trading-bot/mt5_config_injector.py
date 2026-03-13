import os
import config

def inject_headless_config():
    # SECTION 3 — Headless Login Configuration (Native Foundation)
    # Target the repository-local config folder
    config_dir = os.path.join(config.TERMINAL_DIR, "config")

    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir)
        except:
            return

    # common.ini for Experts/Algo-trading
    common_path = os.path.join(config_dir, "common.ini")
    with open(common_path, "w") as f:
        f.write("[Common]\nExpertsEnable=1\nExpertsDllImport=1\nWebLogin=0\nNewsEnable=0\n")

    # terminal.ini for login bypass (SECTION 3)
    terminal_ini = os.path.join(config_dir, "terminal.ini")
    with open(terminal_ini, "w") as f:
        f.write("[Common]\n")
        f.write(f"Login={config.MT5_LOGIN}\n")
        f.write(f"Password={config.MT5_PASSWORD}\n")
        f.write(f"Server={config.MT5_SERVER}\n")
        f.write("KeepPrivate=0\n")
        f.write("EnableNews=0\n")
        f.write("\n[Charts]\n")
        f.write("MaxBars=100000\n")

    print(f"Headless Config (terminal.ini) pre-seeded at {config_dir}")
