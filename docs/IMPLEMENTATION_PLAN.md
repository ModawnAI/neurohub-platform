# NeuroHub: Services, Evaluations, Payments & Downloads — Implementation Plan

> **Date**: 2026-02-24
> **Status**: Implementation In Progress (Phases 1–12 complete, Phase 13–14 in progress)
> **Scope**: 4 features across 14 new files and 20 modified files

---

## Table of Contents

1. [Context & Goals](#1-context--goals)
2. [Architecture Overview](#2-architecture-overview)
3. [Phase 1: Database Schema (Alembic Migration 0008)](#3-phase-1-database-schema)
4. [Phase 2: Backend — Service Flexibility](#4-phase-2-backend--service-flexibility)
5. [Phase 3: Backend — Evaluations](#5-phase-3-backend--evaluations)
6. [Phase 4: Backend — Watermark Task](#6-phase-4-backend--watermark-task)
7. [Phase 5: Backend — PDF Report Generation](#7-phase-5-backend--pdf-report-generation)
8. [Phase 6: Backend — Toss Payments](#8-phase-6-backend--toss-payments)
9. [Phase 7: Frontend — API Client & Types](#9-phase-7-frontend--api-client--types)
10. [Phase 8: Frontend — Admin Service Creation](#10-phase-8-frontend--admin-service-creation)
11. [Phase 9: Frontend — Evaluator Pages](#11-phase-9-frontend--evaluator-pages)
12. [Phase 10: Frontend — Download Buttons](#12-phase-10-frontend--download-buttons)
13. [Phase 11: Frontend — Payment Pages](#13-phase-11-frontend--payment-pages)
14. [Phase 12: i18n](#14-phase-12-i18n)
15. [Phase 13: Demo Seed Data](#15-phase-13-demo-seed-data)
16. [Phase 14: Dependencies & Config](#16-phase-14-dependencies--config)
17. [Data Flow Diagrams](#17-data-flow-diagrams)
18. [File Summary](#18-file-summary)
19. [Verification Plan](#19-verification-plan)
20. [Key Patterns & Decisions](#20-key-patterns--decisions)

---

## 1. Context & Goals

NeuroHub is a Korean-first medical AI workflow orchestration platform with an existing pipeline:

```
Request → Compute → QC → Report → FINAL
```

The platform currently lacks:
- A demo service that showcases **human-in-the-loop** evaluation with image watermarking
- **Flexible service creation** supporting multimodal inputs and automatic vs human-reviewed modes
- **PDF report generation** and watermarked file downloads
- **Payment integration** (Toss Payments) for service fees

### Features Being Added

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Demo Watermark Service** | Users upload JPEG → evaluator reviews/approves/rejects → approved files get watermarked → user notified |
| 2 | **Flexible Service Creation** | Admin creates services with diverse data structures, multimodal file types, automatic or human-in-the-loop modes, evaluator assignment |
| 3 | **Report & Watermarked Download** | After notification, users download report as PDF and watermarked file |
| 4 | **Toss Payments Integration** | Card, Apple Pay, Google Pay, bank transfer payments with demo pages |

### Design Principles

- Build incrementally on existing patterns (outbox, state machine, Supabase storage, Celery workers)
- No state machine changes needed — HUMAN_IN_LOOP services reuse the existing QC step
- Additive-only database migrations (nullable first → backfill → NOT NULL)
- All UI text localized (Korean primary, English secondary)
- Multi-tenancy enforced on all new tables via `institution_id`

---

## 2. Architecture Overview

### Evaluation Workflow (Feature 1)

```
┌────────────┐     ┌──────────┐     ┌─────────────┐     ┌──────────────┐
│  Request    │────▶│  QC      │────▶│ Evaluator    │────▶│ Watermark    │
│  (COMPUTING)│     │  Status  │     │ Decision     │     │ Celery Task  │
└────────────┘     └──────────┘     └─────────────┘     └──────────────┘
                                         │                      │
                                    ┌────┴────┐            ┌────┴────┐
                                    │APPROVE  │            │Upload to│
                                    │REJECT   │            │Storage  │
                                    │REVISION │            └────┬────┘
                                    └─────────┘                 │
                                                           ┌────┴────┐
                                                           │Generate │
                                                           │PDF      │
                                                           │Report   │
                                                           └─────────┘
```

### Payment Workflow (Feature 4)

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌───────────┐
│  Select   │────▶│ Prepare  │────▶│ Toss Payment │────▶│  Confirm  │
│  Service  │     │ (Backend)│     │ Widget (SDK) │     │  (Backend)│
└──────────┘     └──────────┘     └──────────────┘     └───────────┘
                      │                   │                    │
                 Create Payment      User pays           Verify amount
                 (PENDING)           via Toss             Call Toss API
                 Return order_id     Redirect to          Update CONFIRMED
                                     success/fail
```

### Technology Choices

| Component | Choice | Reason |
|-----------|--------|--------|
| Image watermark | **Pillow** | Pure Python, no system deps |
| PDF generation | **reportlab** | Avoids cairo/pango system deps on Fly.io Docker |
| Payment gateway | **Toss Payments V2** | Korean payment ecosystem, supports card/Apple Pay/Google Pay/transfer |
| Task queue | **Celery + Redis** (existing) | Reuse existing infrastructure |
| Storage | **Supabase Storage** (existing) | Presigned URLs, existing bucket structure |

---

## 3. Phase 1: Database Schema

**Migration file**: `apps/api/migrations/versions/0008_services_evaluations_payments.py`

### 3.1 New Columns on `service_definitions`

| Column | Type | Default | Nullable | Purpose |
|--------|------|---------|----------|---------|
| `outputs_schema` | JSONB | null | Yes | JSON Schema for service outputs |
| `service_type` | String(30) | `"AUTOMATIC"` | No | `AUTOMATIC` or `HUMAN_IN_LOOP` |
| `unit_price_krw` | Numeric(18,2) | `0` | No | Price per run in KRW |
| `accepted_file_types` | JSONB | null | Yes | e.g. `["image/jpeg","image/png"]` |
| `requires_evaluator` | Boolean | `false` | No | Whether evaluator must review |

**Migration strategy**: Columns added nullable first, then backfilled with defaults, then NOT NULL constraint applied.

### 3.2 New Column on `reports`

| Column | Type | Purpose |
|--------|------|---------|
| `watermarked_storage_path` | String(1000), nullable | Path to watermarked output file in storage |

### 3.3 New Table: `service_evaluators`

Links evaluator users to services (many-to-many).

```sql
CREATE TABLE service_evaluators (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id   UUID NOT NULL REFERENCES service_definitions(id) ON DELETE CASCADE,
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    is_active    BOOLEAN DEFAULT true,
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE(service_id, user_id)
);
-- Indexes: service_id, user_id, institution_id
```

### 3.4 New Table: `evaluations`

Human-in-the-loop decisions (separate from medical QC reviews).

```sql
CREATE TABLE evaluations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    request_id          UUID NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    run_id              UUID REFERENCES runs(id) ON DELETE SET NULL,
    evaluator_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    decision            VARCHAR(30) NOT NULL,  -- APPROVE | REJECT | REVISION_NEEDED
    comments            TEXT,
    watermark_text      VARCHAR(500),
    output_storage_path VARCHAR(1000),
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);
-- Indexes: institution_id, request_id
```

### 3.5 New Table: `payments`

Toss Payments transaction records.

```sql
CREATE TABLE payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id  UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    request_id      UUID REFERENCES requests(id) ON DELETE SET NULL,
    order_id        VARCHAR(100) UNIQUE NOT NULL,
    payment_key     VARCHAR(200) UNIQUE,
    amount          NUMERIC(18,2) NOT NULL,
    currency        VARCHAR(10) DEFAULT 'KRW',
    status          VARCHAR(30) DEFAULT 'PENDING',  -- PENDING | CONFIRMED | FAILED | CANCELLED | REFUNDED
    method          VARCHAR(50),
    toss_response   JSONB,
    confirmed_at    TIMESTAMPTZ,
    failed_at       TIMESTAMPTZ,
    error_detail    TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
-- Indexes: institution_id, request_id, order_id
```

### 3.6 Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `apps/api/app/models/evaluation.py` | **NEW** | `ServiceEvaluator` + `Evaluation` SQLAlchemy models |
| `apps/api/app/models/payment.py` | **NEW** | `Payment` SQLAlchemy model |
| `apps/api/app/models/service.py` | **MODIFY** | Add 5 new `mapped_column` fields to `ServiceDefinition` |
| `apps/api/app/models/report.py` | **MODIFY** | Add `watermarked_storage_path` field |
| `apps/api/app/models/__init__.py` | **MODIFY** | Import new models |
| `apps/api/migrations/versions/0008_*.py` | **NEW** | Alembic migration with `upgrade()` and `downgrade()` |

### 3.7 Model Details

**ServiceEvaluator** (`apps/api/app/models/evaluation.py`):
```python
class ServiceEvaluator(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "service_evaluators"
    __table_args__ = (UniqueConstraint("service_id", "user_id", name="uq_service_evaluator"),)

    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_definitions.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

**Evaluation** (`apps/api/app/models/evaluation.py`):
```python
class Evaluation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "evaluations"

    institution_id: Mapped[uuid.UUID]  # FK → institutions
    request_id: Mapped[uuid.UUID]      # FK → requests (CASCADE)
    run_id: Mapped[uuid.UUID | None]   # FK → runs (SET NULL)
    evaluator_id: Mapped[uuid.UUID | None]  # FK → users (SET NULL)
    decision: Mapped[str]              # APPROVE | REJECT | REVISION_NEEDED
    comments: Mapped[str | None]
    watermark_text: Mapped[str | None]
    output_storage_path: Mapped[str | None]
```

**Payment** (`apps/api/app/models/payment.py`):
```python
class Payment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    institution_id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID | None]
    request_id: Mapped[uuid.UUID | None]
    order_id: Mapped[str]           # unique, format: "nh-{16hex}"
    payment_key: Mapped[str | None] # unique, from Toss
    amount: Mapped[float]           # Numeric(18,2)
    currency: Mapped[str]           # default "KRW"
    status: Mapped[str]             # PENDING → CONFIRMED / FAILED / REFUNDED
    method: Mapped[str | None]      # Card, Transfer, etc.
    toss_response: Mapped[dict | None]  # full Toss API response (JSONB)
    confirmed_at: Mapped[datetime | None]
    failed_at: Mapped[datetime | None]
    error_detail: Mapped[str | None]
```

---

## 4. Phase 2: Backend — Service Flexibility

### 4.1 Schema Updates

**File**: `apps/api/app/schemas/service.py`

**ServiceRead** — Extended with:
```python
service_type: str = "AUTOMATIC"
outputs_schema: dict | None = None
accepted_file_types: list[str] | None = None
unit_price_krw: float = 0
requires_evaluator: bool = False
```

**ServiceCreate** — Extended with:
```python
service_type: str = "AUTOMATIC"      # AUTOMATIC | HUMAN_IN_LOOP
inputs_schema: dict | None = None
outputs_schema: dict | None = None
options_schema: dict | None = None
accepted_file_types: list[str] | None = None
unit_price_krw: float = 0
requires_evaluator: bool = False
```

**ServiceUpdate** — All new fields optional for partial updates.

### 4.2 New Schemas

**File**: `apps/api/app/schemas/evaluation.py`

| Schema | Purpose | Key Fields |
|--------|---------|------------|
| `EvaluationCreate` | Decision submission | `decision`, `comments`, `watermark_text` |
| `EvaluationRead` | Single evaluation | All fields + `created_at` |
| `EvaluationQueueItem` | Queue list item | `request_id`, `service_name`, `case_count`, `priority` |
| `EvaluationQueueResponse` | Paginated queue | `items: list[EvaluationQueueItem]` |
| `EvaluationDetailResponse` | Full context | Cases, files, runs, previous evaluations |
| `ServiceEvaluatorCreate` | Assign evaluator | `user_id` |
| `ServiceEvaluatorRead` | Assignment detail | `id`, `service_id`, `user_id`, `is_active` |
| `ServiceEvaluatorListResponse` | Assignment list | `items: list[ServiceEvaluatorRead]` |

**File**: `apps/api/app/schemas/payment.py`

| Schema | Purpose | Key Fields |
|--------|---------|------------|
| `PaymentPrepare` | Initiate payment | `service_id`, `amount`, `request_id?` |
| `PaymentPrepareResponse` | SDK config | `payment_id`, `order_id`, `customer_key` |
| `PaymentConfirm` | Verify payment | `payment_key`, `order_id`, `amount` |
| `PaymentConfirmResponse` | Confirmation | `status`, `method`, `receipt_url` |
| `PaymentRead` | Payment record | All fields |
| `PaymentListResponse` | Payment history | `items: list[PaymentRead]` |
| `PaymentCancelRequest` | Refund request | `reason` |

### 4.3 Service API Enhancements

**File**: `apps/api/app/api/v1/services.py`

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/services` | POST | SYSTEM_ADMIN | Create service with all new fields |
| `/services/{id}` | PATCH | SYSTEM_ADMIN | Update service with new fields |
| `/services/{id}/evaluators` | GET | SYSTEM_ADMIN | List evaluators for a service |
| `/services/{id}/evaluators` | POST | SYSTEM_ADMIN | Assign evaluator (body: `{user_id}`) |
| `/services/{id}/evaluators/{user_id}` | DELETE | SYSTEM_ADMIN | Remove evaluator assignment |

**Implementation details**:
- `_service_to_read()` helper maps all new model fields to response schema
- Evaluator assignment enforces unique constraint (409 on duplicate)
- Evaluator list filters by `is_active=True`

---

## 5. Phase 3: Backend — Evaluations

**File**: `apps/api/app/api/v1/evaluations.py`

### 5.1 Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/evaluations/queue` | GET | Evaluator | List requests in QC status where current user is assigned evaluator |
| `/evaluations/{request_id}` | GET | Evaluator | Full evaluation context (cases, files, runs, previous evaluations) |
| `/evaluations/{request_id}/decide` | POST | Evaluator | Submit decision: APPROVE / REJECT / REVISION_NEEDED |

### 5.2 Queue Endpoint Logic

```python
# 1. Find services where current user is active evaluator
evaluator_services = SELECT service_id FROM service_evaluators
    WHERE user_id = current_user.id AND is_active = True

# 2. Find requests in QC status for those services
requests = SELECT * FROM requests
    WHERE service_id IN evaluator_services
    AND status = "QC"
    AND institution_id = current_user.institution_id
    ORDER BY created_at ASC
```

### 5.3 Decision Logic

```
POST /evaluations/{request_id}/decide
Body: { decision: "APPROVE" | "REJECT" | "REVISION_NEEDED", comments?, watermark_text? }

1. Validate request is in QC status
2. Verify current user is assigned evaluator for the service
3. SELECT ... FOR UPDATE on request (prevent concurrent modifications)
4. Create Evaluation record

APPROVE:
  → Emit WATERMARK_REQUESTED outbox event (payload: request_id, evaluation_id, watermark_text)
  → Transition request: QC → REPORTING
  → Create notification: "평가 완료 — 워터마크 처리 중" (Evaluation complete — processing watermark)

REJECT:
  → Transition request: QC → FAILED
  → Store cancel_reason on request
  → Create notification: "평가 결과: 반려됨" (Evaluation result: rejected)

REVISION_NEEDED:
  → Transition request: QC → COMPUTING (retry)
  → Create notification: "수정 요청이 접수되었습니다" (Revision request received)
```

### 5.4 State Machine Integration

HUMAN_IN_LOOP services reuse the existing QC step. No state machine changes are needed:

```
CREATED → RECEIVING → STAGING → READY_TO_COMPUTE → COMPUTING → QC → REPORTING → FINAL
                                                                 ↑        ↓
                                                                 └── (REVISION_NEEDED)

                                                         QC → FAILED (REJECT)
```

When a request reaches QC, evaluators see it in their queue (instead of generic reviewers). The evaluator acts as the QC reviewer for HUMAN_IN_LOOP services.

---

## 6. Phase 4: Backend — Watermark Task

### 6.1 Watermark Utility

**File**: `apps/api/app/worker/watermark.py`

```python
def apply_watermark(
    image_bytes: bytes,
    text: str,
    opacity: float = 0.3,
    font_size: int = 36,
) -> bytes:
```

**Algorithm**:
1. Open image (JPEG/PNG) and convert to RGBA
2. Create transparent overlay matching image dimensions
3. Load DejaVuSans TTF font (fallback to PIL default)
4. Calculate text dimensions for grid spacing
5. Draw watermark text in diagonal grid (spacing: `text_width+80` × `text_height+100`)
6. Rotate entire text layer **30 degrees** for diagonal effect
7. Crop rotated layer to original image bounds
8. Composite watermarked layer onto original
9. Convert to RGB and export as JPEG (quality=90)

**Watermark appearance**: Gray text `(128, 128, 128)` with configurable opacity, repeated diagonally across the full image.

### 6.2 Celery Task

**File**: `apps/api/app/worker/tasks.py` — `apply_watermark_task`

```python
@celery_app.task(
    name="neurohub.tasks.apply_watermark",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    queue="compute",
)
def apply_watermark_task(self, request_id: str, evaluation_id: str):
```

**Task flow**:
1. Load evaluation and request from DB
2. Find input files (first image file from case files)
3. Download image from `neurohub-inputs` bucket via Supabase Storage REST API
4. Apply watermark using `apply_watermark()` with evaluator's text
5. Upload watermarked file to `neurohub-outputs` bucket
6. Update `evaluation.output_storage_path` with storage path
7. Emit `REPORT_REQUESTED` outbox event → triggers PDF generation
8. Create notification for request owner

**Storage helpers** (new sync functions for Celery context):
- `_supabase_storage_headers()` — Returns auth headers for Supabase Storage API
- `_upload_to_storage(bucket, path, data, content_type)` — PUT to Supabase Storage
- `_download_from_storage(bucket, path)` — GET from Supabase Storage

### 6.3 Reconciler Integration

**File**: `apps/api/app/reconciler.py`

```python
def _dispatch_watermark_requested(event: OutboxEvent) -> None:
    celery_app.send_task(
        "neurohub.tasks.apply_watermark",
        args=[event.payload["request_id"], event.payload["evaluation_id"]],
        queue="compute",
    )

EVENT_HANDLERS = {
    "RUN_SUBMITTED": _dispatch_run_submitted,
    "REPORT_REQUESTED": _dispatch_report_requested,
    "WATERMARK_REQUESTED": _dispatch_watermark_requested,  # NEW
}
```

### 6.4 Celery Config

**File**: `apps/api/app/worker/celery_app.py`

```python
task_routes={
    "neurohub.tasks.execute_run": {"queue": "compute"},
    "neurohub.tasks.generate_report": {"queue": "reporting"},
    "neurohub.tasks.apply_watermark": {"queue": "compute"},  # NEW
},
```

---

## 7. Phase 5: Backend — PDF Report Generation

### 7.1 PDF Generation

**File**: `apps/api/app/worker/tasks.py` — Extended `generate_report` task

Uses `reportlab` to generate A4 PDF:

```python
def _generate_pdf_bytes(report_content: dict, service_name: str, request_id: str) -> bytes:
```

**PDF structure**:
1. **Header**: Title, service name, generation date
2. **Metadata table**: Request ID, status, case count
3. **Summary**: Stats and key findings
4. **Run details**: Individual run results
5. **Conclusions**: Final analysis text

### 7.2 Extended Report Task Flow

```
generate_report task:
  1. Build report content dict (existing logic)
  2. Generate PDF using _generate_pdf_bytes()
  3. Upload PDF to neurohub-reports bucket
  4. Set report.pdf_storage_path = uploaded path
  5. Check for watermarked file from evaluation
  6. If exists, set report.watermarked_storage_path
  7. Transition request: REPORTING → FINAL
```

### 7.3 Download Endpoints

**File**: `apps/api/app/api/v1/requests.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/requests/{request_id}/report/download` | GET | Presigned URL for PDF from `neurohub-reports` bucket |
| `/requests/{request_id}/watermarked/download` | GET | Presigned URL for watermarked file from `neurohub-outputs` bucket |

Both use `storage.create_presigned_download()` (existing helper, 15-minute expiry).

---

## 8. Phase 6: Backend — Toss Payments

### 8.1 Toss API Client

**File**: `apps/api/app/services/toss_payments.py`

```python
class TossPaymentsClient:
    BASE_URL = "https://api.tosspayments.com/v1"

    async def confirm_payment(payment_key, order_id, amount) -> dict
    async def cancel_payment(payment_key, reason) -> dict
    async def get_payment(payment_key) -> dict
```

**Authentication**: `Basic base64(secret_key + ":")`

**HTTP client**: `httpx.AsyncClient` with 15-second timeout.

### 8.2 Payment Endpoints

**File**: `apps/api/app/api/v1/payments.py`

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/payments/prepare` | POST | User | Create Payment (PENDING), return Toss SDK params |
| `/payments/confirm` | POST | User | Verify amount, call Toss API, update to CONFIRMED |
| `/payments/history` | GET | User | List user's payments (offset/limit, max 100) |
| `/payments/{payment_id}` | GET | User | Single payment detail |
| `/payments/{payment_id}/cancel` | POST | User | Cancel/refund via Toss API |

### 8.3 Prepare Endpoint Details

```python
POST /payments/prepare
Body: { service_id, amount, request_id? }

Response: {
    payment_id: "uuid",
    order_id: "nh-{16hex}",          # generated server-side
    amount: 1000,
    currency: "KRW",
    customer_key: "nh-user-{12chars}" # first 12 chars of user UUID
}
```

### 8.4 Confirm Endpoint Details

```python
POST /payments/confirm
Body: { payment_key, order_id, amount }

1. Load payment by order_id + institution_id
2. VERIFY amount matches DB record (prevent tampering)
3. Call Toss API: POST /v1/payments/confirm { paymentKey, orderId, amount }
4. On success:
   - Update payment: status=CONFIRMED, payment_key, method, toss_response
   - Set confirmed_at timestamp
   - Extract receipt_url from Toss response
5. On failure:
   - Update payment: status=FAILED, error_detail
   - Set failed_at timestamp
   - Re-raise error

Response: { payment_id, status, method?, receipt_url? }
```

### 8.5 Config

**File**: `apps/api/app/config.py`

```python
# Toss Payments
toss_secret_key: str = ""   # Backend API auth
toss_client_key: str = ""   # Frontend SDK init
```

**Environment variables**:
- `TOSS_SECRET_KEY` — Fly.io secret
- `TOSS_CLIENT_KEY` — Fly.io secret + `NEXT_PUBLIC_TOSS_CLIENT_KEY` on Vercel

---

## 9. Phase 7: Frontend — API Client & Types

**File**: `apps/web/lib/api.ts`

### 9.1 New TypeScript Interfaces

```typescript
interface EvaluationQueueItem {
    request_id: string;
    request_status: string;
    service_name: string;
    service_display_name: string;
    case_count: number;
    created_at: string;
    priority: string;
}

interface EvaluationRead {
    id: string;
    institution_id: string;
    request_id: string;
    evaluator_id: string;
    decision: string;
    comments: string | null;
    watermark_text: string | null;
    output_storage_path: string | null;
    created_at: string;
}

interface EvaluationDetailResponse {
    request_id: string;
    request_status: string;
    service_name: string;
    service_display_name: string;
    cases: CaseRead[];
    files: CaseFileRead[];
    runs: any[];
    evaluations: EvaluationRead[];
}

interface ServiceEvaluatorRead {
    id: string;
    service_id: string;
    user_id: string;
    institution_id: string;
    is_active: boolean;
    created_at: string;
}

interface PaymentPrepareResponse {
    payment_id: string;
    order_id: string;
    amount: number;
    currency: string;
    customer_key: string;
}

interface PaymentRead {
    id: string;
    order_id: string;
    payment_key: string | null;
    amount: number;
    currency: string;
    status: string;
    method: string | null;
    request_id: string | null;
    confirmed_at: string | null;
    created_at: string;
}
```

### 9.2 New API Functions

```typescript
// Evaluations
listEvaluationQueue(): Promise<{ items: EvaluationQueueItem[] }>
getEvaluationDetail(requestId: string): Promise<EvaluationDetailResponse>
submitEvaluation(requestId: string, payload: {
    decision: string;
    comments?: string;
    watermark_text?: string;
}): Promise<EvaluationRead>

// Evaluator management
listServiceEvaluators(serviceId: string): Promise<{ items: ServiceEvaluatorRead[] }>
assignEvaluator(serviceId: string, userId: string): Promise<ServiceEvaluatorRead>
removeEvaluator(serviceId: string, userId: string): Promise<void>

// Downloads
getReportDownloadUrl(requestId: string): Promise<{ download_url: string; filename: string }>
getWatermarkedDownloadUrl(requestId: string): Promise<{ download_url: string; filename: string }>

// Payments
preparePayment(payload: { service_id: string; amount: number; request_id?: string }): Promise<PaymentPrepareResponse>
confirmPayment(payload: { payment_key: string; order_id: string; amount: number }): Promise<{
    payment_id: string;
    status: string;
    method?: string;
    receipt_url?: string;
}>
getPaymentHistory(): Promise<{ items: PaymentRead[] }>
```

### 9.3 Extended ServiceRead

```typescript
interface ServiceRead {
    // existing fields...
    service_type: string;           // "AUTOMATIC" | "HUMAN_IN_LOOP"
    outputs_schema: object | null;
    accepted_file_types: string[] | null;
    unit_price_krw: number;
    requires_evaluator: boolean;
    description: string | null;
}
```

### 9.4 Schema Extension

**File**: `apps/web/lib/schemas.ts`

```typescript
export const serviceCreateSchema = z.object({
    name: z.string().min(1),
    display_name: z.string().min(1),
    version: z.string().default("1.0"),
    department: z.string().optional(),
    description: z.string().optional(),
    service_type: z.enum(["AUTOMATIC", "HUMAN_IN_LOOP"]).default("AUTOMATIC"),
    accepted_file_types: z.array(z.string()).optional(),
    unit_price_krw: z.number().min(0).default(0),
    requires_evaluator: z.boolean().default(false),
});
```

---

## 10. Phase 8: Frontend — Admin Service Creation

**File**: `apps/web/app/(authenticated)/admin/services/page.tsx`

### 10.1 Extended Create Dialog

New form fields added between description textarea and submit buttons:

| Field | Type | Description |
|-------|------|-------------|
| **Service Type** | Button group | `AUTOMATIC` / `HUMAN_IN_LOOP` toggle |
| **Accepted File Types** | Multi-select chips | JPEG, PNG, PDF, DICOM, CSV, JSON |
| **Price (KRW)** | Number input | Unit price with min=0 |
| **Requires Evaluator** | Checkbox | Whether evaluator must review |

**File type options**:
```typescript
const FILE_TYPE_OPTIONS = [
    { label: "JPEG", value: "image/jpeg" },
    { label: "PNG", value: "image/png" },
    { label: "PDF", value: "application/pdf" },
    { label: "DICOM", value: "application/dicom" },
    { label: "CSV", value: "text/csv" },
    { label: "JSON", value: "application/json" },
];
```

### 10.2 Extended Table

New columns added to the services table:

| Column | Content |
|--------|---------|
| Type | Status chip: "자동 처리" (green) or "전문가 검토" (blue) |
| Price | `₩{formatted_number}` or `"-"` if zero |

Table now has 9 columns (was 7).

### 10.3 Create Mutation

```typescript
const createMut = useMutation({
    mutationFn: () => {
        const data = createForm.validate();
        return createService({
            name: data.name,
            display_name: data.display_name,
            version: data.version,
            department: data.department || undefined,
            description: data.description || undefined,
            service_type: data.service_type,
            accepted_file_types: data.accepted_file_types?.length ? data.accepted_file_types : undefined,
            unit_price_krw: data.unit_price_krw,
            requires_evaluator: data.requires_evaluator,
        });
    },
    onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["services"] });
        setShowCreate(false);
        createForm.reset();
    },
});
```

---

## 11. Phase 9: Frontend — Evaluator Pages

### 11.1 Evaluation Queue

**File**: `apps/web/app/(authenticated)/expert/evaluations/page.tsx`

- Lists pending evaluation requests for the current user
- Auto-refreshes every 15 seconds via `refetchInterval`
- Card-based layout with service name, request ID (8 chars), case count, status chip, date
- Clicking a card navigates to `/expert/evaluations/{request_id}`

**Query key**: `["evaluation-queue"]`

### 11.2 Evaluation Detail

**File**: `apps/web/app/(authenticated)/expert/evaluations/[id]/page.tsx`

**Layout**: Two-column grid

**Left column**:
- List of uploaded files (filename, slot, size, status)
- Previous evaluation history (decision + comments in cards)

**Right column** (Decision Form):
- Comments textarea
- Watermark text input (auto-populated: `{ServiceName} - {LocalDate}`)
- Three action buttons:
  - **APPROVE** (CheckCircle icon) — Triggers watermark pipeline
  - **REVISION_NEEDED** (ArrowCounterClockwise icon) — Sends back for rerun
  - **REJECT** (XCircle icon) — Marks request as failed

**Mutation**:
```typescript
const decideMut = useMutation({
    mutationFn: (decision: string) => submitEvaluation(id, {
        decision,
        comments: comments || undefined,
        watermark_text: watermarkText || undefined,
    }),
    onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["evaluation-queue"] });
        queryClient.invalidateQueries({ queryKey: ["evaluation-detail", id] });
        addToast("success", t("toast.transitionSuccess"));
        router.push("/expert/evaluations");
    },
});
```

**Query keys**: `["evaluation-queue"]`, `["evaluation-detail", id]`

### 11.3 Navigation

**Modified files**:
- `apps/web/app/(authenticated)/expert/layout.tsx` — Added Stamp icon + "Evaluations" nav link
- Sidebar shows "평가" (Evaluations) under Expert section

---

## 12. Phase 10: Frontend — Download Buttons

**File**: `apps/web/app/(authenticated)/user/requests/[id]/page.tsx`

When request status is `FINAL`, the success panel now shows **three download buttons**:

| Button | Style | Action |
|--------|-------|--------|
| **보고서 (PDF)** / Report (PDF) | Primary, small | `getReportDownloadUrl(id)` → `window.open(url)` |
| **워터마크 파일** / Watermarked File | Secondary, small | `getWatermarkedDownloadUrl(id)` → `window.open(url)` |
| **JSON 다운로드** / JSON Download | Secondary, small | Client-side blob download of report JSON |

**Download handlers**:
```typescript
const handleDownloadPdf = async () => {
    try {
        const { download_url } = await getReportDownloadUrl(id);
        window.open(download_url, "_blank");
    } catch {
        addToast("error", t("download.pdfNotAvailable"));
    }
};

const handleDownloadWatermarked = async () => {
    try {
        const { download_url } = await getWatermarkedDownloadUrl(id);
        window.open(download_url, "_blank");
    } catch {
        addToast("error", t("download.watermarkedNotAvailable"));
    }
};
```

---

## 13. Phase 11: Frontend — Payment Pages

### 13.1 Payment Page

**File**: `apps/web/app/(authenticated)/user/payment/page.tsx`

**Layout**: Two-column grid (services + payment widget | payment history)

**Left column — Service Selection**:
- List of ACTIVE services where `unit_price_krw > 0`
- Each card shows: display name, service type label, description, price (₩ formatted, large bold)
- Click to select, highlighted border on selection

**Left column — Payment Flow**:
1. Select service → "Pay Now" button appears with price summary
2. Click "Pay Now" → `prepareMut` calls `POST /payments/prepare`
3. Backend returns `order_id`, `customer_key`
4. Load Toss SDK dynamically, initialize payment widgets
5. Render payment methods in `#payment-widget` div
6. "Confirm Payment" button calls `widgets.requestPayment()`
7. Toss redirects to success/fail URL

**Toss SDK Integration**:
```typescript
// Dynamic SDK loading
const script = document.createElement("script");
script.src = "https://js.tosspayments.com/v2/standard";

// Widget initialization
const tossPayments = TossPayments(clientKey);
const widgets = tossPayments.widgets({ customerKey });
await widgets.setAmount({ currency: "KRW", value: amount });
await widgets.renderPaymentMethods({ selector: "#payment-widget", variantKey: "DEFAULT" });

// Payment request
await widgets.requestPayment({
    orderId,
    orderName: serviceName,
    successUrl: `${origin}/user/payment/success`,
    failUrl: `${origin}/user/payment/fail`,
});
```

**Right column — Payment History**:
- List of past payments with order_id, method, date, amount, status badge
- Status colors: CONFIRMED=green, FAILED=red, PENDING=gray

### 13.2 Payment Success

**File**: `apps/web/app/(authenticated)/user/payment/success/page.tsx`

**Flow**:
1. Extract URL params: `paymentKey`, `orderId`, `amount`
2. Call `confirmPayment({ payment_key, order_id, amount })`
3. Backend verifies, confirms with Toss, updates record

**UI states**:
- **Loading**: Spinner while confirming
- **Success**: CheckCircle icon, "결제 완료" / "Payment Successful", optional receipt link
  - Buttons: "요청 생성" → `/user/new-request`, "결제 내역" → `/user/payment`
- **Error**: XCircle icon, error message, "다시 시도" retry button

### 13.3 Payment Failure

**File**: `apps/web/app/(authenticated)/user/payment/fail/page.tsx`

**Flow**:
1. Extract URL params: `code`, `message` (from Toss redirect)
2. Display error with code and message

**UI**:
- XCircle icon (danger color)
- "결제 실패" / "Payment Failed" title
- Error message from Toss
- Error code (small text, if provided)
- Buttons: "다시 시도" → `/user/payment`, "대시보드" → `/user/dashboard`

### 13.4 Navigation

**Modified**: `apps/web/app/(authenticated)/user/layout.tsx`
- Added CreditCard icon import
- Added "결제" (Payments) nav link to user sidebar

---

## 14. Phase 12: i18n

**Files**: `apps/web/lib/i18n/ko.ts`, `apps/web/lib/i18n/en.ts`

~60 new translation keys added across 4 namespaces:

### 14.1 `evaluation.*` Keys

| Key | Korean | English |
|-----|--------|---------|
| `evaluation.queueTitle` | 평가 대기열 | Evaluation Queue |
| `evaluation.queueSubtitle` | 검토가 필요한 요청 목록 | Requests awaiting your review |
| `evaluation.noItems` | 대기 중인 평가가 없습니다 | No pending evaluations |
| `evaluation.detailTitle` | 평가 상세 | Evaluation Detail |
| `evaluation.filesAndData` | 제출 파일 및 데이터 | Submitted Files & Data |
| `evaluation.previousEvaluations` | 이전 평가 이력 | Previous Evaluations |
| `evaluation.noPrevious` | 이전 평가 이력이 없습니다 | No previous evaluations |
| `evaluation.decisionForm` | 평가 결정 | Your Decision |
| `evaluation.comments` | 코멘트 (선택) | Comments (optional) |
| `evaluation.commentsPlaceholder` | 평가 의견을 입력하세요... | Enter your evaluation comments... |
| `evaluation.watermarkText` | 워터마크 텍스트 | Watermark Text |
| `evaluation.watermarkHint` | 승인 시 이미지에 삽입될 텍스트 | Text to embed in the image on approval |
| `evaluation.approve` | 승인 | Approve |
| `evaluation.reject` | 반려 | Reject |
| `evaluation.revisionNeeded` | 수정 요청 | Revision Needed |
| `evaluation.caseCount` | 케이스 | cases |
| `evaluation.notQcStatus` | QC 상태가 아닌 요청입니다 | Request is not in QC status |
| `evaluation.requestId` | 요청 번호 | Request # |
| `evaluation.priority` | 우선순위 | Priority |
| `evaluation.evaluator` | 평가자 | Evaluator |
| `evaluation.decision` | 결정 | Decision |

### 14.2 `payment.*` Keys

| Key | Korean | English |
|-----|--------|---------|
| `payment.title` | 결제 | Payments |
| `payment.subtitle` | 서비스 이용을 위한 결제 | Pay for service usage |
| `payment.selectService` | 서비스 선택 | Select a Service |
| `payment.payNow` | 결제하기 | Pay Now |
| `payment.preparing` | 결제 준비 중... | Preparing payment... |
| `payment.confirmPayment` | 결제 확인 | Confirm Payment |
| `payment.processing` | 처리 중... | Processing... |
| `payment.successTitle` | 결제 완료 | Payment Successful |
| `payment.successMessage` | 결제가 성공적으로 완료되었습니다 | Your payment has been completed successfully |
| `payment.failTitle` | 결제 실패 | Payment Failed |
| `payment.genericFail` | 결제 처리 중 오류가 발생했습니다 | An error occurred during payment processing |
| `payment.retry` | 다시 시도 | Retry |
| `payment.viewReceipt` | 영수증 보기 | View Receipt |
| `payment.createRequest` | 요청 생성하기 | Create Request |
| `payment.history` | 결제 내역 | Payment History |
| `payment.noHistory` | 결제 내역이 없습니다 | No payment history |
| `payment.amount` | 금액 | Amount |
| `payment.method` | 결제 수단 | Method |
| `payment.orderId` | 주문 번호 | Order ID |
| `payment.confirming` | 결제 확인 중... | Confirming payment... |
| `payment.humanInLoop` | 전문가 검토 | Expert Review |
| `payment.automatic` | 자동 처리 | Automatic |

### 14.3 `download.*` Keys

| Key | Korean | English |
|-----|--------|---------|
| `download.reportPdf` | 보고서 (PDF) | Report (PDF) |
| `download.watermarkedFile` | 워터마크 파일 | Watermarked File |
| `download.pdfNotAvailable` | PDF 보고서가 아직 준비되지 않았습니다 | PDF report is not ready yet |
| `download.watermarkedNotAvailable` | 워터마크 파일이 없습니다 | Watermarked file not available |

### 14.4 `adminServices.*` Additions

| Key | Korean | English |
|-----|--------|---------|
| `adminServices.serviceType` | 서비스 유형 | Service Type |
| `adminServices.automatic` | 자동 처리 | Automatic |
| `adminServices.humanInLoop` | 전문가 검토 (Human-in-the-Loop) | Expert Review (Human-in-the-Loop) |
| `adminServices.fileTypes` | 허용 파일 유형 | Accepted File Types |
| `adminServices.price` | 이용 가격 (KRW) | Price (KRW) |
| `adminServices.evaluators` | 평가자 | Evaluators |
| `adminServices.assignEvaluator` | 평가자 배정 | Assign Evaluator |
| `adminServices.requiresEvaluator` | 평가자 필요 | Requires Evaluator |
| `adminServices.tableType` | 유형 | Type |
| `adminServices.tablePrice` | 가격 | Price |

---

## 15. Phase 13: Demo Seed Data

**File**: `apps/api/scripts/seed_dev.py`

Add a demo watermark service for testing the complete evaluation workflow:

```python
WATERMARK_SERVICE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
WATERMARK_PIPELINE_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")

# ServiceDefinition
ServiceDefinition(
    id=WATERMARK_SERVICE_ID,
    institution_id=institution_id,
    name="image-watermark-demo",
    display_name="이미지 워터마크 데모",
    description="전문가가 이미지를 검토하고 워터마크를 추가하는 데모 서비스",
    version="1.0.0",
    status="ACTIVE",
    department="연구",
    service_type="HUMAN_IN_LOOP",
    accepted_file_types=["image/jpeg", "image/png"],
    unit_price_krw=1000,
    requires_evaluator=True,
    inputs_schema={
        "required": ["image"],
        "properties": {
            "image": {"type": "file", "label": "이미지 파일"},
        },
    },
    created_by=DEFAULT_USER_ID,
)

# PipelineDefinition
PipelineDefinition(
    id=WATERMARK_PIPELINE_ID,
    service_id=WATERMARK_SERVICE_ID,
    name="watermark-demo-default",
    version="1.0.0",
    is_default=True,
    steps=[{"name": "watermark", "type": "human_review"}],
    qc_rules={},
    resource_requirements={"gpu": False, "memory_gb": 2},
)
```

---

## 16. Phase 14: Dependencies & Config

### 16.1 Backend Dependencies

**File**: `apps/api/pyproject.toml`

```toml
dependencies = [
    # ... existing ...
    "Pillow>=10.0.0",      # Image watermark processing
    "reportlab>=4.0.0",    # PDF generation
]
```

Note: `httpx>=0.28.0` already exists (used for Toss API calls).

### 16.2 Frontend Dependencies

**File**: `apps/web/package.json`

```json
"dependencies": {
    // ... existing ...
    "@tosspayments/tosspayments-sdk": "^2.3.0"
}
```

### 16.3 Environment Variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `TOSS_SECRET_KEY` | Fly.io secret | Backend Toss API auth |
| `TOSS_CLIENT_KEY` | Fly.io secret | Backend config |
| `NEXT_PUBLIC_TOSS_CLIENT_KEY` | Vercel env | Frontend Toss SDK init |

---

## 17. Data Flow Diagrams

### 17.1 Complete Evaluation Workflow

```
User uploads JPEG file → Request created (CREATED)
                              ↓
                     Request transitions through:
                     RECEIVING → STAGING → READY_TO_COMPUTE → COMPUTING → QC
                              ↓
Evaluator views queue:  GET /evaluations/queue
                        (filters: user is active evaluator, request in QC status)
                              ↓
Evaluator reviews:      GET /evaluations/{request_id}
                        (loads files, runs, previous evaluations)
                              ↓
Evaluator decides:      POST /evaluations/{request_id}/decide
                              ↓
                     ┌────────┼────────┐
                     │        │        │
                  APPROVE  REJECT  REVISION
                     │        │        │
                     │     FAILED   COMPUTING
                     │     (notify)  (rerun)
                     ↓
            WATERMARK_REQUESTED outbox event
                     ↓
            Reconciler → Celery compute queue
                     ↓
            apply_watermark_task:
            1. Download image from neurohub-inputs
            2. Apply watermark (Pillow)
            3. Upload to neurohub-outputs
            4. Update evaluation.output_storage_path
            5. Emit REPORT_REQUESTED
            6. Notify user
                     ↓
            generate_report task:
            1. Build report content
            2. Generate PDF (reportlab)
            3. Upload PDF to neurohub-reports
            4. Set pdf_storage_path
            5. Copy watermarked_storage_path
            6. Transition: REPORTING → FINAL
                     ↓
            User receives notification
            User downloads PDF + watermarked file
```

### 17.2 Complete Payment Workflow

```
User visits /user/payment
                     ↓
          GET /services (filtered: ACTIVE, price > 0)
          GET /payments/history
                     ↓
User selects service + clicks "Pay Now"
                     ↓
          POST /payments/prepare
          → Creates Payment (PENDING)
          → Returns: { order_id, customer_key, amount }
                     ↓
Frontend loads Toss SDK:
          TossPayments(clientKey)
          widgets = tossPayments.widgets({ customerKey })
          widgets.setAmount({ currency: "KRW", value: amount })
          widgets.renderPaymentMethods({ selector: "#payment-widget" })
                     ↓
User fills payment form → clicks "Confirm Payment"
                     ↓
          widgets.requestPayment({
              orderId, orderName,
              successUrl: "/user/payment/success",
              failUrl: "/user/payment/fail"
          })
                     ↓
               Toss processes payment
                     ↓
          ┌──────────┴──────────┐
        SUCCESS               FAILURE
          ↓                     ↓
Redirect to:              Redirect to:
/payment/success          /payment/fail
?paymentKey=xxx           ?code=xxx
&orderId=xxx              &message=xxx
&amount=xxx
          ↓                     ↓
POST /payments/confirm    Show error + retry
→ Verify amount match
→ Call Toss API confirm
→ Update CONFIRMED
→ Return receipt_url
          ↓
Show success + receipt
CTA: Create request
```

### 17.3 TanStack Query Keys

| Query Key | Endpoint | Refetch |
|-----------|----------|---------|
| `["evaluation-queue"]` | `GET /evaluations/queue` | Every 15s |
| `["evaluation-detail", id]` | `GET /evaluations/{id}` | On demand |
| `["services"]` | `GET /services` | On demand (invalidated on create/update) |
| `["payment-history"]` | `GET /payments/history` | On demand |

---

## 18. File Summary

### 18.1 New Files (14)

| File | Purpose |
|------|---------|
| `apps/api/app/models/evaluation.py` | ServiceEvaluator + Evaluation SQLAlchemy models |
| `apps/api/app/models/payment.py` | Payment SQLAlchemy model |
| `apps/api/app/schemas/evaluation.py` | 8 Pydantic schemas for evaluation API |
| `apps/api/app/schemas/payment.py` | 6 Pydantic schemas for payment API |
| `apps/api/app/api/v1/evaluations.py` | 3 evaluation endpoints (queue, detail, decide) |
| `apps/api/app/api/v1/payments.py` | 5 payment endpoints (prepare, confirm, history, detail, cancel) |
| `apps/api/app/services/toss_payments.py` | Toss Payments V2 async HTTP client |
| `apps/api/app/worker/watermark.py` | Pillow-based image watermark utility |
| `apps/api/migrations/versions/0008_*.py` | Alembic migration (3 new tables, 6 new columns) |
| `apps/web/app/(authenticated)/expert/evaluations/page.tsx` | Evaluation queue UI |
| `apps/web/app/(authenticated)/expert/evaluations/[id]/page.tsx` | Evaluation detail + decision form UI |
| `apps/web/app/(authenticated)/user/payment/page.tsx` | Payment initiation + Toss widget UI |
| `apps/web/app/(authenticated)/user/payment/success/page.tsx` | Payment success handler UI |
| `apps/web/app/(authenticated)/user/payment/fail/page.tsx` | Payment failure handler UI |

### 18.2 Modified Files (20)

| File | Change |
|------|--------|
| `apps/api/app/models/service.py` | Add 5 columns (service_type, outputs_schema, etc.) |
| `apps/api/app/models/report.py` | Add `watermarked_storage_path` |
| `apps/api/app/models/__init__.py` | Import new models |
| `apps/api/app/schemas/service.py` | Extend ServiceCreate/Read/Update with new fields |
| `apps/api/app/api/v1/services.py` | New fields in CRUD + evaluator management endpoints |
| `apps/api/app/api/v1/requests.py` | Add report/watermarked download endpoints |
| `apps/api/app/api/v1/router.py` | Include evaluations + payments routers |
| `apps/api/app/worker/tasks.py` | Add watermark task + PDF generation + storage helpers |
| `apps/api/app/worker/celery_app.py` | Add watermark task route to compute queue |
| `apps/api/app/reconciler.py` | Add WATERMARK_REQUESTED event handler |
| `apps/api/app/config.py` | Add `toss_secret_key`, `toss_client_key` |
| `apps/api/pyproject.toml` | Add Pillow, reportlab dependencies |
| `apps/api/scripts/seed_dev.py` | Add demo watermark service seed |
| `apps/web/lib/api.ts` | Add ~20 new API functions + types |
| `apps/web/lib/schemas.ts` | Extend serviceCreateSchema with 4 new fields |
| `apps/web/lib/i18n/ko.ts` | Add ~60 Korean translation keys |
| `apps/web/lib/i18n/en.ts` | Add ~60 English translation keys |
| `apps/web/app/(authenticated)/expert/layout.tsx` | Add evaluations nav link |
| `apps/web/app/(authenticated)/user/layout.tsx` | Add payments nav link |
| `apps/web/app/(authenticated)/admin/services/page.tsx` | Extended create dialog + table columns |
| `apps/web/app/(authenticated)/user/requests/[id]/page.tsx` | Add PDF + watermarked download buttons |
| `apps/web/package.json` | Add @tosspayments/tosspayments-sdk |

---

## 19. Verification Plan

| # | Test | Expected Result |
|---|------|-----------------|
| 1 | Run `alembic upgrade head` | New tables + columns created without errors |
| 2 | Run `python scripts/seed_dev.py` | Demo watermark service exists with correct config |
| 3 | Admin creates service via UI | HUMAN_IN_LOOP service with file types + price saved |
| 4 | Admin assigns evaluator | ServiceEvaluator record created |
| 5 | User selects service → pays via Toss | Payment widget renders, payment confirmed |
| 6 | User creates request → uploads JPEG | Request transitions through pipeline to QC |
| 7 | Evaluator sees request in queue | Queue shows pending evaluation |
| 8 | Evaluator approves with watermark text | Evaluation created, WATERMARK_REQUESTED emitted |
| 9 | Celery processes watermark | Watermarked image uploaded to neurohub-outputs |
| 10 | Report generated as PDF | PDF uploaded to neurohub-reports bucket |
| 11 | User sees FINAL status | Download buttons for PDF + watermarked file work |
| 12 | User receives notification | Toast/notification at each state transition |
| 13 | Evaluator rejects request | Request transitions to FAILED, user notified |
| 14 | Evaluator requests revision | Request returns to COMPUTING for rerun |
| 15 | Payment cancellation | Toss API called, payment status → REFUNDED |

---

## 20. Key Patterns & Decisions

| # | Pattern | Description |
|---|---------|-------------|
| 1 | **Transactional Outbox** | All state changes emit outbox events in the same DB transaction for async processing |
| 2 | **Multi-tenancy** | All new tables include `institution_id` with RESTRICT FK to prevent cross-tenant access |
| 3 | **State Machine Reuse** | HUMAN_IN_LOOP services reuse existing QC step — no state machine changes needed |
| 4 | **Amount Verification** | Payment `confirm` endpoint re-verifies amount against DB to prevent client-side tampering |
| 5 | **Idempotency** | Payment `order_id` unique, service evaluator assignments unique-constrained |
| 6 | **Queue Routing** | Watermark + execute_run on `compute` queue; generate_report on `reporting` queue |
| 7 | **Korean-first i18n** | All UI text uses i18n system, default Korean with English support |
| 8 | **Pure Python Processing** | Pillow + reportlab chosen over system-dep alternatives (ImageMagick, WeasyPrint) |
| 9 | **Sync Storage Helpers** | Celery tasks use sync `httpx` (not async) for Supabase Storage API calls |
| 10 | **Presigned URLs** | All file downloads use 15-minute presigned URLs — never expose raw storage paths |

---

## 21. UX Evaluation by Role

A thorough UX audit was conducted after Phases 1–12 were implemented. This section documents the findings for each of the three user roles and identifies gaps in the current implementation.

### 21.1 서비스 사용자 (Service User)

**Persona**: Submits medical data, views AI analysis results and reports.

**Navigation** (`/user/layout.tsx`):
- Dashboard → Service Catalog → My Requests → New Request → Payment → Settings

#### Current User Journey

```
Dashboard → Service Catalog → New Request (4-step wizard) → My Requests → Request Detail (download)
                                                                              ↕
                                                              Payment → Success → New Request
```

#### Strengths
- Draft auto-save in localStorage for the new request wizard (dropout recovery)
- Clear 4-step wizard: Service → Cases → Upload → Review & Submit
- Timeline component provides visual progress tracking
- Download section with PDF, watermarked file, and JSON options
- Toast notifications for state transitions
- Idempotency key pattern prevents duplicate submissions

#### Critical Issues Found

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 1 | **Payment not linked to request** | CRITICAL | User pays on `/user/payment`, but Payment record has optional `request_id`. After payment success, CTA says "Create Request" but doesn't pass `payment_id` or `service_id` to the new request wizard. User must manually re-select the same service. No verification that user has paid before submitting a request. |
| 2 | **Expert feedback invisible** | HIGH | When an evaluator rejects a request or requests revision, the user sees status=FAILED or COMPUTING but cannot see the evaluator's comments or decision reason. The request detail page only shows `cancel_reason` (set on user-initiated cancels), not evaluation comments. |
| 3 | **Service catalog missing pricing** | HIGH | `/user/services` shows service cards but doesn't display `unit_price_krw`, `service_type`, `description`, or `accepted_file_types`. User must go to a separate Payment page to see prices. The "Request Analysis" button navigates to `/user/new-request` but doesn't pre-select the service. |
| 4 | **No client-side file type validation** | MEDIUM | When uploading files in Step 3 of the wizard, `accepted_file_types` from the service definition is not checked. User can upload a PDF to a JPEG-only service and only gets rejected server-side. |
| 5 | **No upload progress indicator** | MEDIUM | File uploads to Supabase Storage show no progress bar or percentage. For large DICOM files this creates uncertainty. |
| 6 | **No notification center** | MEDIUM | Sidebar has no notifications page. State transition notifications (toast) are ephemeral and lost on page reload. |

#### Recommended Fixes (Phase 15)

1. **Service Catalog Enhancement**: Add `unit_price_krw`, `service_type` badge, `description`, and `accepted_file_types` to service cards. "Request Analysis" button should navigate to `/user/new-request?service_id={id}` with pre-selection.

2. **Request Detail — Show Evaluation Feedback**: When request has associated evaluations (from `GET /evaluations/{request_id}` or embed in request response), display evaluator's decision, comments, and timestamp in a "Review Feedback" panel on the request detail page.

3. **Payment → Request Flow**: After payment success, navigate to `/user/new-request?service_id={id}&payment_id={id}` to pre-select service and link payment. Alternatively, show confirmed payments on the new request page as available credits.

---

### 21.2 전문가 리뷰어 (Expert Reviewer)

**Persona**: Reviews AI analysis results, provides QC and expert opinions.

**Navigation** (`/expert/layout.tsx`):
- Dashboard → Review Queue → Evaluations → Settings

#### Current User Journey

```
Dashboard → Review Queue (/expert/reviews) → Review Detail (/expert/reviews/[id])
         → Evaluations  (/expert/evaluations) → Evaluation Detail (/expert/evaluations/[id])
```

#### Critical Issues Found

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 1 | **Two separate, confusing queues** | CRITICAL | Experts have TWO queue pages: `/expert/reviews` (existing QC/EXPERT_REVIEW queue using `listReviewQueue`) and `/expert/evaluations` (new evaluation queue using `listEvaluationQueue`). Both show items in QC status. The distinction is: Reviews = generic QC for all services; Evaluations = service-specific evaluator assignments. But this is **not explained anywhere** in the UI. An expert assigned as evaluator to a HUMAN_IN_LOOP service will see the same request appear in **both** queues. |
| 2 | **No analysis result visualization** | HIGH | Neither the review detail nor evaluation detail pages show the actual AI analysis output (predictions, confidence scores, segmentation overlays). Experts see only raw files and run status chips. They're being asked to approve results they can't inspect. |
| 3 | **Decision meanings unclear** | HIGH | Buttons say "Approve", "Reject", "Rerun"/"Revision Needed" but don't explain the downstream consequences (e.g., Approve = watermark + report generation; Reject = request FAILED permanently; Revision = re-compute, adds to queue again). |
| 4 | **QC Score undefined** | MEDIUM | The review detail shows a "QC Score (0-100)" input with no explanation of the scale, no rubric, and no indication of whether a minimum score is required. |
| 5 | **No report preview** | MEDIUM | In the EXPERT_REVIEW flow (report review), the expert is asked to approve/reject a report but **cannot see the report content**. The reports panel only shows report type and status, not the actual content or PDF. |

#### Recommended Fixes (Phase 16)

1. **Merge Queues**: Either (a) remove `/expert/evaluations` and route all evaluation items through the existing `/expert/reviews` queue with an "Evaluation" tab, or (b) clearly differentiate the two with explanatory text: "Review Queue = medical QC for all services" vs "Evaluations = assigned evaluator tasks for specific services".

2. **Add Decision Descriptions**: Below each decision button, add a brief description:
   - Approve: "워터마크를 적용하고 보고서를 생성합니다" / "Applies watermark and generates report"
   - Reject: "요청이 실패 처리됩니다" / "Request will be marked as failed"
   - Revision: "재분석을 위해 되돌립니다" / "Returns for re-analysis"

3. **Report Preview**: In EXPERT_REVIEW mode, fetch and display report content (summary, conclusions) inline before asking for approval.

---

### 21.3 관리자 (Admin)

**Persona**: System operation, user management, service configuration.

**Navigation** (`/admin/layout.tsx`):
- Dashboard → Requests → Users → Organizations → Services → API Keys → Audit Logs → Settings

#### Current User Journey

```
Dashboard → Services (create/edit/toggle) → Assign evaluators (API only, no UI)
         → Users (approve experts) → Requests (manual state transitions)
```

#### Critical Issues Found

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 1 | **No evaluator assignment UI** | HIGH | Backend has `POST/GET/DELETE /services/{id}/evaluators` endpoints, and API client has `assignEvaluator()`, `removeEvaluator()`, `listServiceEvaluators()` functions. But the admin services page has **no UI** for managing evaluators. Admin must use API directly or cURL. This is a critical gap for the HUMAN_IN_LOOP workflow — without assigned evaluators, no one can review requests. |
| 2 | **Service edit doesn't allow updating new fields** | HIGH | The edit dialog only allows changing `display_name`, `version`, `department`. Cannot edit `service_type`, `unit_price_krw`, `accepted_file_types`, or `requires_evaluator` after creation. If admin sets wrong price, must deactivate and recreate. |
| 3 | **Manual request state transitions** | MEDIUM | Admin requests page shows transition buttons (e.g., "Start Receiving", "Staging Complete") but only for the first 2 transitions. COMPUTING→QC and later transitions are not exposed. For AUTOMATIC services, admins can't manually advance stuck requests. |
| 4 | **No revenue/billing dashboard** | MEDIUM | Payments exist but admin has no visibility into payment totals, revenue by service, or failed payment rates. No reconciliation between payments and requests. |
| 5 | **No search across entities** | MEDIUM | Can't search requests by ID, users by email, or services by name from the admin dashboard. Must navigate to each section and scroll. |

#### Recommended Fixes (Phase 17)

1. **Evaluator Management Section**: Add an expandable section or sub-dialog in the admin services page. When viewing a HUMAN_IN_LOOP service, show "Evaluators" panel with:
   - List of assigned evaluators (name, email, status)
   - "Add Evaluator" button → user search/select → `assignEvaluator()`
   - "Remove" button per evaluator → `removeEvaluator()`

2. **Extended Edit Dialog**: Add service_type, unit_price_krw, accepted_file_types, and requires_evaluator to the edit dialog (using the same UI components as the create dialog).

---

### 21.4 Cross-Role Integration Issues

| Connection | Issue | Impact |
|------------|-------|--------|
| **User → Expert** | Users cannot see evaluation comments/decisions on their request detail page | Users don't know why their request was rejected or sent for revision |
| **User → Payment** | Payment success page CTA doesn't pass service context to new request creation | Users must re-select service, breaking the flow |
| **Expert → Expert** | Two separate queues (reviews + evaluations) show overlapping items | Experts confused about which queue to use, may process same request twice |
| **Admin → Expert** | No UI to assign evaluators to services | HUMAN_IN_LOOP workflow is broken until admin uses API directly |
| **Admin → Service** | Can't edit pricing or service type after creation | Must deactivate + recreate to fix mistakes |

---

## 22. Corrective Phases (Phase 15–17)

Based on the UX evaluation, three corrective phases are needed before the implementation is complete.

### Phase 15: Service User UX Fixes

**Priority**: CRITICAL — Fixes the broken payment→request flow and missing feedback

| # | Change | File(s) | Description |
|---|--------|---------|-------------|
| 1 | **Service Catalog Enhancement** | `user/services/page.tsx` | Add `unit_price_krw` (₩ formatted), `service_type` badge, `description` text, `accepted_file_types` chips to each service card. "Request Analysis" button passes `?service_id={id}` in URL. |
| 2 | **Request Detail — Evaluation Feedback** | `user/requests/[id]/page.tsx` | When request has evaluations, show a "Review Feedback" panel with evaluator's decision, comments, and timestamp. Fetch via existing `getEvaluationDetail()` or embed in request response. |
| 3 | **Payment Success → Pre-select Service** | `user/payment/success/page.tsx` | "Create Request" button navigates to `/user/new-request?service_id={service_id}` using the `service_id` from the payment record. |
| 4 | **New Request — Pre-select from URL** | `user/new-request/page.tsx` | Read `service_id` from URL search params and auto-select the service in Step 1 of the wizard. |
| 5 | **Client-side File Type Validation** | `user/new-request/page.tsx` | In Step 3 (upload), check file MIME type against `accepted_file_types` from the selected service. Show inline error for unsupported files. |

**i18n keys needed** (~10):
- `serviceCatalog.price`, `serviceCatalog.serviceType`, `serviceCatalog.fileTypes`
- `requestDetail.evaluationFeedback`, `requestDetail.evaluatorDecision`, `requestDetail.evaluatorComments`
- `newRequest.unsupportedFileType`

### Phase 16: Expert Reviewer UX Fixes

**Priority**: HIGH — Resolves confusing dual-queue and missing context

| # | Change | File(s) | Description |
|---|--------|---------|-------------|
| 1 | **Merge Evaluation Queue into Review Queue** | `expert/reviews/page.tsx`, `expert/evaluations/page.tsx` | Add "Evaluation" tab to the existing reviews page filter (QC / EXPERT_REVIEW / Evaluation / Completed). Remove separate evaluations nav link. Evaluation items use the same card UI but route to `/expert/evaluations/[id]` for the evaluation-specific decision form. |
| 2 | **Decision Descriptions** | `expert/evaluations/[id]/page.tsx`, `expert/reviews/[id]/page.tsx` | Add descriptive text below each decision button explaining the consequence. |
| 3 | **Report Content Preview** | `expert/reviews/[id]/page.tsx` | When in EXPERT_REVIEW mode, display report summary, conclusions, and generated_at inline. Add "View Full PDF" link if pdf_storage_path exists. |
| 4 | **QC Score Guidance** | `expert/reviews/[id]/page.tsx` | Add helper text below QC Score input: "0 = 완전 부적합, 100 = 완벽 (최소 기준: 서비스별 상이)" / "0 = completely inadequate, 100 = perfect (minimum varies by service)" |

**i18n keys needed** (~8):
- `evaluation.approveDescription`, `evaluation.rejectDescription`, `evaluation.revisionDescription`
- `expertReviewDetail.reportPreview`, `expertReviewDetail.viewFullPdf`
- `qcScore.helpText`

### Phase 17: Admin UX Fixes

**Priority**: HIGH — Evaluator assignment is required for HUMAN_IN_LOOP to work

| # | Change | File(s) | Description |
|---|--------|---------|-------------|
| 1 | **Evaluator Management UI** | `admin/services/page.tsx` | Add expandable "Evaluators" section per service (or a sub-dialog). Shows assigned evaluators with name/email. "Add Evaluator" opens a user search input → calls `assignEvaluator()`. "Remove" button per row → calls `removeEvaluator()`. Only shown for services where `requires_evaluator === true`. |
| 2 | **Extended Edit Dialog** | `admin/services/page.tsx` | Add `service_type`, `unit_price_krw`, `accepted_file_types`, and `requires_evaluator` fields to the edit dialog (same UI as create). Update `openEdit()` to populate these from the service, and update `updateMut` to send them. |
| 3 | **Admin User Search** | `admin/services/page.tsx` (evaluator assignment) | Simple text search on users endpoint to find evaluators by name/email for assignment. Uses existing `listUsers` API with a search filter. |

**i18n keys needed** (~6):
- `adminServices.manageEvaluators`, `adminServices.addEvaluator`, `adminServices.removeEvaluator`
- `adminServices.searchUser`, `adminServices.noEvaluatorsAssigned`, `adminServices.evaluatorAdded`

---

## 23. Updated File Summary (Including Corrective Phases)

### New Files Added in Corrective Phases: 0

All fixes modify existing files — no new pages or components needed.

### Additional Modified Files (Phase 15–17)

| File | Phase | Change |
|------|-------|--------|
| `apps/web/app/(authenticated)/user/services/page.tsx` | 15 | Add price, service_type, description, file types to cards |
| `apps/web/app/(authenticated)/user/requests/[id]/page.tsx` | 15 | Add evaluation feedback panel |
| `apps/web/app/(authenticated)/user/payment/success/page.tsx` | 15 | Pass service_id to new request CTA |
| `apps/web/app/(authenticated)/user/new-request/page.tsx` | 15 | Pre-select service from URL param; file type validation |
| `apps/web/app/(authenticated)/expert/reviews/page.tsx` | 16 | Add "Evaluation" filter tab |
| `apps/web/app/(authenticated)/expert/evaluations/[id]/page.tsx` | 16 | Add decision descriptions |
| `apps/web/app/(authenticated)/expert/reviews/[id]/page.tsx` | 16 | Add decision descriptions, report preview, QC score help |
| `apps/web/app/(authenticated)/expert/layout.tsx` | 16 | Remove separate evaluations nav (merged into reviews) |
| `apps/web/app/(authenticated)/admin/services/page.tsx` | 17 | Evaluator management UI; extended edit dialog |
| `apps/web/lib/i18n/ko.ts` | 15-17 | ~24 new keys |
| `apps/web/lib/i18n/en.ts` | 15-17 | ~24 new keys |

---

## 24. Updated Verification Plan

| # | Test | Phase | Expected Result |
|---|------|-------|-----------------|
| 1 | Run `alembic upgrade head` | 1 | New tables + columns created |
| 2 | Run `python scripts/seed_dev.py` | 13 | Demo watermark service seeded |
| 3 | Admin creates HUMAN_IN_LOOP service via UI | 8 | Service with price, file types, evaluator requirement saved |
| 4 | **Admin assigns evaluator to service via UI** | **17** | ServiceEvaluator record created, shown in service detail |
| 5 | **Admin edits service price/type after creation** | **17** | Service updated without recreating |
| 6 | **User browses service catalog with prices** | **15** | Cards show ₩ price, type badge, file types |
| 7 | User pays via Toss widget | 11 | Payment confirmed, success page shown with receipt |
| 8 | **Payment success → pre-selects service in new request** | **15** | Wizard Step 1 auto-selects paid service |
| 9 | User creates request → uploads JPEG | existing | Pipeline reaches QC status |
| 10 | **User tries uploading PDF to JPEG-only service** | **15** | Client-side error shown before upload |
| 11 | **Evaluator sees request in unified Review Queue** | **16** | Single queue with QC + Evaluation tabs |
| 12 | Evaluator approves with watermark text | 9 | WATERMARK_REQUESTED emitted, watermark processed |
| 13 | **User sees evaluator's comments on request detail** | **15** | Feedback panel shows decision + comments |
| 14 | Report generated as PDF | 5 | PDF uploaded, download works |
| 15 | User downloads PDF + watermarked file | 10 | Both presigned URLs return files |
| 16 | Evaluator rejects request | 9 | FAILED status, user sees rejection reason |
| 17 | **Expert sees decision descriptions** | **16** | Approve/Reject/Revision consequences explained |
| 18 | Payment cancellation | 6 | Toss API called, REFUNDED status |

**Bold** = new/updated tests from corrective phases

---

## 25. Implementation Priority Order

```
COMPLETED:
  Phase 1:  Database schema + migration           ✅
  Phase 2:  Backend service flexibility            ✅
  Phase 3:  Backend evaluations                    ✅
  Phase 4:  Backend watermark task                 ✅
  Phase 5:  Backend PDF report generation          ✅
  Phase 6:  Backend Toss Payments                  ✅
  Phase 7:  Frontend API client + types            ✅
  Phase 8:  Frontend admin service creation        ✅
  Phase 9:  Frontend evaluator pages               ✅
  Phase 10: Frontend download buttons              ✅
  Phase 11: Frontend payment pages                 ✅
  Phase 12: i18n                                   ✅

IN PROGRESS:
  Phase 13: Demo seed data                         🔄
  Phase 14: Dependencies + config                  🔄

PLANNED (Corrective — from UX evaluation):
  Phase 15: Service user UX fixes                  ⬜ (CRITICAL)
  Phase 16: Expert reviewer UX fixes               ⬜ (HIGH)
  Phase 17: Admin UX fixes                         ⬜ (HIGH)
```

Recommended order for corrective phases:
1. **Phase 17 first** — Admin evaluator assignment UI (blocks HUMAN_IN_LOOP workflow entirely)
2. **Phase 15 second** — Service user fixes (payment→request linkage, evaluation feedback)
3. **Phase 16 third** — Expert queue consolidation (polish, not blocking)
