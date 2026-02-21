# NeuroHub Fly.io 배포 가이드 (KR)

## 1. 배포 파일
- API: `/Users/paksungho/Downloads/neurohub/NeuroHub/infra/fly/api/fly.toml`
- Worker: `/Users/paksungho/Downloads/neurohub/NeuroHub/infra/fly/worker/fly.toml`
- Reconciler: `/Users/paksungho/Downloads/neurohub/NeuroHub/infra/fly/reconciler/fly.toml`
- 공통 이미지: `/Users/paksungho/Downloads/neurohub/NeuroHub/apps/api/Dockerfile`

## 2. 사전 준비
```bash
fly auth login
```

Fly API 토큰을 사용하는 경우:
```bash
export FLY_API_TOKEN='<ROTATED_TOKEN>'
```

## 3. 앱 생성
```bash
fly apps create neurohub-api
fly apps create neurohub-worker
fly apps create neurohub-reconciler
```

## 4. 시크릿 주입
각 앱에 공통으로 아래 시크릿을 넣습니다.

```bash
fly secrets set \
  DATABASE_URL='postgresql+asyncpg://postgres:<PW>@db.<PROJECT_REF>.supabase.co:5432/postgres' \
  REDIS_URL='redis://<REDIS_HOST>:6379/0' \
  SUPABASE_URL='https://<PROJECT_REF>.supabase.co' \
  SUPABASE_JWKS_URL='https://<PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json' \
  SUPABASE_ISSUER='https://<PROJECT_REF>.supabase.co/auth/v1' \
  SUPABASE_JWT_AUDIENCE='authenticated' \
  SUPABASE_ANON_KEY='<ANON_KEY>' \
  SUPABASE_SERVICE_ROLE_KEY='<SERVICE_ROLE_KEY>' \
  APP_ENV='production' \
  APP_DEBUG='false' \
  ALLOW_DEV_AUTH_FALLBACK='false' \
  -a neurohub-api
```

Worker/Reconciler도 동일하게 `-a`만 바꿔 주입합니다.

## 5. 배포

### API
```bash
cd /Users/paksungho/Downloads/neurohub/NeuroHub
fly deploy --config infra/fly/api/fly.toml
```

### Worker
```bash
cd /Users/paksungho/Downloads/neurohub/NeuroHub
fly deploy --config infra/fly/worker/fly.toml
```

### Reconciler
```bash
cd /Users/paksungho/Downloads/neurohub/NeuroHub
fly deploy --config infra/fly/reconciler/fly.toml
```

## 6. 운영 체크
- API health: `GET /api/v1/health`
- Worker 로그: `fly logs -a neurohub-worker`
- Reconciler 로그: `fly logs -a neurohub-reconciler`
- API release command로 `alembic upgrade head`가 실행되는지 확인
