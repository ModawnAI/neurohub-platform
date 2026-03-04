# NeuroHub

의료 AI 뇌영상 분석 워크플로우 플랫폼.

PET, MRI, DTI, fMRI 등 다중 모달리티 뇌영상 데이터에 대해 **DICOM 수신 → BIDS 변환 → 품질검증(Pre-QC) → 기법별 컨테이너 분석 → 다중기법 융합 점수화 → 전문가 검토 → PDF 보고서 생성**까지 엔드투엔드 파이프라인을 제공합니다.

---

## 목차

1. [팀 역할](#1-팀-역할)
2. [서버 접속 정보](#2-서버-접속-정보)
3. [기술 스택](#3-기술-스택)
4. [프로젝트 구조](#4-프로젝트-구조)
5. [아키텍처](#5-아키텍처)
6. [서버 구성 및 실행](#6-서버-구성-및-실행)
7. [신경영상 분석 파이프라인](#7-신경영상-분석-파이프라인)
8. [Docker 컨테이너 상세](#8-docker-컨테이너-상세)
9. [테스트 데이터 및 실행 스크립트](#9-테스트-데이터-및-실행-스크립트)
10. [테스트 결과 요약](#10-테스트-결과-요약)
11. [백엔드 테스트](#11-백엔드-테스트)
12. [배포](#12-배포)
13. [문서](#13-문서)

---

## 1. 팀 역할

| 역할 | 담당자 |
|------|--------|
| 서버 접근 및 프로세싱 코드 | 어진석 박사 |
| 데이터 관리 | 이준호 연구원 |

---

## 2. 서버 접속 정보

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
| SSH 포트 | `3093` (SSLH 멀티플렉싱 — SSH + HTTP 공유) |
| 접속 명령 | `ssh -p 3093 yookj@103.22.220.93` |

### 웹 접속

| 서비스 | URL |
|--------|-----|
| NeuroHub 웹 UI | `http://103.22.220.93:3093` (외부) / `http://10.0.0.142:3000` (내부) |
| FastAPI 백엔드 | `http://localhost:8080` (서버 내부 전용) |

### 테스트 계정

| 역할 | 이메일 | 비밀번호 |
|------|--------|----------|
| 관리자 | `admin@neurohub.com` | `asdfasdf` |
| 사용자 | `user@neurohub.com` | `asdfasdf` |
| 전문가 | `expert@neurohub.com` | `asdfasdf` |

---

## 3. 기술 스택

| 레이어 | 기술 |
|--------|------|
| 프론트엔드 | Next.js 16 (App Router), React 19, TypeScript 5.7, Tailwind CSS 4, Radix UI, TanStack Query v5 |
| 백엔드 | FastAPI, Python 3.11+, SQLAlchemy 2 (async), Pydantic v2, Alembic |
| 비동기 처리 | Celery + Redis, Transactional Outbox + Reconciler |
| 인증/DB/스토리지 | PostgreSQL 17.9, MinIO (S3 호환), Local JWT (HS256) |
| 컨테이너 | Docker (ubuntu:22.04), 호스트 마운트 방식 신경영상 도구 |
| AI 에이전트 | Google Gemini 2.0 Flash (임상 AI 보조) |
| 패키지 관리 | Bun 1.2 (monorepo workspaces) |

---

## 4. 프로젝트 구조

```
NeuroHub/
├── apps/
│   ├── web/                           # Next.js 프론트엔드
│   │   ├── app/
│   │   │   ├── (public)/              # 랜딩, 로그인, 회원가입, 온보딩
│   │   │   └── (authenticated)/
│   │   │       ├── user/              # 대시보드, 분석 요청, 서비스 카탈로그, DICOM 워크리스트,
│   │   │       │                      # 그룹 스터디, 마켓플레이스, 결제, 리포트, 뷰어
│   │   │       ├── expert/            # 리뷰 큐, 모델 관리, 피드백, 성능 지표
│   │   │       └── admin/             # 요청 관리, 사용자, 기관, 서비스, API 키,
│   │   │                              # 감사 로그, 분석 기법, DICOM 게이트웨이
│   │   ├── components/                # UI 컴포넌트 (사이드바, 마법사, NIfTI 뷰어, Pre-QC 뷰어 등)
│   │   ├── lib/                       # API 클라이언트, i18n (600+ 키), Zod 스키마
│   │   └── e2e/                       # Playwright E2E 테스트
│   │
│   └── api/                           # FastAPI 백엔드
│       ├── app/
│       │   ├── api/v1/                # 25개 라우트 모듈 (60+ 엔드포인트)
│       │   ├── models/                # 22개 SQLAlchemy 모델
│       │   ├── schemas/               # Pydantic 요청/응답 스키마
│       │   ├── services/              # 29개 서비스 모듈
│       │   │   ├── local_container_runner.py   # Docker 컨테이너 오케스트레이션
│       │   │   ├── pipeline_orchestrator.py    # E2E 파이프라인 코디네이터
│       │   │   ├── zip_processor.py            # 스마트 ZIP/DICOM 추출기
│       │   │   ├── fusion_engine.py            # 다중기법 융합 점수화
│       │   │   └── storage.py                  # MinIO 스토리지 서비스
│       │   ├── middleware/            # 속도 제한, 구조화 로깅, 타임아웃
│       │   ├── worker/                # Celery 작업 (compute, reporting, technique 실행)
│       │   └── security/              # Local JWT (HS256) 인증
│       ├── migrations/                # Alembic DB 마이그레이션
│       ├── scripts/                   # 시드 스크립트, E2E 테스트 스크립트
│       └── tests/                     # 38개 pytest 테스트 파일
│
├── containers/                        # 신경영상 분석용 Docker 컨테이너
│   ├── cortical-thickness/            # FreeSurfer 피질두께 분석
│   ├── diffusion-properties/          # FSL/MRtrix3 확산텐서 분석
│   ├── tractography/                  # MRtrix3 섬유경로 추적
│   └── fdg-pet/                       # MATLAB/SPM25 FDG-PET 분석
│
└── docs/                              # 기술 PRD, 배포 가이드, 감사 보고서
```

---

## 5. 아키텍처

### 5.1 데이터 흐름

```
Frontend (Next.js :3000)
  → FastAPI (/api/v1 :8080)
  → PostgreSQL (:5433, SQLAlchemy async)
  → Outbox 이벤트 (동일 트랜잭션)
  → Reconciler → Redis (:6380) → Celery Worker
  → Docker 컨테이너 (신경영상 분석)
  → NEUROHUB_OUTPUT 파싱 → 융합 점수화 → 보고서
```

### 5.2 요청 생명주기 (상태 머신)

```
CREATED → RECEIVING → STAGING → READY_TO_COMPUTE → COMPUTING → QC → REPORTING → [EXPERT_REVIEW →] FINAL
종료 상태: FINAL, FAILED, CANCELLED
```

각 전환은 역할 기반(PHYSICIAN, TECHNICIAN, REVIEWER, SYSTEM_ADMIN)으로 제어. `SELECT ... FOR UPDATE`로 동시성 보호.

### 5.3 인증

| 방식 | 설명 |
|------|------|
| Local JWT (HS256) | `app/security/local_jwt.py` — 서버 자체 JWT 발급/검증 |
| 개발 모드 폴백 | `X-User-Id`, `X-Username`, `X-Institution-Id`, `X-Roles` 헤더 |
| B2B API 키 | `hmac.compare_digest` 기반 API 키 인증 |

### 5.4 다중 테넌시

모든 리소스는 `institution_id`로 격리. JWT 클레임에서 `institution_id` 추출 후 모든 쿼리에 필터 적용.

### 5.5 멱등성 (Idempotency)

생성 엔드포인트는 `idempotency_key`를 수용. SHA-256 해시로 중복 방지. 동일 키 + 다른 페이로드 = 409 Conflict.

### 5.6 트랜잭셔널 아웃박스

도메인 쓰기 + `outbox_events` 삽입을 하나의 DB 트랜잭션에서 처리. Reconciler가 5초 간격으로 폴링하여 Redis로 디스패치.

---

## 6. 서버 구성 및 실행

### 6.1 서비스 포트

| 서비스 | 포트 | 비고 |
|--------|------|------|
| PostgreSQL 17.9 | `5433` | 기본 5432가 아님 |
| Redis 7.4.2 | `6380` | 기본 6379가 아님 |
| MinIO | `9000` | 콘솔 `9001` |
| FastAPI | `8080` | 개발 환경은 8000 |
| Next.js | `3000` | 외부 접속은 SSLH 3093 경유 |
| Celery Worker | — | compute, reporting 큐 |
| Reconciler | — | Outbox → Redis 디스패처 |

### 6.2 전체 서비스 시작

```bash
bash ~/neurohub-platform/scripts/start-all.sh
```

### 6.3 개별 서비스 시작

```bash
# PostgreSQL, Redis, MinIO (systemd)
sudo systemctl start postgresql redis minio

# FastAPI 백엔드
cd ~/neurohub-platform/neurohub-repo/apps/api
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 >> ~/neurohub-platform/logs/api.log 2>&1 &

# Next.js 프론트엔드
bash /tmp/restart-web.sh

# Celery Worker
cd ~/neurohub-platform/neurohub-repo/apps/api && source venv/bin/activate
nohup celery -A app.worker.celery_app:celery_app worker -Q compute,reporting -l info --concurrency=4 \
  > ~/neurohub-platform/logs/celery.log 2>&1 &
```

### 6.4 환경 변수

**Backend** (`apps/api/.env`):
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

**Frontend** (`apps/web/.env.local`):
```
NEXT_PUBLIC_API_URL=/api/v1
API_ORIGIN=http://localhost:8080
NEXT_PUBLIC_USE_LOCAL_AUTH=true
```

> **주의**: Next.js standalone 빌드는 `next.config.ts`의 rewrite 대상을 빌드 시점에 고정(bake)합니다. `.env.local`의 `API_ORIGIN`은 `next build` 중에 읽혀 `.next/standalone/` 내부 파일에 하드코딩됩니다. 빌드 후 변경해도 반영되지 않으므로, 반드시 **빌드 전에 올바른 값 확인** 필요.

---

## 7. 신경영상 분석 파이프라인

### 7.1 전체 흐름

```
ZIP 업로드 → 스마트 추출 → DICOM→NIfTI 변환 → 모달리티 분류 → BIDS 구성
  → Pre-QC 검증 → 기법별 Docker 컨테이너 팬아웃 → NEUROHUB_OUTPUT 파싱
  → 융합 점수화 (가중 합산) → 전문가 검토 → PDF 보고서
```

### 7.2 파이프라인 오케스트레이터 단계

| 단계 | 설명 | 도구 |
|------|------|------|
| **추출 + 스캔** | ZIP 다운로드, DICOM 매직바이트 감지, 시리즈별 그룹핑 | `zip_processor.py` |
| **DICOM → NIfTI** | 자동 포맷 변환 | `dcm2niix` |
| **모달리티 분류** | T1, DWI, PET 등 자동 식별 | 내장 분류기 |
| **BIDS 구성** | 표준 BIDS 디렉토리 생성 | 내장 |
| **Pre-QC** | 해상도, 방향, 볼륨 수, SUV 범위 검증 | `pre_qc.py` |
| **기법 실행** | Docker 컨테이너 병렬 실행 | `local_container_runner.py` |
| **융합 점수화** | 서비스별 기법 가중 합산 | `fusion_engine.py` |
| **보고서** | WeasyPrint 기반 PDF 생성 | `report_generation.py` |

### 7.3 등록된 분석 기법 (21개)

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

### 7.4 임상 서비스 (7개)

각 서비스는 기법 모듈의 가중 조합으로 구성됩니다:

| 서비스 | 기법 조합 |
|--------|-----------|
| 뇌전증 종합 | MRI + EEG + PET + fMRI (6개 기법) |
| 치매 종합 | MRI + PET + DTI (6개 기법) |
| 파킨슨병 | MRI + PET + DTI (5개 기법) |
| 뇌종양 | MRI + DTI (4개 기법) |
| 수면장애 | EEG + PSG + MRI (4개 기법) |
| 뇌졸중 평가 | MRI + SPECT + DTI (4개 기법) |
| 기억장애 | MRI + fMRI + EEG (5개 기법) |

### 7.5 NEUROHUB_OUTPUT 프로토콜

모든 기법 컨테이너는 stdout에 아래 JSON 스키마를 출력합니다:

```json
{
  "module": "기법_키",
  "module_version": "1.0.0",
  "qc_score": 85.0,
  "qc_flags": [],
  "features": {"특징_이름": 숫자값, ...},
  "maps": {"맵_이름": "/output/파일경로", ...},
  "confidence": 72.3
}
```

`LocalContainerRunner`가 컨테이너 stdout에서 `NEUROHUB_OUTPUT: {json}` 라인을 파싱하여 결과를 수집합니다.

---

## 8. Docker 컨테이너 상세

### 8.1 호스트 마운트 아키텍처

FreeSurfer(~15GB), FSL(~5GB), MRtrix3(~500MB), MATLAB(~20GB)은 컨테이너 내부에 포함하기에 너무 크므로, **호스트 도구를 읽기 전용으로 마운트**하는 방식을 채택합니다:

| 호스트 도구 | 호스트 경로 | 컨테이너 마운트 경로 |
|-------------|-----------|-------------------|
| FreeSurfer 8.0 | `/usr/local/freesurfer/8.0.0` | `/opt/freesurfer:ro` |
| FSL 6.x | `/usr/local/fsl` | `/opt/fsl:ro` |
| MRtrix3 3.x | `/usr/local/mrtrix3` | `/opt/mrtrix3:ro` |
| MATLAB R2025b | `/usr/local/MATLAB/R2025b` | `/opt/matlab:ro` |
| SPM25 | `/projects4/environment/codes/spm25` | `/opt/spm25:ro` |
| neuroan_pet | `/projects4/environment/codes/neuroan_pet` | `/opt/neuroan_pet:ro` |
| 정상 대조군 DB | `/projects4/NEUROHUB/TEST/DB` | `/opt/neuroan_db:ro` |

컨테이너 자체는 경량 베이스 이미지 (~100MB) + `nibabel` + `numpy`만 포함합니다.

### 8.2 컨테이너 요약

| 컨테이너 | 이미지 | 베이스 | 도구 | 소요 시간 |
|-----------|--------|--------|------|-----------|
| Cortical Thickness | `neurohub/cortical-thickness:1.0.0` | `python:3.12-slim` | FreeSurfer 8.0 | ~10초 (사전계산) / 6~12시간 (recon-all) |
| Diffusion Properties | `neurohub/diffusion-properties:1.0.0` | `ubuntu:22.04` | FSL + MRtrix3 | ~60초 |
| Tractography | `neurohub/tractography:1.0.0` | `ubuntu:22.04` | MRtrix3 + FreeSurfer | ~120초 (5K 스트림라인) |
| FDG-PET | `neurohub/fdg-pet:1.0.0` | `ubuntu:22.04` | MATLAB R2025b + SPM25 | ~5~10분 |

### 8.3 Cortical Thickness (피질 두께)

FreeSurfer `recon-all`을 실행하여 T1 MRI에서 피질 두께, 표면적, 피질하 볼륨을 추출합니다.

**파이프라인:**
```
T1 NIfTI → recon-all (또는 사전 계산 데이터 복사) → aparc.stats/aseg.stats 파싱
→ 181개 특징 추출 (DK Atlas 68 두께 + 68 면적 + 45 피질하 볼륨)
```

**주요 환경 변수:**
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `NEUROHUB_SKIP_RECON` | `0` | `1`로 설정 시 recon-all 건너뛰고 사전 계산 데이터 사용 |
| `NTHREADS` | `4` | recon-all 병렬 스레드 수 |

**출력 특징 (181개):**
- 영역별 피질 두께: 34 영역 × 2 반구 = 68개
- 영역별 표면적: 34 영역 × 2 반구 = 68개
- 피질하 구조물 볼륨: 45개 (해마, 편도체, 미상핵, 피각, 시상 등)

**출력 맵:**
| 파일 | 설명 |
|------|------|
| `aparc_aseg.nii.gz` | 피질 분할 영상 |
| `brain_mgz` | 두개골 제거 뇌 영상 |
| `lh.thickness` / `rh.thickness` | 좌/우반구 두께 표면 |
| `lh.curv` / `rh.curv` | 좌/우반구 곡률 |
| `lh.area` / `rh.area` | 좌/우반구 표면적 |

### 8.4 Diffusion Properties (확산 특성)

DTI 데이터에서 확산 텐서를 적합하고 FA/MD/AD/RD 스칼라 맵을 추출합니다.

**파이프라인:**
```
DWI NIfTI + bvec/bval
→ mrconvert (NIfTI→MIF)
→ dwidenoise (Marchenko-Pastur PCA 잡음 제거)
→ dwiextract + mrmath (b0 추출 및 평균)
→ dwi2mask (뇌 마스크)
→ dwi2tensor (텐서 적합)
→ tensor2metric (FA/MD/AD/RD 맵)
→ fslstats (마스크 내 평균값)
```

**출력 특징 (4개):**
| 특징 | 설명 | 정상 범위 |
|------|------|----------|
| `mean_fa` | 분획 비등방성 | 0.30~0.55 |
| `mean_md` | 평균 확산도 | 0.0007~0.0012 mm²/s |
| `mean_ad` | 축 확산도 | 0.001~0.0015 mm²/s |
| `mean_rd` | 방사 확산도 | 0.0005~0.001 mm²/s |

**출력 맵:** `fa.nii.gz`, `md.nii.gz`, `ad.nii.gz`, `rd.nii.gz`, `colorfa.mif`

### 8.5 Tractography (섬유경로 추적)

다중 조직 CSD + ACT 기반 전뇌 트랙토그래피 및 구조적 연결성 매트릭스를 생성합니다.

**파이프라인:**
```
DWI NIfTI + bvec/bval + FreeSurfer aparc+aseg
→ mrconvert → dwi2mask → dwi2response (dhollander)
→ dwi2fod (multi-tissue CSD)
→ FreeSurfer LUT 패치 (8.0 sclimbic 7열→6열 정규화)
→ 5ttgen freesurfer (5조직 분류 영상)
→ tckgen -act -backtrack (ACT 트랙토그래피)
→ tckstats (스트림라인 통계)
→ tck2connectome (DK84 연결성 매트릭스)
```

**주요 환경 변수:**
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `STREAMLINE_COUNT` | `10000` | 생성할 스트림라인 수 (테스트: 5000, 프로덕션: 100000+) |

**FreeSurfer 8.0 LUT 패치:**
FreeSurfer 8.0의 `FreeSurferColorLUT.txt` 파일에서 `sclimbic` 섹션(라인 819~)이 7열 형식으로 되어 있어 MRtrix3 `labelconvert`가 거부합니다. 컨테이너가 런타임에 LUT를 자동 패치(7열→6열)하여 해결합니다.

**출력 특징 (8개):** `streamline_count`, `mean_length`, `min_length`, `max_length`, `median_length`, `n_atlas_regions`, `n_connections`, `connectivity_density`

**출력 맵:** `WBT_{count}.tck` (트랙토그램), `connectome.csv` (84×84 연결성 매트릭스)

### 8.6 FDG-PET (포도당 대사 PET)

MATLAB/SPM25 기반 `neuroan_pet` 파이프라인을 래핑하여 FDG-PET 데이터의 통계 분석을 수행합니다.

**파이프라인:**
```
PET DICOM + T1 DICOM (또는 NIfTI)
→ spm_dicom_convert (DICOM→NIfTI)
→ 전처리: 공간정합(PET→T1) + 정규화(MNI 공간) + 6mm 가우시안 스무딩
→ 통계: ROI 기반 z-score + SPM two-sample t-test (vs 정상 대조군)
→ 보고서: MIP + Colin27 3D 렌더링 HTML
```

**필수 실행 조건:**

| 조건 | 이유 |
|------|------|
| `--net=host` | MATLAB 라이선스가 호스트 MAC 주소에 바인딩, 컨테이너 네트워크에서 검증 실패 |
| `LANG=en_US.UTF-8` | MATLAB R2025b가 POSIX 로케일에서 세그폴트 |
| `libgdk-pixbuf-2.0-0` | MATLAB R2025b 렌더링에 필수, 없으면 세그폴트 |
| Xvfb (가상 프레임버퍼) | SPM 리포트 생성 시 디스플레이 필요 |
| MathWorksServiceHost 강제 종료 | MATLAB 종료 후에도 데몬이 stdout 파이프를 잡고 있어 subprocess 블록 |

**출력 특징 (13개):**
| 특징 | 설명 |
|------|------|
| `zscore_mean/std/min/max` | Z-score 통계 |
| `hypometabolic_voxels` | 대사 저하 복셀 수 (z < -2) |
| `hypometabolic_fraction` | 대사 저하 비율 |
| `tmap_ncgt_pt_voxels/max_t` | NC>환자 T-맵 통계 |
| `tmap_ptgt_nc_voxels/max_t` | 환자>NC T-맵 통계 |
| `mean_uptake/std_uptake` | 섭취율 통계 |
| `global_metabolic_index` | 전체 대사 지수 (mean/max × 100) |

**출력 맵:** Z-score 맵, T-맵 (대사 저하/항진), 스무딩 PET, 정규화 PET, SPM.mat, HTML 보고서

---

## 9. 테스트 데이터 및 실행 스크립트

### 9.1 테스트 데이터 경로

| 데이터 | 경로 | 설명 |
|--------|------|------|
| **sub-001** 원본 ZIP | `/projects4/NEUROHUB/TEST/INPUT/sub-001_raw.zip` | T1 MRI + DTI DICOM |
| **sub-001** BIDS | `/projects1/pi/jhlee/01_neurohub/input/sub-001_raw_BIDS/` | 사전 변환된 BIDS |
| **sub-002** 원본 | `/projects4/NEUROHUB/TEST/INPUT/sub-002_raw/` | PET_tr + preT1 DICOM |
| **sub-003** 원본 | `/projects4/NEUROHUB/TEST/INPUT/sub-003_raw/` | T1 + fMRI (미테스트) |
| FreeSurfer 사전 계산 | `/projects4/NEUROHUB/TEST/INPUT/freesurfer/` | sub-001 recon-all 결과 |
| FDG 정상 대조군 DB | `/projects4/NEUROHUB/TEST/DB/FDG-NC/` | 정상 대조군 PET 데이터 |

### 9.2 sub-001 테스트 (T1 MRI + DTI) — 3개 컨테이너

서버에 SSH 접속 후 아래 명령을 순서대로 실행합니다.

#### Cortical Thickness (~10초, 사전 계산 모드)

```bash
sudo docker run --rm \
  -v /projects1/pi/jhlee/01_neurohub/input/sub-001_raw_BIDS:/input:ro \
  -v /usr/local/freesurfer/8.0.0:/opt/freesurfer:ro \
  -v /tmp/ct_test_output:/output \
  --memory 16g \
  -e NEUROHUB_SKIP_RECON=1 \
  neurohub/cortical-thickness:1.0.0
```

#### Diffusion Properties (~60초)

```bash
sudo docker run --rm \
  -v /projects1/pi/jhlee/01_neurohub/input/sub-001_raw_BIDS:/input:ro \
  -v /usr/local/fsl:/opt/fsl:ro \
  -v /usr/local/mrtrix3:/opt/mrtrix3:ro \
  -v /usr/local/freesurfer/8.0.0:/opt/freesurfer:ro \
  -v /tmp/dp_test_output:/output \
  --memory 16g \
  neurohub/diffusion-properties:1.0.0
```

#### Tractography (~120초, 5000 스트림라인)

```bash
sudo docker run --rm \
  -v /projects1/pi/jhlee/01_neurohub/input/sub-001_raw_BIDS:/input:ro \
  -v /usr/local/fsl:/opt/fsl:ro \
  -v /usr/local/mrtrix3:/opt/mrtrix3:ro \
  -v /usr/local/freesurfer/8.0.0:/opt/freesurfer:ro \
  -v /projects4/NEUROHUB/TEST/INPUT/freesurfer:/input/freesurfer:ro \
  -v /tmp/tck_test_output:/output \
  --memory 16g \
  -e STREAMLINE_COUNT=5000 \
  neurohub/tractography:1.0.0
```

### 9.3 sub-002 테스트 (FDG-PET) — 1개 컨테이너

#### FDG-PET (~5~10분)

```bash
sudo docker run --rm --net=host \
  -v /projects4/NEUROHUB/TEST/INPUT/sub-002_raw:/input:ro \
  -v /projects4/NEUROHUB/TEST/DB/FDG-NC:/db:ro \
  -v /projects4/NEUROHUB/TEST/INPUT/freesurfer:/input/freesurfer:ro \
  -v /usr/local/freesurfer/8.0.0:/opt/freesurfer:ro \
  -v /usr/local/MATLAB/R2025b:/opt/matlab:ro \
  -v /usr/local/spm25:/opt/spm25:ro \
  -v /tmp/pet_test_output:/output \
  --memory 16g \
  -e LANG=en_US.UTF-8 \
  neurohub/fdg-pet:1.0.0
```

> **주의**: FDG-PET 컨테이너는 반드시 `--net=host`와 `LANG=en_US.UTF-8`을 사용해야 합니다.

### 9.4 결과 확인

각 컨테이너 실행 후 stdout에서 `NEUROHUB_OUTPUT:` 라인을 확인합니다:

```bash
# 출력 디렉토리 확인
ls -la /tmp/ct_test_output/     # Cortical Thickness
ls -la /tmp/dp_test_output/     # Diffusion Properties
ls -la /tmp/tck_test_output/    # Tractography
ls -la /tmp/pet_test_output/    # FDG-PET
```

### 9.5 Docker 이미지 빌드

이미지가 없는 경우 서버에서 빌드합니다:

```bash
cd ~/neurohub-platform/neurohub-repo/containers

# 각 컨테이너 빌드 (~30초/개)
sudo docker build -t neurohub/cortical-thickness:1.0.0 cortical-thickness/
sudo docker build -t neurohub/diffusion-properties:1.0.0 diffusion-properties/
sudo docker build -t neurohub/tractography:1.0.0 tractography/
sudo docker build -t neurohub/fdg-pet:1.0.0 fdg-pet/

# 빌드 확인
sudo docker images | grep neurohub
```

---

## 10. 테스트 결과 요약

### 10.1 sub-001 (T1 MRI + DTI) 최종 결과

| 컨테이너 | 상태 | QC | Confidence | 특징 수 | QC 플래그 |
|-----------|------|-----|-----------|---------|----------|
| Cortical Thickness | **PASS** | 85.0 | 76.5 | 181개 | 없음 |
| Diffusion Properties | **PASS** (경고) | 70.0 | 59.5 | 4개 | `FA_OUTSIDE_NORMAL_RANGE` |
| Tractography | **PASS** | 95.0 | 80.8 | 8개 | 없음 |
| 퓨전 엔진 | **PASS** | — | 81.7 | 11개 통합 | 일치도 1.000 |

### 10.2 sub-002 (FDG-PET) 최종 결과

| 컨테이너 | 상태 | QC | 특징 수 | 출력 |
|-----------|------|-----|---------|------|
| FDG-PET | **PASS** | 85.0 | 13개 | Z-score 맵, T-맵, 스무딩 PET, SPM.mat |

### 10.3 퓨전 엔진 가중치 (파킨슨 진단 서비스)

| 기법 | 기본 가중치 | QC | 조정 가중치 |
|------|-----------|-----|-----------|
| Cortical_Thickness | 0.15 | 85.0 | 0.1275 |
| Diffusion_Properties | 0.20 | 70.0 | 0.1400 |
| Tractography | 0.00 | 95.0 | 0.0000 |

### 10.4 성능 (소요 시간)

| 테스트 | 시간 |
|--------|------|
| Docker 이미지 빌드 (각) | ~30초 |
| Cortical Thickness (사전 계산) | ~10초 |
| Diffusion Properties | ~60초 |
| Tractography (5K 스트림라인) | ~120초 |
| FDG-PET (MATLAB/SPM25) | ~5~10분 |
| 퓨전 엔진 | <1초 |

### 10.5 알려진 이슈 및 해결

| 이슈 | 원인 | 해결 |
|------|------|------|
| MRtrix3 `libtiff.so.5` 누락 | `python:3.12-slim`(Bookworm)에 libtiff6만 존재 | 베이스를 `ubuntu:22.04`로 변경 |
| FreeSurfer 8.0 LUT 7열 오류 | sclimbic 섹션이 비표준 7열 | 런타임 LUT 패치 (7열→6열) |
| MATLAB 세그폴트 | POSIX 로케일 + libgdk-pixbuf 누락 | `LANG=en_US.UTF-8` + 패키지 설치 |
| MATLAB 라이선스 실패 | 컨테이너 네트워크에서 MAC 주소 불일치 | `--net=host` 사용 |
| MathWorksServiceHost 블록 | MATLAB 종료 후 데몬이 stdout 점유 | 강제 kill 로직 추가 |

---

## 11. 백엔드 테스트

38개 테스트 파일 — 상태 머신, 요청 CRUD, 업로드, 컨테이너 실행, 기법 오케스트레이션, 융합 엔진, 파이프라인, ZIP 프로세서, Pre-QC, AI 에이전트, 속도 제한, 리콘실러, 웹훅 등.

```bash
# 전체 테스트
cd apps/api && source venv/bin/activate && pytest

# 특정 파일
pytest tests/test_zip_processor.py -v
pytest tests/test_pipeline_orchestrator.py -v
pytest tests/test_container_runner.py -v
pytest tests/test_fusion_engine.py -v

# 프론트엔드 E2E
cd apps/web && bunx playwright test
```

---

## 12. 배포

### 12.1 프론트엔드 배포 (서버)

```bash
# 1. 로컬에서 rsync (반드시 .env.local 제외)
rsync -avz --exclude .env.local --exclude node_modules --exclude .next \
  -e "ssh -p 3093" apps/web/ yookj@103.22.220.93:~/neurohub-platform/neurohub-repo/apps/web/

# 2. 서버에서 빌드 전 확인
cat ~/neurohub-platform/neurohub-repo/apps/web/.env.local | grep API_ORIGIN
# → 반드시 http://localhost:8080 이어야 함

# 3. 빌드
cd ~/neurohub-platform/neurohub-repo/apps/web && bun run build

# 4. 빌드 후 포트 확인
grep -o 'localhost:80[0-9]*' .next/standalone/.next/routes-manifest.json | sort -u
# → localhost:8080 이어야 함

# 5. 재시작
bash /tmp/restart-web.sh
```

### 12.2 백엔드 배포 (서버)

```bash
# 1. rsync (반드시 .env 제외)
rsync -avz --exclude .env --exclude venv --exclude __pycache__ \
  -e "ssh -p 3093" apps/api/ yookj@103.22.220.93:~/neurohub-platform/neurohub-repo/apps/api/

# 2. 마이그레이션
cd ~/neurohub-platform/neurohub-repo/apps/api && source venv/bin/activate
alembic upgrade head

# 3. API 재시작
pkill -f 'uvicorn app.main' && sleep 2
nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 >> ~/neurohub-platform/logs/api.log 2>&1 &

# 4. Celery 재시작 (워커 코드 변경 시)
pkill -f celery && sleep 2
nohup celery -A app.worker.celery_app:celery_app worker -Q compute,reporting -l info --concurrency=4 \
  > ~/neurohub-platform/logs/celery.log 2>&1 &
```

### 12.3 배포 후 검증 (필수)

```bash
# 1. API 상태
curl -s http://localhost:8080/api/v1/health

# 2. 인증 (API 직접)
curl -s http://localhost:8080/api/v1/auth/login -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@neurohub.com","password":"asdfasdf"}'

# 3. 인증 (Next.js 프록시 — 포트 불일치 감지)
curl -s http://localhost:3000/api/v1/auth/login -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@neurohub.com","password":"asdfasdf"}'

# 4. 서비스 목록
TOKEN=$(curl -s http://localhost:8080/api/v1/auth/login -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@neurohub.com","password":"asdfasdf"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:3000/api/v1/services | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"items\"])} services')"

# 5. Next.js 로그 확인
tail -5 /tmp/neurohub-web.log
```

---

## 13. 문서

| 문서 | 경로 |
|------|------|
| 기술 PRD (한국어) | [docs/TECHNICAL_PRD_KR.md](docs/TECHNICAL_PRD_KR.md) |
| 컨테이너 테스트 보고서 | [docs/CONTAINER_TEST_REPORT.md](docs/CONTAINER_TEST_REPORT.md) |
| 플랫폼 감사 및 로드맵 | [docs/AUDIT_AND_ROADMAP.md](docs/AUDIT_AND_ROADMAP.md) |
| UX/UI 성능 감사 | [docs/AUDIT_UIUX_PERFORMANCE.md](docs/AUDIT_UIUX_PERFORMANCE.md) |

### 사용자 역할

| 역할 | 기능 |
|------|------|
| 의사 / 기사 | 6단계 마법사 분석 요청, 상태 추적, 결과 조회, DICOM 워크리스트 |
| 전문가 리뷰어 | QC 리뷰 큐, 구조화 피드백/어노테이션, 모델 성능 추적 |
| 시스템 관리자 | 사용자/기관 관리, 서비스 설정, 기법 관리, DICOM 게이트웨이, 감사 로그 |

---

## License

Private. All rights reserved.
