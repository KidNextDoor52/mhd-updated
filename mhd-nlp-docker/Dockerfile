FROM python:3.10.6-slim

# System deps (add OCR + PDF tools here)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    gcc \
    g++ \
    cmake \
    libomp-dev \
    libboost-all-dev \
    libsqlite3-dev \
    libffi-dev \
    libssl-dev \
    wget \
    curl \
    pkg-config \
    python3-dev \
    # --- OCR / PDF deps ---
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    # (optional but nice for Pillow on some slim images)
    libjpeg-dev \
    zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Make sure requirements.txt includes:
# pytesseract, pdf2image, pillow, PyPDF2
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

COPY app/ ./app
COPY app/templates ./templates
COPY app/static ./static

# uvicorn entry
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
