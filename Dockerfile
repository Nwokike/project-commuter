# Docker build file for Render combining Python, UV, and Google Chrome

FROM python:3.12-slim

# Prevent prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install system dependencies for Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set up the application directory
WORKDIR /app

# Copy the rest of the application
COPY . .

# Install python dependencies incredibly fast using uv
# Sync frozen lockfile dependencies to ensure exact reproduction
RUN uv sync --frozen

# Command to run the FastApi application
CMD ["uv", "run", "python", "server.py"]
