from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
    bda_compute_mode: str = "demo"  # demo | docker
    bda_docker_host: str = "unix:///var/run/docker.sock"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.bda_cors_origins.split(",") if o.strip()]

    @property
    def is_postgresql(self) -> bool:
        return self.bda_db_path.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()
