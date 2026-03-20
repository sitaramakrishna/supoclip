# Use Python 3.13 slim image
FROM python:3.13-slim

# Install system dependencies including ffmpeg, unzip, and build tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    unzip \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install deno (required by yt-dlp for YouTube JS challenge solving)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_DIR=/root/.deno
ENV PATH="/root/.deno/bin:${PATH}"

# Install uv package manager
RUN pip install uv
ENV UV_PYTHON=/usr/local/bin/python3

# Set working directory
WORKDIR /app

# Copy pyproject.toml and uv.lock for dependency installation
COPY pyproject.toml uv.lock* ./

# Create virtual environment and install dependencies using uv sync
RUN uv venv .venv && uv sync

# Force update yt-dlp to the absolute latest version to handle YouTube API changes
# Also install from git to get the very latest commits
RUN uv pip install --upgrade --force-reinstall yt-dlp
RUN uv pip install --upgrade --force-reinstall "yt-dlp[default]"

# Copy source code
COPY src/ ./src/

# Copy fonts and transitions directories
COPY fonts/ ./fonts/
COPY transitions/ ./transitions/

# Create necessary directories for video processing
RUN mkdir -p /app/uploads /app/clips /app/logs /tmp

# Expose the port (Cloud Run uses PORT env var)
EXPOSE 8080

# Use a shell script to expand the PORT environment variable
CMD .venv/bin/uvicorn src.main_refactored:app --host 0.0.0.0 --port ${PORT:-8080}
