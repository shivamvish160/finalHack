# Build from the REPO ROOT (docker build -f services/api-gateway/Dockerfile .)
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/ ./agents/
COPY services/api-gateway/app/ ./services/api-gateway/app/

ENV PYTHONPATH=/app
WORKDIR /app/services/api-gateway

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
