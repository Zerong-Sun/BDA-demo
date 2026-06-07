FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY artifacts artifacts

# Run as a non-root user; ensure writable paths for db/artifacts at runtime.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/backend/db /app/artifacts \
    && chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app
EXPOSE 8100

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8100"]
