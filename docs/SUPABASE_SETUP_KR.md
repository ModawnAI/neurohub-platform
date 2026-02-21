# NeuroHub Supabase 설정 가이드 (KR)

## 1. 현재 상태
- `supabase init` 완료: `/Users/paksungho/Downloads/neurohub/NeuroHub/supabase/config.toml`
- Supabase CLI 토큰 로그인 완료 (`neurohub-local` 프로필)
- 스토리지/RLS 부트스트랩 SQL 추가:
  - `/Users/paksungho/Downloads/neurohub/NeuroHub/supabase/migrations/20260221130000_neurohub_storage_and_rls.sql`

## 2. 프로젝트 준비
NeuroHub 전용 Supabase 프로젝트를 선택해야 합니다.

1. 기존 프로젝트 연결:
```bash
cd /Users/paksungho/Downloads/neurohub/NeuroHub
supabase link --project-ref <YOUR_PROJECT_REF> --password '<DB_PASSWORD>'
```

2. 신규 프로젝트 생성(필요 시):
```bash
supabase projects create NeuroHub \
  --org-id <YOUR_ORG_ID> \
  --region ap-northeast-2 \
  --db-password '<STRONG_DB_PASSWORD>'
```

## 3. 환경변수 세팅

### API (`/Users/paksungho/Downloads/neurohub/NeuroHub/apps/api/.env`)
```env
DATABASE_URL=postgresql+asyncpg://postgres:<DB_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres
REDIS_URL=redis://<REDIS_HOST>:6379/0
SUPABASE_URL=https://<PROJECT_REF>.supabase.co
SUPABASE_JWKS_URL=https://<PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_ISSUER=https://<PROJECT_REF>.supabase.co/auth/v1
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_ANON_KEY=<SUPABASE_ANON_KEY>
SUPABASE_SERVICE_ROLE_KEY=<SUPABASE_SERVICE_ROLE_KEY>
ALLOW_DEV_AUTH_FALLBACK=false
```

### Web (`/Users/paksungho/Downloads/neurohub/NeuroHub/apps/web/.env.local`)
```env
NEXT_PUBLIC_API_BASE=https://api.neurohub.example/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://<PROJECT_REF>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<SUPABASE_ANON_KEY>
```

## 4. 스키마/정책 적용 순서

1. Python 도메인 스키마(Alembic):
```bash
cd /Users/paksungho/Downloads/neurohub/NeuroHub/apps/api
alembic upgrade head
python scripts/seed_dev.py
```

2. Supabase 스토리지/RLS SQL 적용:
```bash
cd /Users/paksungho/Downloads/neurohub/NeuroHub
supabase db push --include-all
```

## 5. 점검 체크리스트
- `storage.buckets`에 아래 3개 버킷 존재
  - `neurohub-inputs`
  - `neurohub-outputs`
  - `neurohub-reports`
- JWT claim에 `institution_id` 포함
- 기관 A 토큰으로 기관 B `requests` 조회 시 차단되는지 확인
- `ALLOW_DEV_AUTH_FALLBACK=false`에서 헤더 인증이 차단되는지 확인
