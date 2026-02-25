## ── Stage 1: Builder ──
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc libpq-dev \
       libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
       libcairo2-dev libgdk-pixbuf-2.0-dev libffi-dev \
       fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install .

## ── Stage 2: Runtime ──
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl libpq5 \
       libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
       libcairo2 libgdk-pixbuf-2.0-0 libffi8 \
       fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid 1001 --no-create-home appuser

COPY --from=builder /install /usr/local

COPY alembic.ini ./
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
