from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[1]

INSECURE_JWT_SECRETS = frozenset({"change-me-in-production", "", "secret", "changeme"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # development | production. Controls startup hardening checks and docs exposure.
    bda_env: str = "development"
    bda_db_path: str = str(REPO_ROOT / "db" / "bda.sqlite3")
    bda_cors_origins: str = "http://localhost:4173,http://127.0.0.1:4173,http://localhost:5173,http://127.0.0.1:5173"
    bda_jwt_secret: str = "change-me-in-production"
    bda_jwt_algorithm: str = "HS256"
    bda_jwt_expire_minutes: int = 480
    bda_artifacts_backend: str = "local"
    bda_minio_endpoint: str = "localhost:9000"
    bda_minio_access_key: str = "minioadmin"
    bda_minio_secret_key: str = "minioadmin"
    bda_minio_bucket: str = "bda-artifacts"
    bda_minio_secure: bool = False
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    bda_compute_mode: str = "demo"  # demo | local | docker
    bda_docker_host: str = "unix:///var/run/docker.sock"

    # Maximum accepted upload size in bytes (default 25 MiB). Guards against memory/disk DoS.
    bda_max_upload_bytes: int = 25 * 1024 * 1024
    # Sliding-window rate limits (requests per minute, per client IP).
    bda_rate_limit_enabled: bool = True
    bda_rate_limit_per_minute: int = 300
    bda_auth_rate_limit_per_minute: int = 30
    # Expose Swagger/OpenAPI docs. Disabled automatically in production unless overridden.
    bda_expose_docs: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.bda_cors_origins.split(",") if o.strip()]

    @property
    def is_postgresql(self) -> bool:
        return self.bda_db_path.startswith("postgresql")

    @property
    def is_production(self) -> bool:
        return self.bda_env.strip().lower() in {"production", "prod"}

    @property
    def docs_enabled(self) -> bool:
        return self.bda_expose_docs and not self.is_production

    def validate_for_environment(self) -> list[str]:
        """Return a list of fatal misconfigurations for the current environment.

        Empty list means the configuration is safe to boot. In production a
        non-empty list should abort startup; in development it is advisory.
        """
        problems: list[str] = []
        if self.is_production:
            if self.bda_jwt_secret.strip() in INSECURE_JWT_SECRETS:
                problems.append(
                    "BDA_JWT_SECRET is unset or uses an insecure default; set a strong random secret."
                )
            if len(self.bda_jwt_secret) < 32:
                problems.append("BDA_JWT_SECRET must be at least 32 characters in production.")
            if not self.cors_origins_list or "*" in self.cors_origins_list:
                problems.append("BDA_CORS_ORIGINS must be an explicit allowlist in production.")
            if self.bda_artifacts_backend == "minio" and self.bda_minio_secret_key == "minioadmin":
                problems.append("MinIO credentials must not use the default 'minioadmin' in production.")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
