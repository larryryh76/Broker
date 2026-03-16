FROM ghcr.io/larryryh76/mt5-headless:latest

# Avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install Linux-side Python dependencies for the trading bot
# Note: The base image already handles the Wine-side bridge server
COPY trading-bot/requirements.txt .
RUN pip install -r requirements.txt

# Copy the trading bot code into the container
COPY . .

# Expose bridge port
EXPOSE 8001

# Command to start the trading bot
# The base image's entrypoint will handle starting Xvfb and MT5
# We override CMD to run our bot logic
CMD ["python", "trading-bot/bot.py"]
