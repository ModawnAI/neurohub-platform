# NeuroHub API

## 1) Environment

```bash
cp .env.example .env
```

Core variables:
- `DATABASE_URL`: Supabase Postgres connection string (`postgresql+asyncpg://...`)
- `REDIS_URL`: Redis for Celery broker/backend
- `SUPABASE_JWKS_URL`: Supabase Auth JWKS endpoint
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `ALLOW_DEV_AUTH_FALLBACK`: local header-auth fallback (`true` only in development)

## 2) Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## 3) Migrate + Seed

```bash
alembic upgrade head
python scripts/seed_dev.py
```

Seed creates:
- default institution
- dev user
- default service/pipeline for first request flow

## 4) Run API

```bash
uvicorn app.main:app --reload --port 8000
```

## 5) Run Worker

```bash
celery -A app.worker.celery_app:celery_app worker -Q compute,reporting -l info
```

## 6) Run Reconciler

```bash
python -m app.reconciler
```

## 7) Auth Behavior

- Production path: `Authorization: Bearer <supabase_jwt>`
- Development fallback: `X-User-Id`, `X-Institution-Id`, `X-Roles` headers
- If `ALLOW_DEV_AUTH_FALLBACK=false`, bearer token is mandatory.
