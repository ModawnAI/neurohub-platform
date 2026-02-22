# NeuroHub Platform Audit & Roadmap

**Date**: 2026-02-22
**Scope**: Full-stack audit against `TECHNICAL_PRD_KR.md`
**Status**: Post-Phase 1–17 implementation, all 28 API endpoints live on Fly.io

---

## Table of Contents

1. [Current State Summary](#1-current-state-summary)
2. [Backend Audit](#2-backend-audit)
3. [Frontend Audit](#3-frontend-audit)
4. [PRD Coverage Matrix](#4-prd-coverage-matrix)
5. [Database & Security Audit](#5-database--security-audit)
6. [Prioritized Roadmap](#6-prioritized-roadmap)

---

## 1. Current State Summary

### What's Built

**Backend (FastAPI)** — 28 live endpoints on `neurohub-api.fly.dev`
- Health: `/health`, `/health/live`, `/health/ready`
- Auth: `/auth/me`
- Requests: full CRUD + lifecycle (create, list, get, transition, confirm, submit, cancel)
- Uploads: presign, complete, list cases, list files, download
- Services: list services, list pipelines
- Organizations: list, list members
- Users: list, get by ID
- Admin: stats, all requests, audit logs
- Notifications: list, read-all
- Billing: usage query
- Reviews: review queue
- API Keys: list, create
- B2B: create request, get request, presign upload, complete upload

**Frontend (Next.js 16)** — Deployed on Vercel
- Landing page with responsive nav, hero, features, pricing, footer
- Auth: login, register, onboarding wizard
- User role: dashboard, 6-step new request wizard, request list, request detail, service catalog, settings
- Expert role: dashboard, review queue, review detail
- Admin role: dashboard, requests overview, users management, organizations, services
- Shared: sidebar layout, notification bell, language switcher, timeline, error boundary

**Infrastructure**
- Fly.io: 3 process types (app, worker, reconciler) × 2 machines = 6 machines
- Supabase: 23 tables, 3 Alembic migrations applied
- Dev auth bypass for testing

### Deployment Verification (2026-02-22)

All 28 endpoints tested against live Fly.io API — **28/28 PASS**.

---

## 2. Backend Audit

### 2.1 Scores

| Area | Score | Notes |
|------|-------|-------|
| API Design | 3.5/5 | Solid REST patterns, missing input validation depth |
| DB Schema | 3.5/5 | Good normalization, missing indexes + RLS |
| Security | 2.5/5 | Auth works, missing rate limiting (production), HIPAA gaps |
| Error Handling | 2/5 | No global exception handler, inconsistent error shapes |
| Testing | 3/5 | 48 unit tests pass, 31 DB-dependent tests need local Supabase |
| Observability | 1.5/5 | Structured logging middleware exists but no metrics/tracing |
| Production Readiness | 2.5/5 | Running on Fly.io, but missing health check depth + graceful shutdown |

### 2.2 Critical Gaps

#### Input Validation
- **Missing**: Request body size limits, file size enforcement at API level, content-type whitelist for DICOM uploads
- **Impact**: Potential abuse via oversized payloads
- **Fix**: Add Pydantic validators + FastAPI request size middleware

#### Global Exception Handler
- **Current**: Each endpoint catches its own errors inconsistently
- **Missing**: Centralized `@app.exception_handler` for `NeuroHubError`, `RequestValidationError`, unhandled exceptions
- **Impact**: Inconsistent error response shapes, stack traces leaking in production
- **Fix**: Create `app/exceptions.py` with `NeuroHubError` hierarchy, register handler in `main.py`

#### Rate Limiting
- **Current**: `app/middleware/rate_limit.py` uses in-memory dict (resets on deploy)
- **Missing**: Redis-backed sliding window
- **Impact**: No real rate limiting in multi-machine Fly.io deployment
- **Fix**: Use Redis ZRANGEBYSCORE pattern

#### Database Indexes
- **Missing indexes on hot query paths**:
  - `requests(institution_id, status)` — every list query
  - `requests(institution_id, created_at DESC)` — sorted listing
  - `outbox_events(processed_at, created_at)` — reconciler polling
  - `audit_logs(institution_id, created_at DESC)` — admin queries
  - `usage_ledger(institution_id, created_at)` — billing aggregation
  - `runs(status, heartbeat_at)` — stale run detection
- **Impact**: Full table scans as data grows
- **Fix**: Alembic migration `0004_add_indexes`

#### HIPAA/Medical Compliance
- **Missing**: `patient_access_logs` never written to
- **Missing**: PHI field encryption at rest
- **Missing**: Audit log for file downloads
- **Impact**: Non-compliant for production medical use
- **Fix**: Wire `patient_access_logs` into upload/download endpoints, add encryption service

#### API Key Auth Hardening
- **Current**: B2B API key auth works but missing:
  - Key rotation (create new → deprecate old)
  - Scope-based permissions (read-only vs full)
  - Usage quota per key
- **Fix**: Add `scopes` column to `institution_api_keys`, enforce in dependency

### 2.3 Medium Priority

| Issue | Current State | Recommendation |
|-------|--------------|----------------|
| Celery task error handling | Basic try/catch | Add `on_failure` callback, DLQ for failed tasks |
| Report generation | Stub JSON report | Implement actual template rendering (WeasyPrint for PDF) |
| QC decision validation | Accepts any JSON | Define QC criteria schema per service/pipeline |
| File checksum verification | SHA-256 stored but not verified against storage | Add post-upload verification step |
| Graceful shutdown | `kill_signal = SIGINT` | Add signal handler for in-progress requests |
| Config validation | Pydantic settings | Add startup checks for required external services |
| Webhook support | Not implemented | PRD mentions webhook notifications for B2B |

---

## 3. Frontend Audit

### 3.1 Scores

| Area | Score | Notes |
|------|-------|-------|
| Architecture | 8/10 | Clean App Router structure, proper role-based layouts |
| Completeness | 4/10 | Core flows exist, many admin features stub/missing |
| Accessibility | 2/10 | No ARIA labels, no focus management, no skip links |
| UX/Polish | 5/10 | Functional but sparse — missing loading states, empty states |
| Performance | 5/10 | No image optimization, no route prefetch, no virtual scroll |
| Code Quality | 7/10 | TypeScript strict, consistent patterns, Biome-clean |
| Medical Readiness | 2/10 | No DICOM viewer, no structured report view |

### 3.2 Critical Missing Features

#### DICOM Viewer
- **PRD**: "DICOM 뷰어 또는 파일 미리보기" (Section 16)
- **Current**: File list shows names only, no preview capability
- **Recommendation**: Integrate Cornerstone.js or OHIF Viewer as embedded component
- **Effort**: Large (3-5 days)

#### Organization Management UI
- **PRD**: Full org CRUD, member invite/remove, role assignment
- **Current**: Admin org page lists orgs in a table, no edit/create/invite
- **Missing pages**: `/admin/organizations/[id]` (detail + members), invite modal, role editor
- **Effort**: Medium (1-2 days)

#### Service Management UI
- **PRD**: Create/edit/deactivate services and pipelines
- **Current**: Admin services page is read-only list
- **Missing**: Create service modal, edit modal, deactivate toggle, pipeline configuration
- **Effort**: Medium (1-2 days)

#### Report Download & Viewing
- **PRD**: "리포트 PDF/JSON 다운로드" (Section 16)
- **Current**: No report viewing or download functionality
- **Missing**: Report detail page, PDF render, download button
- **Effort**: Medium (1-2 days, depends on backend PDF generation)

#### Expert Review Flow
- **PRD**: Full QC decision + report review with structured forms
- **Current**: Basic QC approve/reject exists, report review is minimal
- **Missing**: Structured QC criteria display, comparison view, revision tracking
- **Effort**: Medium (2-3 days)

### 3.3 UX Gaps

| Issue | Current | Recommendation |
|-------|---------|----------------|
| Empty states | Generic "no data" text | Illustrated empty states with CTAs |
| Loading states | Spinner only | Skeleton loaders for tables and cards |
| Form validation feedback | Inline text errors | Shake animation + field highlighting |
| Optimistic updates | None | TanStack Query `onMutate` for status transitions |
| Mobile responsiveness | Landing page only | All authenticated pages need responsive layouts |
| Dark mode | Not implemented | PRD doesn't require, but Tailwind v4 makes it trivial |
| Toast notifications | Not implemented | Add Radix Toast for mutation confirmations |
| Keyboard shortcuts | None | `Cmd+K` command palette for power users |

### 3.4 Accessibility (WCAG 2.1 AA)

- **Missing**: `aria-label` on all icon-only buttons
- **Missing**: `:focus-visible` ring styles (currently no visible focus indicator)
- **Missing**: Skip navigation link
- **Missing**: `aria-live` regions for dynamic content (notifications, status changes)
- **Missing**: Proper heading hierarchy (some pages jump from h1 to h4)
- **Missing**: Color contrast verification (some gray text may fail 4.5:1)
- **Missing**: Form labels associated with inputs via `htmlFor`

### 3.5 Performance

| Issue | Fix | Impact |
|-------|-----|--------|
| No virtual scrolling | `@tanstack/react-virtual` for admin tables | High for 1000+ row tables |
| No route prefetching | Next.js `<Link prefetch>` on nav items | Medium — faster navigation |
| Large bundle size | Dynamic imports for wizard steps, DICOM viewer | Medium |
| No image optimization | `next/image` for landing page | Low |
| API waterfall | Parallel queries in dashboard pages | Medium |

---

## 4. PRD Coverage Matrix

### Section-by-Section Coverage

| PRD Section | Coverage | Key Gaps |
|-------------|----------|----------|
| §9 Data Model | 85% | `report_reviews` table exists but not fully wired; `patient_access_logs` never written |
| §10 State Machine | 90% | All transitions implemented; missing: timeout-based auto-cancellation |
| §11 API Contract | 75% | All CRUD endpoints exist; missing: webhook endpoints, batch operations |
| §12 Auth & RBAC | 70% | JWT + dev fallback + API key works; missing: key rotation, scope-based permissions, RLS policies |
| §13 Storage | 60% | Presigned upload/download works; missing: virus scanning, file type validation, quota enforcement |
| §14 Transactions | 80% | Outbox pattern implemented; missing: SELECT FOR UPDATE on some mutation paths |
| §15 Worker/Reconciler | 70% | Outbox dispatch + stale runs + ledger consistency; missing: priority queues, actual compute integration |
| §16 Frontend | 50% | Core pages exist; missing: DICOM viewer, report view, org management, service CRUD, full expert flow |
| §17 Deployment | 80% | Fly.io running; missing: CI/CD pipelines, security scanning, structured logging to external service |
| §18 Testing | 40% | Unit tests exist; missing: integration tests with real DB, E2E tests, load tests |

### Feature Completion Detail

```
[████████░░] 80%  Request lifecycle (create → final)
[████████░░] 80%  File upload pipeline
[██████░░░░] 60%  QC review flow
[████░░░░░░] 40%  Report generation + viewing
[██████░░░░] 60%  Expert review flow
[████████░░] 80%  Multi-tenancy isolation
[██████░░░░] 60%  B2B API key auth
[████░░░░░░] 40%  Billing/usage tracking
[██░░░░░░░░] 20%  Notification system (backend only, no real-time)
[████████░░] 80%  Admin dashboard
[████░░░░░░] 40%  Admin organization management
[████░░░░░░] 40%  Admin service management
[██░░░░░░░░] 20%  Audit trail completeness
[░░░░░░░░░░]  0%  CI/CD pipelines
[░░░░░░░░░░]  0%  RLS policies
[░░░░░░░░░░]  0%  E2E tests
[░░░░░░░░░░]  0%  DICOM viewer
[░░░░░░░░░░]  0%  Webhook notifications
```

---

## 5. Database & Security Audit

### 5.1 Schema Status

23 tables exist. All 3 Alembic migrations applied. Seed data present.

### 5.2 Missing RLS Policies

**No RLS policies are currently active.** This is the single biggest security gap.

Tables requiring RLS:
- `requests` — `institution_id = current_institution_id()`
- `cases`, `case_files` — via request join
- `runs`, `run_steps` — via request join
- `reports`, `report_reviews` — via request join
- `qc_decisions` — via request join
- `audit_logs` — `institution_id` filter
- `notifications` — `user_id` filter
- `usage_ledger` — `institution_id` filter
- `institution_members` — `institution_id` filter
- `institution_api_keys` — `institution_id` filter
- `patient_access_logs` — `institution_id` filter

**Priority**: P0 for production. Without RLS, a compromised API server leaks all tenant data.

### 5.3 Missing Indexes

```sql
-- Hot query paths
CREATE INDEX idx_requests_institution_status ON requests(institution_id, status);
CREATE INDEX idx_requests_institution_created ON requests(institution_id, created_at DESC);
CREATE INDEX idx_outbox_unprocessed ON outbox_events(processed_at, created_at) WHERE processed_at IS NULL;
CREATE INDEX idx_audit_logs_institution ON audit_logs(institution_id, created_at DESC);
CREATE INDEX idx_usage_ledger_institution ON usage_ledger(institution_id, created_at);
CREATE INDEX idx_runs_stale ON runs(status, heartbeat_at) WHERE status = 'RUNNING';
CREATE INDEX idx_notifications_user ON notifications(user_id, read_at) WHERE read_at IS NULL;
CREATE INDEX idx_cases_request ON cases(request_id);
CREATE INDEX idx_case_files_case ON case_files(case_id);
```

### 5.4 Security Checklist

| Item | Status | Notes |
|------|--------|-------|
| JWT verification | Done | JWKS-based verification via `supabase_jwt.py` |
| API key constant-time compare | Done | `hmac.compare_digest` in `dependencies.py` |
| Multi-tenant query isolation | Done | All queries filter by `institution_id` |
| RLS as defense-in-depth | Missing | No policies on any table |
| Rate limiting (production) | Missing | In-memory only, resets on deploy |
| Input sanitization | Partial | Pydantic validates types, no content scanning |
| CORS configuration | Done | Configured in `main.py` |
| File upload scanning | Missing | No virus/malware scan on uploaded files |
| PHI encryption at rest | Missing | Supabase encrypts disk but no column-level encryption |
| Audit trail for data access | Missing | `patient_access_logs` table unused |
| Secret rotation | Missing | No key rotation mechanism |
| HTTPS enforcement | Done | `force_https = true` in fly.toml |

---

## 6. Prioritized Roadmap

### P0 — Security & Data Integrity (Must-have for production)

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1 | Apply RLS policies to all tenant-scoped tables | 1 day | Prevents cross-tenant data leakage |
| 2 | Add database indexes for hot query paths | 0.5 day | Prevents performance degradation at scale |
| 3 | Global exception handler + standardized error responses | 0.5 day | Consistent API behavior, no stack trace leaks |
| 4 | Redis-backed rate limiting | 0.5 day | Actual rate limiting in multi-machine deployment |
| 5 | Wire `patient_access_logs` into upload/download | 0.5 day | HIPAA audit trail compliance |

### P1 — Core Feature Gaps

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 6 | Report generation (PDF via WeasyPrint) | 2 days | Completes the analysis lifecycle |
| 7 | Expert review flow (structured QC criteria, comparison view) | 2 days | Core workflow for medical reviewers |
| 8 | Organization management UI (create, edit, invite members) | 1.5 days | Admin can manage tenants |
| 9 | Service management UI (create, edit, deactivate) | 1 day | Admin can configure AI services |
| 10 | API key rotation + scope-based permissions | 1 day | B2B customers can manage access |

### P2 — UX & Polish

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 11 | WCAG 2.1 AA accessibility (focus, ARIA, skip nav) | 1.5 days | Medical software compliance |
| 12 | Skeleton loaders + empty states + toast notifications | 1 day | Professional UX |
| 13 | Mobile responsive authenticated pages | 1.5 days | Usable on tablets in clinical settings |
| 14 | Virtual scrolling for admin tables | 0.5 day | Performance with large datasets |
| 15 | Optimistic updates for status transitions | 0.5 day | Snappier UI |

### P3 — Infrastructure & Testing

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 16 | CI/CD: GitHub Actions for API deploy + tests | 1 day | Automated deployment pipeline |
| 17 | Integration tests with Supabase test project | 1.5 days | Confidence in DB-dependent code |
| 18 | Structured JSON logging to external service | 0.5 day | Production debugging |
| 19 | Prometheus metrics + `/metrics` endpoint | 0.5 day | Observability |
| 20 | E2E tests (Playwright) for critical flows | 2 days | Regression prevention |

### P4 — Advanced Features

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 21 | DICOM viewer integration (Cornerstone.js) | 3-5 days | Medical image preview in-browser |
| 22 | Webhook notifications for B2B partners | 1.5 days | Event-driven integrations |
| 23 | File upload virus scanning (ClamAV) | 1 day | Security for uploaded files |
| 24 | Batch request creation API | 1 day | B2B bulk workflows |
| 25 | Auto-cancellation of stale CREATED requests | 0.5 day | Data hygiene |

### Total Estimated Effort

| Priority | Tasks | Effort |
|----------|-------|--------|
| P0 | 5 tasks | ~3 days |
| P1 | 5 tasks | ~7.5 days |
| P2 | 5 tasks | ~5 days |
| P3 | 5 tasks | ~5.5 days |
| P4 | 5 tasks | ~7-9 days |
| **Total** | **25 tasks** | **~28-30 days** |

---

## Appendix A: File Inventory

### Backend (`apps/api/`)
```
app/
├── main.py                    # FastAPI app, middleware, CORS
├── config.py                  # Pydantic settings
├── database.py                # SQLAlchemy async engine + session
├── dependencies.py            # Auth (JWT/API key/dev fallback), DB session
├── exceptions.py              # Custom exception classes (stub)
├── reconciler.py              # Outbox dispatch + stale runs + ledger
├── api/v1/
│   ├── router.py              # Route aggregator
│   ├── requests.py            # Request CRUD + lifecycle
│   ├── uploads.py             # File upload/download
│   ├── services.py            # Service/pipeline listing
│   ├── organizations.py       # Org + members
│   ├── users.py               # User management
│   ├── admin.py               # Admin stats/requests/audit
│   ├── health.py              # Health probes
│   ├── auth.py                # /auth/me
│   ├── notifications.py       # Notification CRUD
│   ├── billing.py             # Usage queries
│   ├── reviews.py             # Review queue
│   ├── api_keys.py            # API key management
│   └── b2b.py                 # B2B endpoints
├── models/                    # 20+ SQLAlchemy models
├── schemas/                   # Pydantic request/response schemas
├── services/                  # Business logic (state machine, storage, billing, notifications)
├── middleware/                 # Rate limiting, logging
├── worker/                    # Celery app + tasks
└── security/                  # JWT verification
```

### Frontend (`apps/web/`)
```
app/
├── layout.tsx                 # Root layout (ko, fonts)
├── error.tsx                  # Global error boundary
├── (public)/                  # Landing, login, register, onboarding
├── (authenticated)/
│   ├── user/                  # Dashboard, requests, new-request wizard, services, settings
│   ├── expert/                # Dashboard, review queue, review detail
│   └── admin/                 # Dashboard, requests, users, organizations, services
components/
├── sidebar.tsx                # Role-based sidebar
├── notification-bell.tsx      # Notification indicator
├── language-switcher.tsx      # ko/en toggle
├── timeline.tsx               # Request status timeline
└── wizard/                    # 6-step request wizard components
lib/
├── api.ts                     # Typed fetch wrapper
├── supabase.ts                # Browser client
├── schemas.ts                 # Zod validation schemas
├── use-wizard.ts              # Wizard state management
├── use-notifications.ts       # Notification polling hook
└── i18n/                      # Korean/English translations
```

---

## Appendix B: Environment & Deploy

| Component | Platform | Region | URL |
|-----------|----------|--------|-----|
| API | Fly.io | nrt (Tokyo) | `neurohub-api.fly.dev` |
| Worker | Fly.io | nrt | (internal) |
| Reconciler | Fly.io | nrt | (internal) |
| Frontend | Vercel | auto | TBD |
| Database | Supabase | — | (managed) |
| Cache/Queue | Redis | — | (Fly.io addon or external) |
