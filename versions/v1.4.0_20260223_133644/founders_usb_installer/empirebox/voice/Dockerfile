FROM python:3.11-slim

WORKDIR /app

# System dependencies for pydub (ffmpeg) and piper
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application source
COPY . .

# Pre-create model directories
RUN mkdir -p /app/models/whisper /app/models/piper

# Download default Piper voice at build time (optional – comment out to speed up builds
# and instead mount models as a Docker volume)
# RUN python -m piper.download --voice en_US-amy-medium --output-dir /app/models/piper

EXPOSE 8200

ENV CONFIG_PATH=/app/config.yaml \
    PIPER_MODELS_DIR=/app/models/piper \
    WHISPER_MODEL=base

CMD ["python", "service.py"]
