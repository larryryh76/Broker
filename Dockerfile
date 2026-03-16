FROM ghcr.io/larryryh76/mt5-headless:latest

# Avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Ensure Python 3 and pip are installed
RUN apt-get update && apt-get install -y python3 python3-pip

# Install Linux-side Python dependencies for the trading bot
# Note: The base image already handles the Wine-side bridge server
COPY trading-bot/requirements.txt .
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

# Copy the trading bot code into the container
COPY . .

# Expose bridge port
EXPOSE 8001

# Command to start the trading bot
# The base image's entrypoint will handle starting Xvfb and MT5
# We override CMD to run our bot logic
CMD ["python3", "trading-bot/bot.py"]
