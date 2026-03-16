FROM ubuntu:22.04

# Avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set Wine architecture and prefix
ENV WINEARCH=win64
ENV WINEPREFIX=/root/.wine
ENV DISPLAY=:99

# Install Wine, Xvfb, wget and dependencies
RUN dpkg --add-architecture i386 && apt-get update && apt-get install -y \
    wine64 \
    wine32 \
    winbind \
    cabextract \
    xvfb \
    x11-utils \
    python3 \
    python3-pip \
    curl \
    wget \
    unzip \
    winetricks \
    fonts-liberation \
    fonts-wine \
    && rm -rf /var/lib/apt/lists/*

# Install mt5linux for the Linux client side
RUN pip3 install mt5linux rpyc==4.1.5

# Create a workspace
WORKDIR /mt5

# Initialize Wine prefix
RUN Xvfb :99 -screen 0 1024x768x16 & \
    sleep 5 && \
    wineboot --init

# Install Gecko and Mono
RUN Xvfb :99 -screen 0 1024x768x16 & \
    sleep 5 && \
    winetricks -q gecko mono

# Download MetaTrader 5 installer
RUN wget -O /mt5setup.exe https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe

# Install MetaTrader 5
RUN Xvfb :99 -screen 0 1024x768x16 & \
    sleep 5 && \
    wine /mt5setup.exe /silent

# Download Python for Windows
RUN wget -O /python-setup.exe https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe

# Install Python inside Wine
RUN Xvfb :99 -screen 0 1024x768x16 & \
    sleep 5 && \
    wine /python-setup.exe /quiet InstallAllUsers=1 PrependPath=1

# Install Python trading dependencies
RUN Xvfb :99 -screen 0 1024x768x16 & \
    sleep 5 && \
    wine python -m pip install --upgrade pip

RUN Xvfb :99 -screen 0 1024x768x16 & \
    sleep 5 && \
    wine python -m pip install MetaTrader5 mt5linux rpyc==4.1.5

# Copy start script
COPY start_mt5.sh /start_mt5.sh
RUN chmod +x /start_mt5.sh

# Expose bridge port
EXPOSE 8001

CMD ["/start_mt5.sh"]
