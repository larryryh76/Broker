FROM ubuntu:22.04

# Avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Wine, Xvfb and dependencies
RUN dpkg --add-architecture i386 && apt-get update && apt-get install -y \
    wine \
    wine32 \
    xvfb \
    python3 \
    python3-pip \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install mt5linux for the Linux client side (if needed in container)
RUN pip3 install mt5linux rpyc==4.1.5

# Create a workspace
WORKDIR /mt5

# Download MT5 installer
RUN curl -o mt5setup.exe https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe

# Download Windows Python for Wine (to run the bridge server)
RUN curl -o python-3.10.11-amd64.exe https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe

# Copy start script
COPY start_mt5.sh /start_mt5.sh
RUN chmod +x /start_mt5.sh

# Expose bridge port
EXPOSE 8001

CMD ["/start_mt5.sh"]
