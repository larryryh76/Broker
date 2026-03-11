# Use Ubuntu 22.04 as the base image
FROM ubuntu:22.04

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV GIT_TERMINAL_PROMPT=0

# Enable 32-bit architecture and install Wine dependencies
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y \
    software-properties-common \
    git \
    wget \
    curl \
    gnupg2 \
    ca-certificates \
    wine64 \
    wine32 \
    winbind \
    xvfb \
    cabextract \
    unzip \
    fonts-wine \
    python3 \
    python3-pip \
    libvulkan1 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Optimize Wine Environment (Production Settings)
ENV DISPLAY=:99
ENV WINEPREFIX=/root/.wine
ENV WINEDEBUG=-all
ENV WINEARCH=win64
ENV WINEDLLOVERRIDES="mscoree,mshtml="

# Install native Linux Python dependencies
COPY trading-bot/requirements_linux.txt /app/requirements_linux.txt
RUN pip3 install --no-cache-dir -r /app/requirements_linux.txt && \
    pip3 install --no-cache-dir pandas-ta-classic

# Download MT5 and Windows Python Embedded
WORKDIR /app
RUN wget https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe -O /app/mt5setup.exe && \
    wget https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip -O /app/python_win.zip && \
    unzip /app/python_win.zip -d /app/python_win

# Fix Windows Embedded Python
RUN sed -i 's/#import site/import site/' /app/python_win/python310._pth

# Copy the rest of the code
COPY . /app
RUN chmod +x /app/run_mt5.sh

# Set the entrypoint to the startup script
ENTRYPOINT ["/app/run_mt5.sh"]
