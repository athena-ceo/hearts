# Copyright (c) 2026 Athena Decision Systems SAS.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "hearts.web:app", "--host", "0.0.0.0", "--port", "8000"]
