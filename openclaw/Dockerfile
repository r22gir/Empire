FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn aiohttp pyyaml
COPY server.py /app/
COPY skills /app/skills/
COPY config.yaml /app/
EXPOSE 7878
CMD ["python", "server.py"]
