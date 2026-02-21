# NeuroHub (Scratch Build)

NeuroHub is a Korean-first medical AI workflow orchestration platform.

## Stack
- Web: Next.js 16 + TypeScript + Tailwind v4 + Radix + TanStack Query + Biome + Bun
- API: FastAPI + SQLAlchemy + Alembic
- Async: Celery + Redis + Reconciler
- Data/Auth/Storage: Supabase (Postgres/Auth/Storage)
- Deploy: Fly.io (API/Worker/Reconciler)

## Structure
- `/Users/paksungho/Downloads/neurohub/NeuroHub/apps/web` - Next.js frontend
- `/Users/paksungho/Downloads/neurohub/NeuroHub/apps/api` - FastAPI backend
- `/Users/paksungho/Downloads/neurohub/NeuroHub/supabase` - Supabase CLI config and SQL policies
- `/Users/paksungho/Downloads/neurohub/NeuroHub/infra/fly` - Fly.io deployment configs
- `/Users/paksungho/Downloads/neurohub/NeuroHub/docs/TECHNICAL_PRD_KR.md` - Technical PRD

## Quick Start

### 1) API
```bash
cd /Users/paksungho/Downloads/neurohub/NeuroHub/apps/api
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
alembic upgrade head
python scripts/seed_dev.py
uvicorn app.main:app --reload --port 8000
```

### 2) Web
```bash
cd /Users/paksungho/Downloads/neurohub/NeuroHub/apps/web
cp .env.local.example .env.local
bun install
bun run dev
```

## Deployment / Operations Docs
- Supabase setup: `/Users/paksungho/Downloads/neurohub/NeuroHub/docs/SUPABASE_SETUP_KR.md`
- Fly deployment: `/Users/paksungho/Downloads/neurohub/NeuroHub/docs/DEPLOYMENT_FLY_KR.md`
