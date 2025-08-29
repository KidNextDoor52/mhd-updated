FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    gcc \
    g++ \
    cmake \
    libomp-dev \          # for nmslib
    libboost-all-dev \    # for nmslib
    libsqlite3-dev \
    libffi-dev \
    libssl-dev \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

COPY app/ ./
COPY app/templates ./templates
COPY app/static ./static

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
