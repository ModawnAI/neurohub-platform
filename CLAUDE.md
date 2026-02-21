# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NeuroHub is a Korean-first medical AI workflow orchestration platform. Monorepo with Bun workspaces.

- **Frontend**: Next.js 16 (App Router) at `apps/web` — Bun, TypeScript, Tailwind v4, Radix UI, TanStack Query v5, Biome
- **Backend**: FastAPI at `apps/api` — Python 3.11+, SQLAlchemy 2 async, Alembic, Pydantic v2
- **Async**: Celery + Redis + Outbox Reconciler
- **DB/Auth/Storage**: Supabase (Postgres, JWT Auth, Storage buckets)
- **Deploy**: Fly.io (API/Worker/Reconciler at nrt region), Vercel (frontend)

## Commands

### Web (from repo root)
```bash
bun run web:dev        # Next.js dev server (port 3000)
bun run web:build      # production build
bun run web:check      # tsc --noEmit
bun run web:lint       # biome check
```

### Web (from apps/web)
```bash
bun run dev | build | check | lint
bun run format         # biome format --write
```

### API (from apps/api, venv activated)
```bash
uvicorn app.main:app --reload --port 8000    # dev server
alembic upgrade head                          # run migrations
alembic revision --autogenerate -m "desc"     # generate migration
python scripts/seed_dev.py                    # seed dev data
celery -A app.worker.celery_app:celery_app worker -Q compute,reporting -l info
python -m app.reconciler                      # outbox reconciler
pytest                                        # run tests
ruff check . && ruff format .                 # lint + format
```

## Architecture

### Data Flow
Frontend (Next.js) → FastAPI (`/api/v1`) → Supabase Postgres (via SQLAlchemy async) → Outbox events in same transaction → Reconciler polls outbox → Redis → Celery workers (compute, reporting queues)

The frontend NEVER writes directly to DB — all writes go through FastAPI.

### Auth
- Production: Supabase JWT Bearer token, verified via JWKS (`app/security/supabase_jwt.py`)
- Dev fallback (`ALLOW_DEV_AUTH_FALLBACK=true`): API accepts `X-User-Id`, `X-Username`, `X-Institution-Id`, `X-Roles` headers without JWT
- Default dev user: `11111111-1111-1111-1111-111111111111`, role `SYSTEM_ADMIN`, institution `00000000-0000-0000-0000-000000000001`

### Multi-tenancy
Every resource has `institution_id`. All queries filter by it. JWT claims contain `institution_id`, extracted in `app/dependencies.py`.

### State Machine (RequestStatus)
```
CREATED → RECEIVING → STAGING → READY_TO_COMPUTE → COMPUTING → QC → REPORTING → [EXPERT_REVIEW →] FINAL
Terminal: FINAL, FAILED, CANCELLED
```
Each transition is role-gated (PHYSICIAN, TECHNICIAN, REVIEWER, SYSTEM_ADMIN). Logic in `app/services/state_machine.py`.

### Idempotency
Create endpoints accept `idempotency_key`. SHA-256 canonical JSON hash in `idempotency_keys` table. Same key + different payload = 409.

### Transactional Outbox
Domain writes + `outbox_events` insert in one DB transaction. Reconciler (`app/reconciler.py`) polls every 5s and dispatches to Redis.

### Key Backend Files
- `app/dependencies.py` — `AuthenticatedUser`, `DbSession` typed dependency aliases
- `app/api/v1/router.py` — aggregates all v1 routes
- `app/api/v1/requests.py` — full CRUD + lifecycle endpoints
- `app/models/base.py` — `UUIDMixin`, `TimestampMixin`, `Base`
- `app/config.py` — pydantic-settings config

### Key Frontend Files
- `app/layout.tsx` — root layout (`lang="ko"`)
- `components/providers.tsx` — TanStack Query provider (staleTime 15s, retry 1)
- `lib/api.ts` — typed fetch wrapper with auth headers
- `lib/supabase.ts` — Supabase browser client

## Code Conventions

### TypeScript
- Imports use `@/` alias (maps to `apps/web` root)
- Biome: lineWidth 100, 2-space indent, recommended rules
- `tsconfig.json`: strict, noUncheckedIndexedAccess, typedRoutes enabled
- `"use client"` directive required for components using hooks
- All user-facing text in Korean (ko-KR)

### Python
- Ruff: line-length 100, select E/F/I
- All models extend `UUIDMixin + TimestampMixin + Base`
- All DB writes must include outbox event in same transaction
- `SELECT ... FOR UPDATE` on state-changing endpoints
- Role check via `user.has_any_role(...)` before transitions

### Migrations
- Alembic for API schema; Supabase MCP tools for Supabase-side migrations
- Never hand-edit Supabase SQL migration files — always use `mcp__supabase__*` tools
- Additive changes only; never rename columns directly
- Add nullable first → backfill → add NOT NULL

## Supabase Storage Buckets
- `neurohub-inputs` — raw DICOM/file uploads
- `neurohub-outputs` — compute results
- `neurohub-reports` — PDF/JSON reports
- Path: `institutions/{institution_id}/requests/{request_id}/cases/{case_id}/{slot}/{filename}`
- All private; access via presigned URLs (15-min expiry)

## Deployment
- **Frontend**: Vercel
- **API**: `fly deploy` from `infra/fly/api` (release command runs `alembic upgrade head`)
- **Worker**: `fly deploy` from `infra/fly/worker`
- **Reconciler**: `fly deploy` from `infra/fly/reconciler`
- Deploy order: migrate → api → worker (never reverse)
- Secrets via `fly secrets set` — never commit to git

## Reference Docs
- Technical PRD (Korean): `docs/TECHNICAL_PRD_KR.md`
- Supabase setup: `docs/SUPABASE_SETUP_KR.md`
- Fly deployment: `docs/DEPLOYMENT_FLY_KR.md`
