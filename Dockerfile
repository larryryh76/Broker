FROM ubuntu:22.04

# Avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Ensure Python 3 and pip are installed
RUN apt-get update && apt-get install -y python3 python3-pip

# Install Linux-side Python dependencies for the trading bot
COPY trading-bot/requirements.txt .
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

# Copy the trading bot code into the container
COPY . .

# Command to start the trading bot
CMD ["python3", "trading-bot/bot.py"]
