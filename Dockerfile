FROM ubuntu:22.04

# Avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Essential system dependencies for Python 3
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install dependencies
COPY trading_bot/requirements.txt .
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r requirements.txt

# Copy bot code
COPY trading_bot/ trading_bot/

# Ensure logs and other necessary directories exist
RUN mkdir -p trading_bot/logs trading_bot/snapshots trading_bot/data trading_bot/models

# Set Python Path and command
ENV PYTHONPATH=/app
CMD ["python3", "trading_bot/bot.py"]
