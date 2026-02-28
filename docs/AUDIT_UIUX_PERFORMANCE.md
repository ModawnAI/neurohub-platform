# NeuroHub — UI/UX & Performance Audit

> Generated 2026-02-26. Covers `apps/web` (Next.js 16), `apps/api` (FastAPI), and infrastructure.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Frontend UI/UX](#2-frontend-uiux)
   - [Component Architecture](#21-component-architecture)
   - [Accessibility (WCAG 2.2 AA)](#22-accessibility)
   - [Responsive Design](#23-responsive-design)
   - [Loading & Skeleton States](#24-loading--skeleton-states)
   - [Error Handling (Frontend)](#25-error-handling-frontend)
   - [Navigation & Routing](#26-navigation--routing)
   - [Design System Consistency](#27-design-system-consistency)
   - [Internationalization](#28-internationalization)
   - [Animations & Transitions](#29-animations--transitions)
3. [Frontend Performance](#3-frontend-performance)
   - [Bundle & Code Splitting](#31-bundle--code-splitting)
   - [State Management & Caching](#32-state-management--caching)
   - [Re-render Hotspots](#33-re-render-hotspots)
4. [Backend Performance](#4-backend-performance)
   - [API Design](#41-api-design)
   - [Database & Query Optimization](#42-database--query-optimization)
   - [Caching Strategy](#43-caching-strategy)
   - [Async Patterns](#44-async-patterns)
   - [Connection Management](#45-connection-management)
5. [Backend Security & Reliability](#5-backend-security--reliability)
   - [Authentication & Authorization](#51-authentication--authorization)
   - [Rate Limiting](#52-rate-limiting)
   - [Error Handling (Backend)](#53-error-handling-backend)
   - [Celery & Workers](#54-celery--workers)
   - [Outbox & Reconciler](#55-outbox--reconciler)
   - [File Upload / Download](#56-file-upload--download)
   - [Health Checks](#57-health-checks)
6. [Infrastructure & DevOps](#6-infrastructure--devops)
7. [Prioritized Recommendations](#7-prioritized-recommendations)
8. [Scoreboard](#8-scoreboard)

---

## 1. Executive Summary

NeuroHub is a well-engineered medical AI platform with solid fundamentals: proper auth, role-based access, transactional outbox, structured logging, and Prometheus metrics. The frontend has good component organization, Korean-first i18n, and proper skeleton loaders.

**Key gaps** fall into three buckets:

| Bucket | Top Issue | Impact |
|--------|-----------|--------|
| **Accessibility** | Missing ARIA roles on tabs, pagination, dialogs | Blocks WCAG AA compliance |
| **Frontend Performance** | Sidebar re-renders on every route, unmemoized computations | Sluggish feel at scale |
| **Backend Performance** | No caching layer, offset pagination, missing FK indexes | Response time degrades with data growth |

**Overall Grade: B+** — production-ready with clear optimization paths.

---

## 2. Frontend UI/UX

### 2.1 Component Architecture

**Structure** (28 components, 3 role-based layouts):
```
apps/web/
├── app/(authenticated)/user/      # Patient/clinician views
├── app/(authenticated)/expert/    # Expert reviewer views
├── app/(authenticated)/admin/     # Admin dashboard
├── app/(public)/                  # Landing, login, register
├── components/                    # Shared UI components
│   ├── wizard/                    # Multi-step form system
│   └── dynamic-form/             # Schema-driven form renderer
└── lib/                          # Hooks, API client, i18n, schemas
```

**Strengths:**
- Clean separation of authenticated/public routes
- Reusable wizard system with localStorage draft persistence (`components/wizard/`)
- Schema-driven dynamic forms with conditional field visibility (`DynamicFormRenderer.tsx:34`)
- Optimistic mutation hook (`lib/use-optimistic-mutation.ts`)
- Virtual table with TanStack Virtual for large datasets (`components/virtual-table.tsx`)

**Issues:**

| # | Issue | File | Severity |
|---|-------|------|----------|
| F-01 | Status rendering duplicated — inline in `RequestCard` instead of reusing `StatusChip` | `request-card.tsx:37` vs `status-chip.tsx` | Low |
| F-02 | Inline dialog divs instead of reusable modal component | Multiple detail pages | Medium |
| F-03 | Form error display reimplemented per-page instead of centralized | Login, register, wizard pages | Low |
| F-04 | Some pages use inline `<span className="spinner">` instead of dedicated Spinner component | Various | Low |

---

### 2.2 Accessibility

**Strengths:**
- Skip-nav link to `#main-content` (`globals.css:73-97`)
- `RouteFocusManager` moves focus on navigation (`route-focus.tsx`)
- Focus-visible ring: 2px solid primary, 2px offset — WCAG 2.2 AA compliant
- Error messages use `role="alert"` and `aria-live="assertive"`
- Sidebar: `role="navigation"`, `aria-label`, `aria-current="page"`
- Skeleton loaders: `role="status"`, `aria-label`
- Mobile sidebar closes on Escape key (`sidebar.tsx:40`)
- Color contrast passes AA (e.g., `--text: #0f172a` on white)

**Issues:**

| # | Issue | File:Line | Fix |
|---|-------|-----------|-----|
| A-01 | Filter tabs missing `role="tablist"`, `role="tab"`, `aria-selected` | `user/requests/page.tsx:49-64` | Add ARIA tab roles |
| A-02 | Admin service tabs missing tab semantics | `admin/services/[id]/page.tsx:30-39` | Same fix |
| A-03 | Pagination missing `<nav aria-label="Pagination">` wrapper | `user/requests/page.tsx:83-100` | Wrap in semantic nav |
| A-04 | Notification dropdown items missing `role="menuitem"` | `notification-bell.tsx:76-80` | Add menuitem + keyboard nav |
| A-05 | Cornerstone DICOM fullscreen overlay not a proper `<dialog>` | `cornerstone-viewer.tsx:39` | Use dialog element or Radix Dialog |
| A-06 | Timeline dots lack screen reader descriptions | `timeline.tsx` | Add `aria-label` per step |

---

### 2.3 Responsive Design

**Breakpoints** (defined in `globals.css`):
```
≥1024px   Full sidebar (256px), full layout
769-1024  Reduced sidebar (200px)
≤768px    Mobile layout, hamburger toggle
≤480px    Extra-small text/spacing adjustments
```

**Strengths:**
- Sidebar collapses to hamburger on mobile, overlay on tap
- Grids collapse: `.grid-3` → 1-col, `.grid-2` → 1-col on mobile
- Tables scroll horizontally with `.table-wrap` and hide columns via `.hide-mobile`
- Dialogs use `min(560px, 92vw)` for safe width
- Font sizes use rem units

**Issues:**

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| R-01 | **Mobile nav disappears entirely** when sidebar is closed — no bottom nav or persistent drawer | **High** | Add persistent bottom nav bar on mobile |
| R-02 | Tables require horizontal scroll below 760px — poor mobile UX | Medium | Card layout for mobile, table for desktop |
| R-03 | Landing page feature grid stays 3-col on tablet | Low | `repeat(auto-fit, minmax(280px, 1fr))` |

---

### 2.4 Loading & Skeleton States

**Components available:**
- `SkeletonRow` — random-width placeholder rows
- `SkeletonTable` — multi-row table skeleton with `aria-label`
- `SkeletonCard` — title + description + meta
- `SkeletonCards` — grid of cards (default 3)
- CSS spinner: `@keyframes spin`, 0.6s rotation
- File upload progress bars with per-file %

**Issues:**

| # | Issue | File | Fix |
|---|-------|------|-----|
| L-01 | Notification dropdown shows blank while loading | `notification-bell.tsx:76` | Add skeleton dropdown |
| L-02 | Skeleton blocks don't pulse — static gray | `skeleton.tsx` | Add CSS `@keyframes pulse` animation |
| L-03 | File upload doesn't show which filename is uploading | `step-file-upload.tsx:74-80` | Show filename in progress UI |

---

### 2.5 Error Handling (Frontend)

**Architecture:**
- `ApiError` class with `status`, `code`, `message`, `detail` (`lib/api.ts:16-28`)
- `apiFetch` throws on non-2xx, caught by components
- Field-level Zod validation via `useZodForm` (`lib/use-zod-form.ts`)
- Global error page (`app/error.tsx`) with digest code and retry button
- 404 page with Korean text
- Toast notifications (5s auto-dismiss) for success/error

**Issues:**

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| E-01 | No error boundaries wrapping feature areas — one error can break entire page | Medium | Add `<ErrorBoundary>` per feature section |
| E-02 | No network timeout configuration — requests can hang indefinitely | Medium | Add `AbortController` timeout to `apiFetch` |
| E-03 | TanStack Query retry=1 with no backoff | Low | Add exponential backoff strategy |
| E-04 | Some error messages show technical codes instead of user-friendly Korean text | Low | Map all error codes to Korean messages |
| E-05 | No client-side error tracking (Sentry/LogRocket) | Low | Add error reporting service |

---

### 2.6 Navigation & Routing

**App Router structure** with role-based route groups:
```
(public)         → /login, /register, /onboarding, /auth/callback
(authenticated)  → /user/*, /expert/*, /admin/*
```

**Middleware** (`middleware.ts`): Checks `nh-onboarded` cookie, redirects by role.

**Strengths:**
- Active sidebar link via `aria-current="page"`
- Back button on detail pages using `useRouter().back()`
- Deep linking works for `/user/requests/[id]`, `/admin/services/[id]`

**Issues:**

| # | Issue | File | Fix |
|---|-------|------|-----|
| N-01 | **No breadcrumb navigation** on detail pages | All `[id]/page.tsx` files | Add `<Breadcrumb>` component |
| N-02 | Filter/tab state not persisted in URL — resets on refresh | `user/requests/page.tsx`, `admin/services/[id]` | Use `?status=QC&tab=input` URL params |
| N-03 | Admin service detail tabs don't update URL | `admin/services/[id]/page.tsx:47` | Push `?tab=pipeline` to URL |

---

### 2.7 Design System Consistency

**Color Tokens** (`globals.css:3-31`):
```css
--primary: #0b6bcb    --success: #16a34a    --warning: #d97706
--danger: #dc2626     --muted: #64748b      --text: #0f172a
--surface: #ffffff    --border: #e2e8f0
```

**Status Colors** — consistent BG/text pairs per state (CREATED→slate, COMPUTING→blue, FINAL→green, FAILED→red).

**Typography:**
- Font: `Noto Sans KR` → `Apple SD Gothic Neo` → `Malgun Gothic` → sans-serif
- Sizes: 11px (caption) → 22px (page title)
- Weights: 400–800

**Icons:** Phosphor React — consistent library, proper sizing (14/20/24), multiple weights.

**Spacing:** `.stack-lg` (20px), `.stack-md` (14px), `.stack-sm` (8px). Border radii: 8→20px.

**Issues:**

| # | Issue | Severity |
|---|-------|----------|
| D-01 | No dark mode — light only | Low |
| D-02 | Some inline `style={{}}` mixed with CSS classes | Low |
| D-03 | Magic numbers (500ms timeout in login, 30s poll interval) not in constants | Low |

---

### 2.8 Internationalization

**Implementation** (`lib/i18n/`):
- `ko.ts` (34KB) and `en.ts` (31KB) — extensive coverage
- `useT()` hook returns translation function
- Locale persisted in localStorage (`neurohub-locale`), defaults to `"ko"`
- Dates use `Intl.DateTimeFormat` with locale-aware formatting

**Issues:**

| # | Issue | Fix |
|---|-------|-----|
| I-01 | Language switcher only on auth pages, not in main app sidebar | Add to sidebar or header |
| I-02 | Some UI strings hardcoded in Korean (e.g., `"의료 영상 AI 분석"` in metadata) | Move to translation files |
| I-03 | No number/currency formatting (e.g., `1,000,000 KRW`) | Use `Intl.NumberFormat` |

---

### 2.9 Animations & Transitions

**Current:** Minimal — `0.15s ease` on background/border/shadow, CSS spinner, card hover shadow.

**Missing:**

| # | Missing Animation | Impact |
|---|-------------------|--------|
| AN-01 | Modal/dialog entrance (no fade-in) | Medium — feels abrupt |
| AN-02 | Toast slide-in/fade-out | Low |
| AN-03 | Mobile sidebar slide-from-left | Medium |
| AN-04 | Skeleton pulse animation | Low — feels static |
| AN-05 | Page route transitions | Low |

---

## 3. Frontend Performance

### 3.1 Bundle & Code Splitting

**Strengths:**
- Cornerstone DICOM libraries dynamically imported (`cornerstone-viewer.tsx:65-67`)
- WASM codec modules ignored at build time (`next.config.ts:20-24`)
- Phosphor icons tree-shakeable
- TanStack Virtual for large table rendering

**Issues:**

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| P-01 | No `next/dynamic` for heavy components like CornerstoneViewer | Medium | `dynamic(() => import('./cornerstone-viewer'), { ssr: false })` |
| P-02 | `ignoreBuildErrors: true` in next.config.ts hides type regressions | Medium | Fix type errors and re-enable |

---

### 3.2 State Management & Caching

**TanStack Query config** (`providers.tsx:16-17`):
```typescript
staleTime: 15_000,  // 15 seconds
retry: 1
```

**Query keys:** `["requests"]`, `["request", id]`, `["notifications"]` (30s poll), etc.

**Issues:**

| # | Issue | File | Fix |
|---|-------|------|-----|
| S-01 | **No query key namespacing** — admin `["requests"]` can collide with user `["requests"]` | Multiple files | Use `["admin", "requests"]` vs `["user", "requests"]` |
| S-02 | Creating a request doesn't invalidate related queries (e.g., service usage counts) | Mutation handlers | Add cross-query invalidation |
| S-03 | File uploads don't use optimistic UI — list doesn't update until refetch | Upload flow | Optimistically add file to cache |

---

### 3.3 Re-render Hotspots

| # | Component | Cause | File:Line | Fix |
|---|-----------|-------|-----------|-----|
| RE-01 | **Sidebar** | `usePathname()` triggers re-render on every route | `sidebar.tsx:23` | `React.memo()` + memoize callbacks |
| RE-02 | **Timeline** | `transitionMap` recalculated every render | `timeline.tsx:42-47` | Wrap in `useMemo` |
| RE-03 | **Mobile sidebar** | `setMobileOpen` in useEffect causes extra render | `sidebar.tsx:34-36` | Move to layout event handler |

---

## 4. Backend Performance

### 4.1 API Design

**Strengths:**
- RESTful resource-based endpoints under `/api/v1/`
- Proper HTTP methods and status codes (201, 404, 409, 422)
- Pagination with offset/limit, `has_more` flag, max 100 (`requests.py:349-377`)
- Idempotency keys with SHA-256 hash collision detection

**Issues:**

| # | Issue | File:Line | Impact | Fix |
|---|-------|-----------|--------|-----|
| API-01 | **Offset pagination** — degrades at large offsets (O(n) scan) | `requests.py:369` | High at >10K rows | Switch to keyset pagination using `(created_at, id)` |
| API-02 | Minimal filtering — only `status` on requests list | `requests.py:353` | Medium | Add date range, priority, patient_ref filters |
| API-03 | Response always includes all cases — no field exclusion | `requests.py:82` | Low | Add `?fields=` sparse fieldset support |

---

### 4.2 Database & Query Optimization

**Strengths:**
- Excellent index coverage — composite indexes on hot paths (`migrations/0004_add_indexes.py`)
- Partial indexes on `outbox` (unprocessed) and `runs` (stale) — highly efficient
- `FOR UPDATE` locking on state-changing endpoints (`requests.py:99-100`)
- Default `lazy="selectin"` on `Request.cases` relationship (`models/request.py:50-54`)
- Connection pool: `pool_size=20`, `max_overflow=10`, `pool_pre_ping=True`

**Issues:**

| # | Issue | File:Line | Impact | Fix |
|---|-------|-----------|--------|-----|
| DB-01 | **Missing FK indexes** on `Request.service_id`, `Request.pipeline_id`, `Run.case_id` | Models | Medium | Add migration with `CREATE INDEX` |
| DB-02 | **Inconsistent relationship loading** — some endpoints use explicit `selectinload`, others rely on model default | `reviews.py:101-104` vs `requests.py:349` | Medium | Always use explicit loading strategy per endpoint |
| DB-03 | **Multiple queries in request detail** — loads request then separate report query | `requests.py:405-414` | Low | Combine into single query or cache |
| DB-04 | **Patient access logs inserted per-case** in a loop | `requests.py:391-403` | Low | Batch with `db.add_all([...])` |
| DB-05 | Missing index on `(institution_id, status, display_name)` for service listing | `services.py:56-65` | Low | Add composite index |

---

### 4.3 Caching Strategy

**Currently cached:**
- JWT JWKS keys — in-memory, 300s TTL, asyncio.Lock protected (`supabase_jwt.py:48-70`)
- Rate limit counters — Redis ZSET with in-memory fallback (`rate_limit.py:72-93`)

**Not cached (should be):**

| # | Data | Read Frequency | Staleness OK? | Recommended TTL |
|---|------|----------------|---------------|-----------------|
| C-01 | Service definitions | Every request creation | Yes (changes rarely) | 1 hour, invalidate on update |
| C-02 | Pipeline definitions | Every request creation | Yes | 1 hour |
| C-03 | Request detail | Reviews, status checks | 30s acceptable | 30s, invalidate on state change |
| C-04 | Institution settings | Every authenticated request | Yes | 5 minutes |

**Estimated impact:** 40% reduction in DB queries for common flows.

---

### 4.4 Async Patterns

**Strengths:**
- Proper `async/await` throughout FastAPI handlers
- Celery tasks correctly use sync session factory (`worker/tasks.py:121-130`)
- `httpx.AsyncClient` for storage operations (`storage.py:22-46`)
- Database session lifecycle: auto-commit on success, auto-rollback on exception (`database.py:27-34`)

**Issues:**

| # | Issue | File:Line | Fix |
|---|-------|-----------|-----|
| AS-01 | **No global request timeout** — handlers can run indefinitely | `main.py` | Add `TimeoutMiddleware(timeout=30)` |
| AS-02 | **PDF generation has no timeout** — WeasyPrint can hang | `worker/tasks.py:315` | Add signal-based timeout (30s) |
| AS-03 | Pool size not configurable via env — hardcoded | `database.py:12-18` | Expose `POOL_SIZE`, `MAX_OVERFLOW` in Settings |

---

### 4.5 Connection Management

**Async pool** (FastAPI): `pool_size=20`, `max_overflow=10` — good for ~200 RPS.
**Sync pool** (Celery): `pool_size=5`, `max_overflow=5` — appropriate for worker count.

**Recommendation at scale:**

| Load | pool_size | max_overflow |
|------|-----------|--------------|
| <50 RPS | 10 | 5 |
| 50-200 RPS | 20 | 10 |
| 200-500 RPS | 40 | 20 |
| 500+ RPS | 80 | 40 |

---

## 5. Backend Security & Reliability

### 5.1 Authentication & Authorization

**Score: 9/10**

- **Three auth methods** with priority: API Key → JWT Bearer → Dev Fallback
- API key: constant-time comparison with `hmac.compare_digest` (`dependencies.py:156`)
- API key: prefix matching prevents full key exposure in logs
- JWT: Supabase JWKS verification with clock skew tolerance (30s)
- Dev fallback: only when `ALLOW_DEV_AUTH_FALLBACK=true` — cannot work in production
- Role-based access: `require_roles()` dependency on endpoints
- State machine transitions role-gated (`state_machine.py:22-39`)
- API key scopes for fine-grained access control
- **Zero raw SQL** — all queries parameterized via SQLAlchemy ORM

---

### 5.2 Rate Limiting

**Score: 9/10**

| Category | Unauth | Auth | Window |
|----------|--------|------|--------|
| auth | 10/min | 20/min | 60s |
| upload | 5/min | 30/min | 60s |
| write | 30/min | 120/min | 60s |
| read | 60/min | 300/min | 60s |

- Redis-backed sliding window (ZSET) with in-memory fallback
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Category`
- Skips health/metrics endpoints
- **Gap:** No per-API-key rate limits (only per-IP)

---

### 5.3 Error Handling (Backend)

**Score: 9/10**

- Custom `NeuroHubError` hierarchy: `NotFoundError`, `ConflictError`, `ForbiddenError`, etc.
- Global handlers for `HTTPException`, `RequestValidationError`, unhandled `Exception`
- All errors include `request_id` for correlation
- Never leaks internal details in production (generic 500 message)
- Structured JSON format: `{"error": "NOT_FOUND", "message": "...", "request_id": "..."}`

---

### 5.4 Celery & Workers

**Config strengths:**
- `worker_prefetch_multiplier=1` — prevents worker overload
- `task_acks_late=True` — failure-safe acknowledgement
- `visibility_timeout=3600` — 1hr for long tasks
- Separate queues: `compute`, `reporting`

**Issues:**

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| W-01 | **No task-level timeouts** — tasks can hang indefinitely | High | Add `task_time_limit=600`, `task_soft_time_limit=300` |
| W-02 | Inconsistent retry strategy — some use exponential backoff, some use fixed 10s | Medium | Standardize exponential backoff on all tasks |
| W-03 | Dead-lettered events only logged, never exported or alerted | Medium | Push to separate Redis queue + alert |

---

### 5.5 Outbox & Reconciler

**Score: 8/10** — transactionally sound implementation.

- Atomic: domain write + outbox event in single DB transaction
- Polling: every 5s, batch of 50, `FOR UPDATE SKIP LOCKED`
- Exponential backoff on failure: `5 * 2^retry_count` seconds
- Dead letter after max retries

**Issues:**

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| OB-01 | **Webhook delivery blocks reconciler loop** — 10s timeout × N webhooks | High | Dispatch webhooks via Celery task instead |
| OB-02 | **No distributed locking** — single reconciler instance only | Medium | Add Redlock for horizontal scaling |
| OB-03 | Event ordering not guaranteed per aggregate | Low | Order by `(aggregate_id, available_at)` |

---

### 5.6 File Upload / Download

**Score: 9/10**

- Presigned URLs (15-min expiry) — client uploads directly to Supabase Storage
- API never handles file bytes in request handlers
- SHA-256 checksums stored per file for integrity verification
- Private buckets — access only via signed URLs

**Gap:** No resumable/chunked upload support for very large DICOM files.

---

### 5.7 Health Checks

- `GET /api/v1/health` — basic liveness (always 200)
- `GET /api/v1/health/live` — TCP liveness probe
- `GET /api/v1/health/ready` — checks DB (`SELECT 1`) + Redis (`PING`), returns 503 if degraded

**Gap:** No Celery worker health check in readiness probe.

---

## 6. Infrastructure & DevOps

**Deployment:**
- Fly.io (nrt/Tokyo): API (1 CPU, 1GB), Worker (2 CPU, 2GB), Reconciler (1 CPU, 512MB)
- Vercel: Frontend auto-deploys
- Release command: `alembic upgrade head` before app start
- Rolling deployment strategy

**CI/CD** (GitHub Actions):
- `api-ci.yml`: Ruff lint → pytest with PostgreSQL 16 + Redis 7 services → pyright (non-blocking)
- `web-ci.yml`: Biome lint → tsc type check
- `deploy-api.yml`: Fly deploy on push to main

**Docker:** Multi-stage build (builder → runtime), non-root user, WeasyPrint system deps included.

**Issues:**

| # | Issue | Impact |
|---|-------|--------|
| INF-01 | `ignoreBuildErrors: true` in `next.config.ts` — type errors don't block deployment | Medium |
| INF-02 | `.env` file with Supabase credentials exists in repo (gitignored but risky) | Low — rotate keys |
| INF-03 | No Playwright E2E tests running in CI | Medium |
| INF-04 | pyright set to `continue-on-error: true` — Python type errors non-blocking | Low |

---

## 7. Prioritized Recommendations

### Critical (Do First)

| # | Recommendation | Area | Effort |
|---|---------------|------|--------|
| 1 | **Add persistent mobile navigation** (bottom nav bar or persistent drawer) | Frontend UX | 1 day |
| 2 | **Add ARIA tab/tablist roles** to filter buttons and admin service tabs | Accessibility | 0.5 day |
| 3 | **Add request timeout middleware** (30s) to prevent hung handlers | Backend | 0.5 day |
| 4 | **Add Celery task timeouts** (`soft=300s`, `hard=600s`) | Backend | 0.5 day |
| 5 | **Move webhook delivery out of reconciler loop** into Celery tasks | Backend | 1 day |

### High (Do Soon)

| # | Recommendation | Area | Effort |
|---|---------------|------|--------|
| 6 | **Switch to keyset pagination** for requests/runs endpoints | Backend | 1–2 days |
| 7 | **Add missing FK indexes** on `service_id`, `pipeline_id`, `run.case_id` | Backend | 0.5 day |
| 8 | **Cache service/pipeline definitions** in Redis (1hr TTL) | Backend | 1 day |
| 9 | **Namespace TanStack Query keys** (`["admin", "requests"]` vs `["user", "requests"]`) | Frontend | 0.5 day |
| 10 | **Add `<ErrorBoundary>` wrappers** around feature sections | Frontend | 0.5 day |
| 11 | **Persist filter/tab state in URL** query params | Frontend UX | 1 day |
| 12 | **Add breadcrumb navigation** to detail pages | Frontend UX | 1 day |

### Medium (Improve Quality)

| # | Recommendation | Area | Effort |
|---|---------------|------|--------|
| 13 | Add pagination `<nav aria-label>` wrapper | Accessibility | 0.5 day |
| 14 | Add `React.memo()` to Sidebar, `useMemo` to Timeline | Frontend Perf | 0.5 day |
| 15 | Add skeleton pulse animation (`@keyframes pulse`) | Frontend UX | 0.5 day |
| 16 | Batch patient access log inserts (`db.add_all`) | Backend Perf | 0.5 day |
| 17 | Add per-API-key rate limit buckets | Backend Security | 1 day |
| 18 | Add Redlock distributed locking for reconciler | Backend Reliability | 1 day |
| 19 | Use `next/dynamic` for CornerstoneViewer SSR skip | Frontend Perf | 0.5 day |
| 20 | Add network timeout to frontend `apiFetch` (AbortController) | Frontend Reliability | 0.5 day |

### Low (Nice to Have)

| # | Recommendation | Area |
|---|---------------|------|
| 21 | Add modal entrance/exit animations | UX Polish |
| 22 | Add mobile sidebar slide-in transition | UX Polish |
| 23 | Add dark mode support | UX |
| 24 | Add number/currency formatting with `Intl.NumberFormat` | i18n |
| 25 | Add language switcher to main sidebar | i18n |
| 26 | Add Sentry/error tracking integration | Observability |
| 27 | Re-enable TypeScript build errors in `next.config.ts` | CI Quality |
| 28 | Add Celery worker check to readiness probe | Health Checks |
| 29 | Add E2E Playwright tests to CI | Testing |
| 30 | Make DB pool size configurable via environment | Ops |

---

## 8. Scoreboard

| Category | Frontend | Backend |
|----------|----------|---------|
| **Architecture** | B+ | A- |
| **Accessibility** | B | — |
| **Responsive Design** | B+ | — |
| **UI/UX Consistency** | A- | — |
| **i18n** | A | — |
| **Loading States** | B | — |
| **Error Handling** | B+ | A |
| **Performance** | B | B+ |
| **Caching** | B | C+ |
| **Security** | — | A |
| **Rate Limiting** | — | A |
| **Async Patterns** | — | B+ |
| **Workers/Outbox** | — | B+ |
| **Observability** | — | A- |
| **CI/CD** | B | B+ |
| **Overall** | **B+** | **B+** |
