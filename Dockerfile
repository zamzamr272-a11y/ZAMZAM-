FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AUTO_CREATE_SCHEMA=false
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-ind tesseract-ocr-eng poppler-utils \
    && rm -rf /var/lib/apt/lists/*
COPY backend /app/backend
COPY frontend /app/frontend
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
