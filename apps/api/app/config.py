from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "NeuroHub API"
    app_env: str = "development"
    app_debug: bool = False
    app_version: str = "0.1.0"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/neurohub"
    redis_url: str = "redis://localhost:6379/0"

    # Supabase integration (do not hardcode values in source code)
    supabase_url: str = ""
    supabase_jwks_url: str = ""
    supabase_issuer: str = ""
    supabase_jwt_audience: str = "authenticated"
    supabase_jwt_clock_skew_seconds: int = 30
    supabase_jwks_cache_ttl_seconds: int = 300
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    allow_dev_auth_fallback: bool = True

    # Storage (Supabase bucket names)
    storage_bucket_inputs: str = "neurohub-inputs"
    storage_bucket_outputs: str = "neurohub-outputs"
    storage_bucket_reports: str = "neurohub-reports"

    # Backward-compatible default tenant during migration stage
    default_institution_id: str = "00000000-0000-0000-0000-000000000001"

    # Toss Payments
    toss_secret_key: str = ""
    toss_client_key: str = ""

    # Reconciler
    stale_run_threshold_minutes: int = 30
    max_run_retries: int = 3

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("+asyncpg", "")


settings = Settings()
