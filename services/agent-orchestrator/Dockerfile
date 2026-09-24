# Build from the REPO ROOT (docker build -f services/agent-orchestrator/Dockerfile .)
# so the shared agents/ package can be copied alongside this service.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/ ./agents/
COPY services/agent-orchestrator/app/ ./services/agent-orchestrator/app/

ENV PYTHONPATH=/app
WORKDIR /app/services/agent-orchestrator

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8080"]
