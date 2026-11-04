# syntax=docker/dockerfile:1
# Image UniOCR — moteur OCR + API + interface web, prête à l'emploi.
#
# Build :  docker build -t unocr .
# Run   :  docker run -p 127.0.0.1:8000:8000 -v unocr-data:/data unocr
#
# L'image embarque Tesseract 5 et les 11 modèles de langue, poppler (PDF)
# et zbar (codes-barres). Aucune dépendance réseau à l'exécution.

FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="UniOCR" \
      org.opencontainers.image.description="Moteur OCR universel : texte, structure, champs, tableaux, codes-barres" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UNOCR_ROOT=/app \
    UNOCR_DATA_DIR=/data

# ── dépendances système ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-fra \
        tesseract-ocr-deu \
        tesseract-ocr-spa \
        tesseract-ocr-ita \
        tesseract-ocr-por \
        tesseract-ocr-nld \
        tesseract-ocr-rus \
        tesseract-ocr-ara \
        tesseract-ocr-chi-sim \
        tesseract-ocr-tur \
        poppler-utils \
        libzbar0 \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── application ──────────────────────────────────────────────────────────────
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

COPY web ./web
COPY profiles ./profiles

# les données (documents, journaux, exports) vivent hors de l'image
RUN groupadd --system unocr && useradd --system --gid unocr --home-dir /data \
        --no-create-home unocr \
    && mkdir -p /data/logs \
    && chown -R unocr:unocr /data \
    && chmod 0750 /data

ENV UNOCR_LOG_DIR=/data/logs

USER unocr

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"

CMD ["python", "-m", "uvicorn", "unocr.api:app", "--host", "0.0.0.0", "--port", "8000"]
