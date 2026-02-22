# NeuroHub

Medical AI workflow orchestration platform. Korean-first, multi-tenant, role-based.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router), React 19, TypeScript 5.7, Tailwind CSS 4, Radix UI |
| Backend | FastAPI, Python 3.11+, SQLAlchemy 2 (async), Pydantic v2, Alembic |
| Async | Celery + Redis, Transactional Outbox + Reconciler |
| Auth/DB/Storage | Supabase (Postgres, JWT Auth, Storage buckets) |
| Package Manager | Bun 1.2 (monorepo workspaces) |
| Deploy | Fly.io (API, Worker, Reconciler — nrt region), Vercel (Frontend) |

## Project Structure

```
NeuroHub/
├── apps/
│   ├── web/                  # Next.js frontend
│   │   ├── app/
│   │   │   ├── (public)/     # Landing, login, register, onboarding
│   │   │   └── (authenticated)/
│   │   │       ├── user/     # Dashboard, requests, new-request wizard, services, settings
│   │   │       ├── expert/   # Dashboard, review queue, review detail
│   │   │       └── admin/    # Dashboard, requests, users, orgs, services, API keys, audit logs
│   │   ├── components/       # Sidebar, wizard, notification bell, timeline, DICOM viewer
│   │   ├── lib/              # API client, Supabase client, i18n, hooks, Zod schemas
│   │   └── e2e/              # Playwright tests
│   └── api/                  # FastAPI backend
│       ├── app/
│       │   ├── api/v1/       # 14 route modules (28 endpoints)
│       │   ├── models/       # 14 SQLAlchemy models
│       │   ├── schemas/      # Pydantic request/response schemas
│       │   ├── services/     # State machine, storage, billing, notifications, webhooks
│       │   ├── middleware/    # Rate limiting, structured logging
│       │   ├── worker/       # Celery app + tasks
│       │   └── security/     # Supabase JWT verification (JWKS)
│       └── tests/            # 20 pytest test files
├── infra/                    # Fly.io deployment configs
└── docs/                     # Technical PRD, deployment guides, audit
```

## Getting Started

### Prerequisites

- [Bun](https://bun.sh) 1.2+
- Python 3.11+
- Supabase project (for DB/Auth/Storage)
- Redis (for Celery task queue)

### Frontend

```bash
# From repo root
bun install
bun run web:dev          # http://localhost:3000

# Other commands
bun run web:build        # Production build
bun run web:check        # TypeScript check
bun run web:lint         # Biome lint
```

### Backend

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Dev server
uvicorn app.main:app --reload --port 8000

# Migrations
alembic upgrade head

# Seed dev data
python scripts/seed_dev.py

# Tests
pytest

# Lint
ruff check . && ruff format .
```

### Environment Variables

Frontend (`apps/web/.env.local`):
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=
```

Backend (`apps/api/.env`):
```
DATABASE_URL=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
REDIS_URL=
ALLOW_DEV_AUTH_FALLBACK=true
```

## Features

### User Roles

- **Physician / Technician** — Submit analysis requests through a 6-step wizard, track status, view results
- **Expert Reviewer** — QC review queue, structured report review, approve/reject decisions
- **System Admin** — Platform overview, user management, organization management, service configuration, audit logs, API key management

### Request Lifecycle

```
CREATED → RECEIVING → STAGING → READY_TO_COMPUTE → COMPUTING → QC → REPORTING → [EXPERT_REVIEW →] FINAL
```

Each transition is role-gated. State machine enforced on the backend with `SELECT ... FOR UPDATE`.

### API (28 Endpoints)

- Health probes, auth, request CRUD + lifecycle
- File upload/download via Supabase Storage presigned URLs
- Service & pipeline catalog
- Organization & user management
- Admin stats, audit logs, notifications
- Billing/usage queries, review queue
- B2B API key auth for external integrations

### Frontend Pages

| Section | Pages |
|---------|-------|
| Public | Landing (KO/EN), Login, Register, Onboarding wizard |
| User | Dashboard, Request list, Request detail, New request (6-step wizard), Service catalog, Settings |
| Expert | Dashboard, Review queue, Review detail, Settings |
| Admin | Dashboard, Requests, Users, Organizations, Services, API keys, Audit logs, Settings |

### Internationalization

Full Korean/English support with 400+ translation keys. Language toggle available on all pages.

### Multi-tenancy

Every resource scoped by `institution_id`. All queries filter by tenant. JWT claims carry institution context.

## Architecture

### Data Flow

```
Frontend (Next.js) → FastAPI (/api/v1) → Supabase Postgres (SQLAlchemy async)
    → Outbox events in same transaction → Reconciler polls outbox → Redis → Celery workers
```

### Auth

- **Production**: Supabase JWT Bearer token, verified via JWKS
- **Dev**: Header-based fallback (`X-User-Id`, `X-Username`, `X-Institution-Id`, `X-Roles`)
- **B2B**: API key auth with `hmac.compare_digest`

### Transactional Outbox

Domain writes + outbox event insertion in a single DB transaction. Reconciler polls every 5s and dispatches to Redis for Celery workers.

## Testing

- **Backend**: 20 test files covering state machine, requests, uploads, rate limiting, exceptions, health, metrics, reconciler, webhooks, virus scanning, and more
- **Frontend**: Playwright E2E tests for landing page and dashboard flows

```bash
# Backend
cd apps/api && pytest

# Frontend E2E
cd apps/web && bunx playwright test
```

## Deployment

| Component | Platform | Region |
|-----------|----------|--------|
| API | Fly.io | nrt (Tokyo) |
| Worker | Fly.io | nrt |
| Reconciler | Fly.io | nrt |
| Frontend | Vercel | auto |
| Database | Supabase | managed |

Deploy order: migrate → API → worker (never reverse).

```bash
# API
fly deploy -c infra/fly/api/fly.toml

# Worker
fly deploy -c infra/fly/worker/fly.toml

# Frontend
vercel --prod
```

## Documentation

- [Technical PRD (Korean)](docs/TECHNICAL_PRD_KR.md)
- [Supabase Setup](docs/SUPABASE_SETUP_KR.md)
- [Fly.io Deployment](docs/DEPLOYMENT_FLY_KR.md)
- [Platform Audit & Roadmap](docs/AUDIT_AND_ROADMAP.md)

## License

Private. All rights reserved.
