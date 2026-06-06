FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir torch numpy biopython
COPY run.py .
ENTRYPOINT ["python", "run.py"]
