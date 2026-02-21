# NeuroHub Web

## Stack
- Next.js 16 (App Router)
- TypeScript strict mode
- Tailwind CSS v4
- Radix UI
- TanStack Query
- Supabase JS (auth session)
- Biome

## Run

```bash
cp .env.local.example .env.local
bun install
bun run dev
```

## Notes
- 기본 언어: 한국어 (`ko`)
- Supabase 세션이 없으면 개발용 헤더 fallback을 사용합니다.
- 운영에서는 API `ALLOW_DEV_AUTH_FALLBACK=false`로 고정하세요.
