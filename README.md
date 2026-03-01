# NeuroHub

Medical AI workflow orchestration platform for neuroimaging analysis. Korean-first, multi-tenant, role-based.

Supports end-to-end clinical pipelines: DICOM ingestion, BIDS conversion, Pre-QC validation, technique-level container execution, multi-technique fusion scoring, expert review, and PDF report generation.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router), React 19, TypeScript 5.7, Tailwind CSS 4, Radix UI, TanStack Query v5 |
| Backend | FastAPI, Python 3.11+, SQLAlchemy 2 (async), Pydantic v2, Alembic |
| Async | Celery + Redis, Transactional Outbox + Reconciler |
| Auth/DB/Storage | Supabase (Postgres, JWT Auth, Storage) or Self-hosted (PostgreSQL, MinIO, Local JWT) |
| Containers | Docker (ubuntu:22.04), host-mounted neuroimaging tools (FreeSurfer, FSL, MRtrix3, MATLAB/SPM25) |
| AI | Google Gemini 2.0 Flash (clinical AI agent) |
| Package Manager | Bun 1.2 (monorepo workspaces) |
| Deploy | Fly.io (API, Worker, Reconciler) + Vercel (Frontend), or self-hosted server |

## Project Structure

```
NeuroHub/
├── apps/
│   ├── web/                       # Next.js frontend
│   │   ├── app/
│   │   │   ├── (public)/          # Landing, login, register, onboarding
│   │   │   └── (authenticated)/
│   │   │       ├── user/          # Dashboard, requests, wizard, services, DICOM worklist,
│   │   │       │                  # group studies, marketplace, payment, reports, viewer
│   │   │       ├── expert/        # Dashboard, review queue, models, feedback, performance
│   │   │       └── admin/         # Dashboard, requests, users, orgs, services, API keys,
│   │   │                          # audit logs, model artifacts, techniques, DICOM gateway
│   │   ├── components/            # Sidebar, wizard, notification bell, timeline, NIfTI viewer,
│   │   │                          # Pre-QC viewer, technique results, fusion results, breadcrumb
│   │   ├── lib/                   # API client, Supabase client, i18n (600+ keys), hooks, Zod schemas
│   │   └── e2e/                   # Playwright E2E tests
│   └── api/                       # FastAPI backend
│       ├── app/
│       │   ├── api/v1/            # 25 route modules (60+ endpoints)
│       │   ├── models/            # 22 SQLAlchemy models
│       │   ├── schemas/           # Pydantic request/response schemas
│       │   ├── services/          # 29 service modules
│       │   ├── middleware/        # Rate limiting, structured logging, timeout
│       │   ├── worker/            # Celery tasks (compute, reporting, technique execution)
│       │   └── security/          # Supabase JWT (JWKS) + Local JWT (HS256)
│       ├── migrations/            # Alembic migrations
│       ├── scripts/               # Seed scripts (services, techniques, DICOM studies)
│       └── tests/                 # 36 pytest test files
├── containers/                    # Docker containers for neuroimaging analysis
│   ├── cortical-thickness/        # FreeSurfer-based cortical thickness analysis
│   ├── diffusion-properties/      # FSL/MRtrix3 diffusion tensor analysis
│   ├── tractography/              # MRtrix3 fiber tractography
│   └── fdg-pet/                   # MATLAB/SPM25 FDG-PET analysis (neuroan_pet)
├── infra/                         # Fly.io deployment configs
└── docs/                          # Technical PRD, deployment guides, audit reports
```

## Getting Started

### Prerequisites

- [Bun](https://bun.sh) 1.2+
- Python 3.11+
- Supabase project or self-hosted PostgreSQL + MinIO + Redis
- Redis (for Celery task queue)
- Docker (for container-based analysis pipelines)

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

# Seed data
python scripts/seed_dev.py          # Dev users + institutions
python scripts/seed_services.py     # 7 clinical services
python scripts/seed_techniques.py   # 21 technique modules

# Worker
celery -A app.worker.celery_app:celery_app worker -Q compute,reporting -l info

# Reconciler
python -m app.reconciler

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
API_ORIGIN=http://localhost:8000
```

Backend (`apps/api/.env`):
```
DATABASE_URL=postgresql+asyncpg://...
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
REDIS_URL=redis://localhost:6379/0
ALLOW_DEV_AUTH_FALLBACK=true
CONTAINER_EXECUTION_ENABLED=true
GEMINI_API_KEY=
```

## Features

### Clinical Analysis Pipeline

```
DICOM Ingest → BIDS Conversion → Pre-QC Validation → Technique Execution → Fusion Scoring → Expert Review → PDF Report
```

1. **DICOM Gateway** — Receive studies from PACS via STOW-RS, scan local directories, link to requests
2. **BIDS Conversion** — Automatic DICOM-to-BIDS conversion with dcm2niix
3. **Pre-QC Validation** — Automated quality checks per modality (MRI resolution, fMRI volumes, DTI gradients, PET SUV range)
4. **Technique Execution** — Fan-out to Docker containers, each running a specific neuroimaging analysis
5. **Fusion Engine** — Weighted aggregation of technique outputs per clinical service (e.g., Dementia = 0.20 FDG-PET + 0.25 Cortical Thickness + ...)
6. **Expert Review** — Structured review queue with accept/reject/revise decisions
7. **PDF Reports** — WeasyPrint-generated clinical reports with brain renderings

### Technique Modules (21 registered)

| Modality | Techniques |
|----------|-----------|
| MRI | Cortical Thickness, Volumetric Analysis, White Matter Lesion, Hippocampal Subfield, Cortical Gyrification |
| PET | FDG-PET, Amyloid PET, Tau PET |
| fMRI | Resting-State fMRI, Memory Encoding fMRI |
| DTI | Diffusion Properties, Tractography |
| EEG | Spectral Analysis, Source Localization, Memory Encoding EEG |
| MEG | Source Localization, Dynamic Causal Modeling |
| SPECT | Perfusion SPECT |
| PSG | Sleep Architecture |

### Docker Containers (4 built)

| Container | Base | Host-Mounted Tools | Output |
|-----------|------|-------------------|--------|
| `cortical-thickness` | ubuntu:22.04 | FreeSurfer 8.0 | 181 regional thickness features |
| `diffusion-properties` | ubuntu:22.04 | FSL, MRtrix3 | FA, MD, RD, AD maps |
| `tractography` | ubuntu:22.04 | MRtrix3, FreeSurfer | 5000 streamlines + connectivity |
| `fdg-pet` | ubuntu:22.04 | MATLAB R2025b, SPM25, neuroan_pet | Z-score maps, regional stats |

### Clinical Services (7 configured)

Each service maps to a weighted combination of technique modules:

- **Epilepsy Comprehensive** — MRI + EEG + PET + fMRI (6 techniques)
- **Dementia Comprehensive** — MRI + PET + DTI (6 techniques)
- **Parkinson's Disease** — MRI + PET + DTI (5 techniques)
- **Brain Tumor** — MRI + DTI (4 techniques)
- **Sleep Disorders** — EEG + PSG + MRI (4 techniques)
- **Stroke Evaluation** — MRI + SPECT + DTI (4 techniques)
- **Memory Disorders** — MRI + fMRI + EEG (5 techniques)

### User Roles

- **Physician / Technician** — Submit analysis requests via 6-step wizard, track status, view results, DICOM worklist
- **Expert Reviewer** — QC review queue, structured feedback with annotations, model performance tracking
- **System Admin** — Platform management, user/org admin, service configuration, technique management, DICOM gateway, audit logs, API keys

### Request Lifecycle (State Machine)

```
CREATED → RECEIVING → STAGING → READY_TO_COMPUTE → COMPUTING → QC → REPORTING → [EXPERT_REVIEW →] FINAL
Terminal: FINAL, FAILED, CANCELLED
```

Each transition is role-gated. State machine enforced on the backend with `SELECT ... FOR UPDATE`.

### AI Agent

Gemini 2.0 Flash-powered clinical AI agent that:
- Analyzes neuroimaging results with clinical context
- Generates structured interpretations
- Provides differential diagnosis suggestions
- Operates within medical AI safety guardrails

### Frontend Pages

| Section | Pages |
|---------|-------|
| Public | Landing (KO/EN), Login, Register, Onboarding wizard |
| User | Dashboard, Request list + detail, New request (6-step wizard), Service catalog, Marketplace + compare, DICOM worklist, Group studies, Payment (Toss), Reports, NIfTI viewer, Settings |
| Expert | Dashboard, Review queue, Model management (list/new/detail), Feedback evaluation, Performance metrics |
| Admin | Dashboard, Requests + detail (with pipeline progress), Users, Organizations, Services + detail, API keys, Audit logs, Model artifacts, Analysis techniques, DICOM gateway, Settings |

### API (60+ Endpoints across 25 route modules)

- Health probes, auth (Supabase JWT + Local JWT)
- Request CRUD + full lifecycle transitions
- File upload/download with validation (type, size, DICOM detection)
- DICOM gateway (list, link, create-from-DICOM)
- Technique modules CRUD, technique execution API
- Pre-QC results and overrides
- Service & pipeline catalog with technique weights
- Organization & user management
- Admin stats, audit logs, notifications
- Billing/usage, Toss Payments integration
- Expert review queue, evaluations, feedback
- Model artifacts (upload, scan, approve, deploy)
- B2B API key auth for external integrations
- Pipeline status and progress tracking
- Batch operations, group analysis

### Internationalization

Full Korean/English support with 600+ translation keys across 20+ namespaces. Language toggle on all pages. Korean-first UI.

### Multi-tenancy

Every resource scoped by `institution_id`. All queries filter by tenant. JWT claims carry institution context.

## Architecture

### Data Flow

```
Frontend (Next.js) → FastAPI (/api/v1) → PostgreSQL (SQLAlchemy async)
    → Outbox events in same transaction → Reconciler polls outbox → Redis → Celery workers
    → Docker containers (neuroimaging analysis) → Output parsing → Fusion scoring → Reports
```

### Auth

- **Production (Cloud)**: Supabase JWT Bearer token, verified via JWKS
- **Production (Self-hosted)**: Local JWT (HS256) via `app/security/local_jwt.py`
- **Dev**: Header-based fallback (`X-User-Id`, `X-Username`, `X-Institution-Id`, `X-Roles`)
- **B2B**: API key auth with `hmac.compare_digest`

### Container Execution

`LocalContainerRunner` orchestrates Docker containers on the self-hosted server:
- Host-mounts neuroimaging tools (FreeSurfer, FSL, MRtrix3, MATLAB/SPM25) as read-only volumes
- Mounts input data (BIDS format) and output directory
- Parses `NEUROHUB_OUTPUT: {json}` from container stdout
- Handles GPU allocation, memory limits, and timeout enforcement

### Transactional Outbox

Domain writes + outbox event insertion in a single DB transaction. Reconciler polls every 5s and dispatches to Redis for Celery workers.

### Pipeline Orchestrator

End-to-end case processing:
1. Smart zip extraction with DICOM detection
2. BIDS conversion (dcm2niix)
3. Pre-QC validation per modality
4. Fan-out technique execution (parallel Docker containers)
5. Fan-in fusion scoring (weighted aggregation)
6. Report generation

## Testing

- **Backend**: 36 test files covering state machine, requests, uploads, containers, techniques, fusion engine, pipeline orchestrator, zip processor, Pre-QC, AI agent, rate limiting, reconciler, webhooks, and more
- **Frontend**: Playwright E2E tests for admin requests, file validation, dashboard flows

```bash
# Backend
cd apps/api && pytest

# Frontend E2E
cd apps/web && bunx playwright test
```

## Deployment

### Cloud (Fly.io + Vercel)

| Component | Platform | Region |
|-----------|----------|--------|
| API | Fly.io | nrt (Tokyo) |
| Worker | Fly.io | nrt |
| Reconciler | Fly.io | nrt |
| Frontend | Vercel | auto |
| Database | Supabase | managed |

Deploy order: migrate → API → worker (never reverse).

```bash
# API (from apps/api)
fly deploy --remote-only

# Worker
fly deploy -c infra/fly/worker/fly.toml

# Frontend
vercel --prod
```

### Self-Hosted Server

Server runs all services on a single machine with GPU access for neuroimaging analysis.

```bash
# Start all services
bash scripts/start-all.sh

# Services: PostgreSQL (:5433), Redis (:6380), MinIO (:9000), FastAPI (:8080), Next.js (:3000)
```

## Documentation

- [Technical PRD (Korean)](docs/TECHNICAL_PRD_KR.md)
- [Supabase Setup](docs/SUPABASE_SETUP_KR.md)
- [Fly.io Deployment](docs/DEPLOYMENT_FLY_KR.md)
- [Platform Audit & Roadmap](docs/AUDIT_AND_ROADMAP.md)
- [UX/UI Performance Audit](docs/AUDIT_UIUX_PERFORMANCE.md)

## License

Private. All rights reserved.
