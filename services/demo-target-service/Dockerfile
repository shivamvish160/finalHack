# Build from the REPO ROOT (docker build -f services/demo-target-service/Dockerfile .)
# No agents/ dependency -- this service is deliberately isolated (design.md §7.1).
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]"

COPY services/demo-target-service/app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
