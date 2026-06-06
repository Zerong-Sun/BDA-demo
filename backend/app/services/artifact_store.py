from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..config import ARTIFACTS_ROOT
from ..settings import get_settings


class ArtifactStore(ABC):
    @abstractmethod
    def save_file(self, key: str, source: Path) -> str: ...

    @abstractmethod
    def get_local_path(self, key: str) -> Path: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...


class LocalArtifactStore(ArtifactStore):
    def save_file(self, key: str, source: Path) -> str:
        dest = ARTIFACTS_ROOT / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source != dest:
            dest.write_bytes(source.read_bytes())
        return key

    def get_local_path(self, key: str) -> Path:
        return ARTIFACTS_ROOT / key

    def exists(self, key: str) -> bool:
        return (ARTIFACTS_ROOT / key).exists()


class MinioArtifactStore(ArtifactStore):
    def __init__(self) -> None:
        from minio import Minio

        settings = get_settings()
        self._client = Minio(
            settings.bda_minio_endpoint,
            access_key=settings.bda_minio_access_key,
            secret_key=settings.bda_minio_secret_key,
            secure=settings.bda_minio_secure,
        )
        self._bucket = settings.bda_minio_bucket
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def save_file(self, key: str, source: Path) -> str:
        self._client.fput_object(self._bucket, key, str(source))
        return key

    def get_local_path(self, key: str) -> Path:
        dest = ARTIFACTS_ROOT / "cache" / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            self._client.fget_object(self._bucket, key, str(dest))
        return dest

    def exists(self, key: str) -> bool:
        try:
            self._client.stat_object(self._bucket, key)
            return True
        except Exception:
            return False


def get_artifact_store() -> ArtifactStore:
    settings = get_settings()
    if settings.bda_artifacts_backend == "minio":
        return MinioArtifactStore()
    return LocalArtifactStore()
