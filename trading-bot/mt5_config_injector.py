import os
import config

def inject_headless_config():
    terminal_dir = config.TERMINAL_DIR

    # Ensure MT5 data directories exist
    dirs = [
        "",
        "config",
        "MQL5",
        "Profiles"
    ]
    for d in dirs:
        path = os.path.join(terminal_dir, d)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            print(f"Created directory: {path}")

    config_dir = os.path.join(terminal_dir, "config")

    # common.ini for Experts
    common_path = os.path.join(config_dir, "common.ini")
    with open(common_path, "w") as f:
        f.write("[Common]\nExpertsEnable=1\nExpertsDllImport=1\n")

    # terminal.ini for login bypass and settings
    terminal_ini = os.path.join(config_dir, "terminal.ini")
    with open(terminal_ini, "w") as f:
        f.write("[Common]\n")
        f.write(f"Login={config.MT5_LOGIN}\n")
        f.write(f"Password={config.MT5_PASSWORD}\n")
        f.write(f"Server={config.MT5_SERVER}\n")
        f.write("EnableNews=0\n")
        f.write("KeepPrivate=0\n")
        f.write("\n[Charts]\n")
        f.write("MaxBars=100000\n")

    print(f"MT5 Headless config injected at {terminal_ini}")
