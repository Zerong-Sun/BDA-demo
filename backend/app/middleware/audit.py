from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class AuditLogMiddleware(BaseHTTPMiddleware):
    WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method not in self.WRITE_METHODS:
            return response
        if not request.url.path.startswith("/api/v1"):
            return response
        try:
            from ..db import connect

            connection = connect()
            try:
                actor_id = None
                auth = request.headers.get("authorization", "")
                if auth.startswith("Bearer "):
                    from ..auth.service import decode_token, get_user_by_username

                    try:
                        payload = decode_token(auth[7:])
                        user = get_user_by_username(connection, payload.get("sub", ""))
                        actor_id = user["user_id"] if user else None
                    except Exception:
                        pass

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
            finally:
                connection.close()
        except Exception:
            pass
        return response
