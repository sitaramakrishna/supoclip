FROM python:3.13-slim

# System deps for FFmpeg, OpenCV, MediaPipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend source
COPY ../backend /app

# Install all deps (full stack including video processing)
RUN pip install --no-cache-dir uv && \
    uv export --no-hashes --no-dev --project /app > /tmp/full-requirements.txt && \
    pip install --no-cache-dir -r /tmp/full-requirements.txt

# Expose worker HTTP port (QStash POSTs here)
EXPOSE 8001

# Start the QStash worker (FastAPI on port 8001)
CMD ["uvicorn", "src.qstash_worker:app", "--host", "0.0.0.0", "--port", "8001"]
