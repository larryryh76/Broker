FROM ubuntu:22.04

# Avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set Wine architecture and prefix
ENV WINEARCH=win64
ENV WINEPREFIX=/root/.wine

# Install Wine, Xvfb, wget and dependencies
RUN dpkg --add-architecture i386 && apt-get update && apt-get install -y \
    wine \
    wine64 \
    wine32 \
    xvfb \
    python3 \
    python3-pip \
    curl \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Initialize Wine
RUN xvfb-run wineboot --init

# Install mt5linux for the Linux client side
RUN pip3 install mt5linux rpyc==4.1.5

# Create a workspace
WORKDIR /mt5

# Download and install MetaTrader 5 silently using Wine
RUN wget -O /mt5setup.exe https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe \
    && xvfb-run wine /mt5setup.exe /auto /quit

# Download and install Windows Python for Wine (to run the bridge server)
RUN wget -O /python-setup.exe https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe \
    && xvfb-run wine /python-setup.exe /quiet InstallAllUsers=1 PrependPath=1 \
    && xvfb-run wine python -m pip install --upgrade pip \
    && xvfb-run wine python -m pip install MetaTrader5 mt5linux rpyc==4.1.5

# Copy start script
COPY start_mt5.sh /start_mt5.sh
RUN chmod +x /start_mt5.sh

# Expose bridge port
EXPOSE 8001

CMD ["/start_mt5.sh"]
