import uuid

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .logging_config import configure_logging, get_logger
from .middleware.audit import AuditLogMiddleware
from .middleware.security import RateLimitMiddleware, SecurityHeadersMiddleware
from .routers import admin, auth, campaigns, compute, copilot, core, experiments, files, jobs, registry, workflow_mgmt
from .services.artifacts import ensure_artifact_dirs
from .settings import get_settings

configure_logging()
logger = get_logger(__name__)

settings = get_settings()

_config_problems = settings.validate_for_environment()
if _config_problems:
    summary = "; ".join(_config_problems)
    if settings.is_production:
        raise RuntimeError(f"Refusing to start with insecure configuration: {summary}")
    logger.warning("insecure_configuration", problems=_config_problems)

app = FastAPI(
    title="BDA API Gateway",
    version="1.0.0",
    description="API gateway for BDA Workbench projects, workflows, candidates, compute, and plugin registry.",
    docs_url="/api/docs" if settings.docs_enabled else None,
    redoc_url="/api/redoc" if settings.docs_enabled else None,
    openapi_url="/api/openapi.json" if settings.docs_enabled else None,
)

ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
ALLOWED_HEADERS = ["Authorization", "Content-Type", "X-Requested-With", "X-Trace-Id"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    max_age=600,
)
app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)
if settings.bda_rate_limit_enabled:
    app.add_middleware(
        RateLimitMiddleware,
        default_per_minute=settings.bda_rate_limit_per_minute,
        auth_per_minute=settings.bda_auth_rate_limit_per_minute,
    )
app.add_middleware(AuditLogMiddleware)

api_v1 = APIRouter(prefix="/api/v1")

api_v1.include_router(auth.router)
api_v1.include_router(auth.users_router)
api_v1.include_router(core.router)
api_v1.include_router(files.router)
api_v1.include_router(experiments.router)
api_v1.include_router(registry.router)
api_v1.include_router(compute.router)
api_v1.include_router(jobs.router)
api_v1.include_router(copilot.router)
api_v1.include_router(campaigns.router)
api_v1.include_router(workflow_mgmt.router)
api_v1.include_router(admin.router)

app.include_router(api_v1)


@app.get("/api/v1/metrics")
def prometheus_metrics():
    """Prometheus scrape endpoint (internal network only in production)."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _trace_id(request: Request) -> str:
    """Honor an inbound trace id but always fall back to a server-generated one."""
    return request.headers.get("x-trace-id") or f"trace_{uuid.uuid4().hex[:16]}"


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    trace_id = _trace_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "http_error",
            "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "details": {"path": request.url.path},
            "trace_id": trace_id,
            "retryable": exc.status_code >= 500,
        },
        headers={"X-Trace-Id": trace_id},
    )


@app.exception_handler(Exception)
async def standard_error_handler(request: Request, exc: Exception):
    trace_id = _trace_id(request)
    # Log full detail server-side (with the trace id) but never leak it to clients.
    logger.exception(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        trace_id=trace_id,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "internal_error",
            "message": "Unexpected backend error.",
            "details": {"path": request.url.path},
            "trace_id": trace_id,
            "retryable": False,
        },
        headers={"X-Trace-Id": trace_id},
    )


ensure_artifact_dirs()
