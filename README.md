# NeuroHub

뇌전증(Epilepsy) 환자의 뇌영상 데이터를 서버에서 자동 분석하여, 상대적으로 뇌 활성이 저하된 영역을 탐지하고 임상 보고서를 생성하는 의료 AI 워크플로우 플랫폼.

PET, MRI, DTI, fMRI 등 다중 모달리티 데이터에 대해 DICOM 수신 → BIDS 변환 → 품질검증(Pre-QC) → 기법별 컨테이너 분석 → 다중기법 융합 점수화 → 전문가 검토 → PDF 보고서 생성까지 엔드투엔드 파이프라인을 지원합니다.

## 역할 및 담당

| 역할 | 담당자 |
|------|--------|
| 서버 접근 및 프로세싱 코드 | 어진석 박사 |
| 데이터 관리 | 이준호 연구원 |

## 서버 접속 정보

### 내부 접속

| 항목 | 값 |
|------|-----|
| IP | `10.0.0.142` |
| 계정 (sudo 권한) | `yookj` |
| 비밀번호 | `monet1234` |

### 외부 접속

| 항목 | 값 |
|------|-----|
| IP | `103.22.220.93` |
| SSH 포트 | `3093` |
| 접속 명령 | `ssh -p 3093 yookj@103.22.220.93` |
| VNC | SSH 터널링을 통해 접속 필요 |

### 웹 접속

| 서비스 | URL |
|--------|-----|
| NeuroHub 웹 UI | `http://103.22.220.93:3093` (외부) / `http://10.0.0.142:3000` (내부) |
| FastAPI 백엔드 | `http://localhost:8080` (서버 내부) |

### 테스트 계정

| 역할 | 이메일 | 비밀번호 |
|------|--------|----------|
| 관리자 | `admin@neurohub.com` | `asdfasdf` |
| 사용자 | `user@neurohub.com` | `asdfasdf` |
| 전문가 | `expert@neurohub.com` | `asdfasdf` |

## 데이터 경로

### 원본 데이터

| 데이터 | 경로 |
|--------|------|
| 초기 PET 데이터 (원본) | `/remotenas2/YUHS/KYJ_Surgery/7463838/PET-CT` |
| 테스트 데이터 (PET + 부속) | `/projects4/NEUROHUB/TEST/INPUT/TEST_MoNET` |

### 테스트 대상 데이터

| 데이터 | 경로 | 설명 |
|--------|------|------|
| sub-001 | `/projects4/NEUROHUB/TEST/INPUT/sub-001_raw_BIDS/` | T1 + DTI (`.tck` 파일 생성 시 분석 완료) |
| sub-002 | `/projects4/NEUROHUB/TEST/INPUT/sub-002_raw/` | T1 + PET |
| sub-003 | `/projects4/NEUROHUB/TEST/INPUT/sub-003_raw/` | T1 + fMRI |
| 분석 결과 샘플 | `/projects1/pi/jhlee/01_neurohub/sample/sub-001_BIDS.zip` | sub-001 코드 완료 후 결과물 |
| FreeSurfer 사전 계산 결과 | `/projects4/NEUROHUB/TEST/INPUT/freesurfer/` | sub-001 FreeSurfer recon-all 결과 |

### 분석 코드 경로

| 코드 | 경로 |
|------|------|
| 분석 코드 전체 | `/projects4/environment/codes/` |
| neuroan_pet (FDG-PET 분석) | `/projects4/environment/codes/neuroan_pet/` |
| SPM25 | `/projects4/environment/codes/spm25/` |
| 정상 대조군 DB (FDG-NC) | `/projects4/NEUROHUB/TEST/DB/FDG-NC/` |

### 호스트 도구 경로

| 도구 | 경로 |
|------|------|
| FreeSurfer 8.0 | `/usr/local/freesurfer/8.0.0` |
| FSL | `/usr/local/fsl` |
| MRtrix3 | `/usr/local/mrtrix3` |
| MATLAB R2025b | `/usr/local/MATLAB/R2025b` |

> **참고**: sub-001은 batch03에서 `.tck` 추출로 분석 완료. batch03 실행 시 CLI 설정은 `--10k`를 권장 (간단 확인용).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router), React 19, TypeScript 5.7, Tailwind CSS 4, Radix UI, TanStack Query v5 |
| Backend | FastAPI, Python 3.11+, SQLAlchemy 2 (async), Pydantic v2, Alembic |
| Async | Celery + Redis, Transactional Outbox + Reconciler |
| Auth/DB/Storage | PostgreSQL 17.9, MinIO (S3 호환), Local JWT (HS256) |
| Containers | Docker (ubuntu:22.04), 호스트 마운트 방식 신경영상 도구 (FreeSurfer, FSL, MRtrix3, MATLAB/SPM25) |
| AI | Google Gemini 2.0 Flash (임상 AI 에이전트) |
| Package Manager | Bun 1.2 (monorepo workspaces) |

## Project Structure

```
NeuroHub/
├── apps/
│   ├── web/                       # Next.js 프론트엔드
│   │   ├── app/
│   │   │   ├── (public)/          # 랜딩, 로그인, 회원가입, 온보딩
│   │   │   └── (authenticated)/
│   │   │       ├── user/          # 대시보드, 요청 목록, 분석 요청 마법사, 서비스 카탈로그,
│   │   │       │                  # DICOM 워크리스트, 그룹 스터디, 마켓플레이스, 결제, 리포트, 뷰어
│   │   │       ├── expert/        # 대시보드, 리뷰 큐, 모델 관리, 피드백, 성능 지표
│   │   │       └── admin/         # 대시보드, 요청 관리, 사용자, 기관, 서비스, API 키,
│   │   │                          # 감사 로그, 모델 아티팩트, 분석 기법, DICOM 게이트웨이
│   │   ├── components/            # 사이드바, 마법사, 알림, 타임라인, NIfTI 뷰어,
│   │   │                          # Pre-QC 뷰어, 기법 결과, 융합 결과, 브레드크럼
│   │   ├── lib/                   # API 클라이언트, i18n (600+ 키), 훅, Zod 스키마
│   │   └── e2e/                   # Playwright E2E 테스트
│   └── api/                       # FastAPI 백엔드
│       ├── app/
│       │   ├── api/v1/            # 25개 라우트 모듈 (60+ 엔드포인트)
│       │   ├── models/            # 22개 SQLAlchemy 모델
│       │   ├── schemas/           # Pydantic 요청/응답 스키마
│       │   ├── services/          # 29개 서비스 모듈
│       │   ├── middleware/        # 속도 제한, 구조화 로깅, 타임아웃
│       │   ├── worker/            # Celery 작업 (compute, reporting, technique 실행)
│       │   └── security/          # Local JWT (HS256) 인증
│       ├── migrations/            # Alembic 마이그레이션
│       ├── scripts/               # 시드 스크립트 (서비스, 기법, DICOM 스터디)
│       └── tests/                 # 36개 pytest 테스트 파일
├── containers/                    # 신경영상 분석용 Docker 컨테이너
│   ├── cortical-thickness/        # FreeSurfer 기반 피질두께 분석
│   ├── diffusion-properties/      # FSL/MRtrix3 확산텐서 분석
│   ├── tractography/              # MRtrix3 섬유경로 추적
│   └── fdg-pet/                   # MATLAB/SPM25 FDG-PET 분석 (neuroan_pet)
└── docs/                          # 기술 PRD, 배포 가이드, 감사 보고서
```

## 서버 서비스 구성

모든 서비스가 단일 서버에서 로컬로 실행됩니다.

| 서비스 | 포트 | 설명 |
|--------|------|------|
| PostgreSQL 17.9 | `5433` | 메인 데이터베이스 |
| Redis 7.4.2 | `6380` | Celery 작업 큐 + 캐시 |
| MinIO | `9000` | S3 호환 오브젝트 스토리지 (DICOM, 결과, 리포트) |
| FastAPI | `8080` | 백엔드 API |
| Next.js | `3000` | 프론트엔드 웹 UI |
| Celery Worker | — | 비동기 분석 작업 실행 |
| Reconciler | — | Outbox → Redis 이벤트 디스패처 |

### 서버 시작

```bash
# 전체 서비스 시작
bash ~/neurohub-platform/scripts/start-all.sh

# 개별 시작
# PostgreSQL, Redis, MinIO는 systemd로 관리
sudo systemctl start postgresql redis minio

# FastAPI
cd ~/neurohub-platform/neurohub-repo/apps/api
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Next.js
cd ~/neurohub-platform/neurohub-repo/apps/web
PORT=3000 HOSTNAME=0.0.0.0 node .next/standalone/server.js

# Celery Worker
celery -A app.worker.celery_app:celery_app worker -Q compute,reporting -l info
```

### 환경 변수

Backend (`apps/api/.env`):
```
DATABASE_URL=postgresql+asyncpg://neurohub@localhost:5433/neurohub
REDIS_URL=redis://localhost:6380/0
USE_LOCAL_AUTH=true
LOCAL_JWT_SECRET=<secret>
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=<key>
MINIO_SECRET_KEY=<secret>
CONTAINER_EXECUTION_ENABLED=true
GEMINI_API_KEY=<key>
```

Frontend (`apps/web/.env.local`):
```
NEXT_PUBLIC_API_URL=/api/v1
API_ORIGIN=http://localhost:8080
```

## 임상 분석 파이프라인

```
DICOM 수신 → BIDS 변환 → Pre-QC 검증 → 기법별 컨테이너 실행 → 융합 점수화 → 전문가 검토 → PDF 보고서
```

1. **DICOM Gateway** — PACS에서 STOW-RS로 수신, 로컬 디렉토리 스캔, 요청에 연결
2. **BIDS Conversion** — dcm2niix를 이용한 DICOM→BIDS 자동 변환
3. **Pre-QC Validation** — 모달리티별 자동 품질검증 (MRI 해상도, fMRI 볼륨 수, DTI 그래디언트, PET SUV 범위)
4. **Technique Execution** — Docker 컨테이너로 팬아웃, 기법별 신경영상 분석 실행
5. **Fusion Engine** — 임상 서비스별 기법 가중 합산 (예: 뇌전증 = FDG-PET 0.15 + 피질두께 0.20 + ...)
6. **Expert Review** — 구조화된 리뷰 큐에서 승인/반려/수정 결정
7. **PDF Reports** — WeasyPrint 기반 임상 보고서 (뇌 렌더링 포함)

### 분석 기법 모듈 (21개 등록)

| 모달리티 | 기법 |
|----------|------|
| MRI | 피질두께, 체적 분석, 백질 병변, 해마 하위영역, 피질 이랑화 |
| PET | FDG-PET, 아밀로이드 PET, 타우 PET |
| fMRI | 휴지기 fMRI, 기억 인코딩 fMRI |
| DTI | 확산 특성, 섬유경로 추적 |
| EEG | 스펙트럼 분석, 소스 국소화, 기억 인코딩 EEG |
| MEG | 소스 국소화, 동적 인과 모델링 |
| SPECT | 관류 SPECT |
| PSG | 수면 구조 |

### Docker 컨테이너 (4개 구축)

| 컨테이너 | 기반 | 호스트 마운트 도구 | 출력 |
|-----------|------|-------------------|------|
| `cortical-thickness` | ubuntu:22.04 | FreeSurfer 8.0 | 181개 영역별 피질두께 |
| `diffusion-properties` | ubuntu:22.04 | FSL, MRtrix3 | FA, MD, RD, AD 맵 |
| `tractography` | ubuntu:22.04 | MRtrix3, FreeSurfer | 5000 스트림라인 + 연결성 |
| `fdg-pet` | ubuntu:22.04 | MATLAB R2025b, SPM25, neuroan_pet | Z-score 맵, 영역별 통계 |

### 임상 서비스 (7개 구성)

각 서비스는 기법 모듈의 가중 조합으로 구성:

- **뇌전증 종합** — MRI + EEG + PET + fMRI (6개 기법)
- **치매 종합** — MRI + PET + DTI (6개 기법)
- **파킨슨병** — MRI + PET + DTI (5개 기법)
- **뇌종양** — MRI + DTI (4개 기법)
- **수면장애** — EEG + PSG + MRI (4개 기법)
- **뇌졸중 평가** — MRI + SPECT + DTI (4개 기법)
- **기억장애** — MRI + fMRI + EEG (5개 기법)

## 사용자 역할

- **의사 / 기사** — 6단계 마법사를 통한 분석 요청, 상태 추적, 결과 조회, DICOM 워크리스트
- **전문가 리뷰어** — QC 리뷰 큐, 구조화된 피드백 및 어노테이션, 모델 성능 추적
- **시스템 관리자** — 플랫폼 관리, 사용자/기관 관리, 서비스 설정, 기법 관리, DICOM 게이트웨이, 감사 로그, API 키

## 요청 생명주기 (상태 머신)

```
CREATED → RECEIVING → STAGING → READY_TO_COMPUTE → COMPUTING → QC → REPORTING → [EXPERT_REVIEW →] FINAL
종료 상태: FINAL, FAILED, CANCELLED
```

각 전환은 역할 기반으로 제어. 백엔드에서 `SELECT ... FOR UPDATE`로 상태 머신 강제.

## 아키텍처

### 데이터 흐름

```
Frontend (Next.js :3000)
  → FastAPI (/api/v1 :8080)
  → PostgreSQL (:5433, SQLAlchemy async)
  → Outbox 이벤트 (동일 트랜잭션)
  → Reconciler → Redis (:6380) → Celery Worker
  → Docker 컨테이너 (신경영상 분석)
  → 출력 파싱 → 융합 점수화 → 보고서
```

### 인증

- **Local JWT (HS256)**: `app/security/local_jwt.py` — 서버 자체 JWT 발급 및 검증
- **개발 모드**: 헤더 기반 폴백 (`X-User-Id`, `X-Username`, `X-Institution-Id`, `X-Roles`)
- **B2B**: API 키 인증 (`hmac.compare_digest`)

### 컨테이너 실행

`LocalContainerRunner`가 서버의 Docker 컨테이너를 오케스트레이션:
- 신경영상 도구를 읽기 전용 볼륨으로 호스트 마운트 (FreeSurfer, FSL, MRtrix3, MATLAB/SPM25)
- 입력 데이터 (BIDS 형식) 및 출력 디렉토리 마운트
- 컨테이너 stdout에서 `NEUROHUB_OUTPUT: {json}` 파싱
- GPU 할당, 메모리 제한, 타임아웃 처리

### 파이프라인 오케스트레이터

엔드투엔드 케이스 처리:
1. 스마트 zip 추출 (DICOM 자동 감지)
2. BIDS 변환 (dcm2niix)
3. 모달리티별 Pre-QC 검증
4. 기법별 팬아웃 실행 (병렬 Docker 컨테이너)
5. 팬인 융합 점수화 (가중 합산)
6. 보고서 생성

## 테스트

- **백엔드**: 36개 테스트 파일 — 상태 머신, 요청, 업로드, 컨테이너, 기법, 융합 엔진, 파이프라인 오케스트레이터, zip 프로세서, Pre-QC, AI 에이전트, 속도 제한, 리콘실러, 웹훅 등
- **프론트엔드**: Playwright E2E 테스트 — 관리자 요청, 파일 검증, 대시보드 플로우

```bash
# 백엔드
cd apps/api && pytest

# 프론트엔드 E2E
cd apps/web && bunx playwright test
```

## 문서

- [기술 PRD (한국어)](docs/TECHNICAL_PRD_KR.md)
- [플랫폼 감사 및 로드맵](docs/AUDIT_AND_ROADMAP.md)
- [UX/UI 성능 감사](docs/AUDIT_UIUX_PERFORMANCE.md)

## License

Private. All rights reserved.
