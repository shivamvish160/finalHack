# Build from the REPO ROOT (docker build -f services/alert-replay-service/Dockerfile .)
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/ ./agents/
COPY services/alert-replay-service/app/ ./services/alert-replay-service/app/

ENV PYTHONPATH=/app
WORKDIR /app/services/alert-replay-service

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8080"]
