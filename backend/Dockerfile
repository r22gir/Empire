FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --create-home --uid 10001 empire \
    && mkdir -p /data \
    && chown -R empire:empire /app /data

USER empire

ENV PYTHONUNBUFFERED=1 \
    EMPIRE_DATA_DIR=/data \
    EMPIRE_TASK_DB=/data/empire.db \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    CORS_ORIGINS=* \
    EMPIRE_ENV=sandbox

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=8s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
