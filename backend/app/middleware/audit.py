from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..logging_config import get_logger

logger = get_logger(__name__)


class AuditLogMiddleware(BaseHTTPMiddleware):
    WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method not in self.WRITE_METHODS:
            return response
        if not request.url.path.startswith("/api/v1"):
            return response

        connection = None
        try:
            from ..db import connect, release_connection

            connection = connect()
            actor_id = self._resolve_actor(request, connection)
            connection.execute(
                """
                INSERT INTO audit_logs (audit_id, actor_id, action, entity_type, entity_id, project_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"audit_{uuid.uuid4().hex[:12]}",
                    actor_id,
                    f"{request.method} {request.url.path}",
                    "http_request",
                    None,
                    request.query_params.get("project_id"),
                    json.dumps({"status_code": response.status_code}),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.commit()
        except Exception as exc:  # noqa: BLE001
            if connection is not None:
                connection.rollback()
            logger.warning(
                "audit_log_write_failed",
                path=request.url.path,
                method=request.method,
                error=str(exc),
            )
        finally:
            if connection is not None:
                from ..db import release_connection

                release_connection(connection)
        return response

    @staticmethod
    def _resolve_actor(request: Request, connection) -> str | None:
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return None
        from ..auth.service import decode_token, get_user_by_username

        try:
            payload = decode_token(auth[7:])
            user = get_user_by_username(connection, payload.get("sub", ""))
            return user["user_id"] if user else None
        except Exception:  # noqa: BLE001 - unauthenticated/invalid token is expected
            return None
