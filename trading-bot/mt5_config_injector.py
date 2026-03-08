import os
import config
from config import logger

def inject_headless_config():
    terminal_dir = config.TERMINAL_DIR
    config_dir = os.path.join(terminal_dir, "config")

    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir)
        except:
            return

    # common.ini for Experts
    common_path = os.path.join(config_dir, "common.ini")
    with open(common_path, "w") as f:
        f.write("[Common]\nExpertsEnable=1\nExpertsDllImport=1\n")

    # terminal.ini for login bypass
    terminal_ini = os.path.join(config_dir, "terminal.ini")
    with open(terminal_ini, "w") as f:
        f.write(f"[Common]\nLogin={config.MT5_LOGIN}\nServer={config.MT5_SERVER}\nPassword={config.MT5_PASSWORD}\n")
        f.write("KeepPrivate=1\nEnableNews=0\nCertInstall=1\n")

    print(f"MT5 Headless config injected at {config_dir}")
