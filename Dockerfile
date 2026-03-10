# Use Ubuntu 22.04 as the base image
FROM ubuntu:22.04

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies for Wine, Xvfb, and Python installer
RUN apt-get update && apt-get install -y \
    software-properties-common \
    wget \
    gnupg2 \
    ca-certificates \
    xvfb \
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

# Set environment variables for Wine and Xvfb
ENV DISPLAY=:99
ENV WINEPREFIX=/root/.wine
ENV WINEDEBUG=-all

# Initialize Wine prefix and download Windows Python & MT5
WORKDIR /app
RUN wineboot --init && \
    wget https://www.python.org/ftp/python/3.12.1/python-3.12.1-amd64.exe -O /app/python-3.12.1-amd64.exe && \
    wget https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe -O /app/mt5setup.exe

# Install Windows Python via Wine (Silent Installation)
RUN xvfb-run -a wine /app/python-3.12.1-amd64.exe /quiet InstallAllUsers=1 PrependPath=1

# Install MetaTrader 5 via Wine (Silent Installation)
# This pre-installs MT5 into the Docker image to avoid installation on every run
RUN xvfb-run -a wine /app/mt5setup.exe /auto /quit

# Copy requirements and install via Wine-based Python
COPY trading-bot/requirements.txt /app/requirements.txt
RUN xvfb-run -a wine python -m pip install --upgrade pip && \
    xvfb-run -a wine python -m pip install -r /app/requirements.txt

# Copy the rest of the code
COPY . /app
RUN chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
