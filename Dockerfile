# Use Ubuntu 22.04 as the base image
FROM ubuntu:22.04

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies for Wine, Xvfb, and native Python
RUN apt-get update && apt-get install -y \
    software-properties-common \
    wget \
    gnupg2 \
    ca-certificates \
    xvfb \
    python3 \
    python3-pip \
    libvulkan1 \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Add WineHQ repository and install Wine
RUN dpkg --add-architecture i386 && \
    mkdir -pm 755 /etc/apt/keyrings && \
    wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key && \
    wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/ubuntu/dists/jammy/winehq-jammy.sources && \
    apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists/*

# Install native Linux Python dependencies
COPY trading-bot/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir mt5linux pandas numpy pandas-ta scikit-learn python-dotenv joblib pymongo requests

# Download MT5 and Windows Python Embedded (to avoid full installer)
WORKDIR /app
RUN wget https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe -O /app/mt5setup.exe && \
    wget https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip -O /app/python_win.zip && \
    unzip /app/python_win.zip -d /app/python_win

# Install MetaTrader 5 via Wine (Silent Installation)
# We do this at build time to pre-warm the image
ENV DISPLAY=:99
ENV WINEPREFIX=/root/.wine
ENV WINEDEBUG=-all
RUN Xvfb :99 -screen 0 1024x768x16 & \
    export DISPLAY=:99 && \
    wineboot --init && \
    wine /app/mt5setup.exe /auto /quit && \
    sleep 30

# Install the actual MetaTrader5 library into the Windows "embedded" python
# Note: Embedded python needs a bit of trickery to run pip
RUN wget https://bootstrap.pypa.io/get-pip.py -O /app/get-pip.py && \
    xvfb-run -a wine /app/python_win/python.exe /app/get-pip.py && \
    xvfb-run -a wine /app/python_win/python.exe -m pip install MetaTrader5

# Copy the rest of the code
COPY . /app
RUN chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
