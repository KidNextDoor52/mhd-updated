# Dockerfile
FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

# Copy everything inside the app folder to root of container
#COPY app/ .env.dev
COPY app/ ./
COPY app/.env.dev .env.dev
COPY frontend/ ./frontend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
