import traceback

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .logging_config import configure_logging, get_logger
from .middleware.audit import AuditLogMiddleware
from .routers import admin, auth, compute, copilot, core, experiments, files, jobs, registry, workflow_mgmt
from .services.artifacts import ensure_artifact_dirs
from .settings import get_settings

configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="BDA API Gateway",
    version="1.0.0",
    description="API gateway for BDA Workbench projects, workflows, candidates, compute, and plugin registry.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditLogMiddleware)

api_v1 = APIRouter(prefix="/api/v1")

api_v1.include_router(auth.router)
api_v1.include_router(core.router)
api_v1.include_router(files.router)
api_v1.include_router(experiments.router)
api_v1.include_router(registry.router)
api_v1.include_router(compute.router)
api_v1.include_router(jobs.router)
api_v1.include_router(copilot.router)
api_v1.include_router(workflow_mgmt.router)
api_v1.include_router(admin.router)

app.include_router(api_v1)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "http_error",
            "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "details": {"path": request.url.path},
            "trace_id": request.headers.get("x-trace-id", "unavailable"),
            "retryable": exc.status_code >= 500,
        },
    )


@app.exception_handler(Exception)
async def standard_error_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        traceback=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "internal_error",
            "message": "Unexpected backend error.",
            "details": {"path": request.url.path},
            "trace_id": request.headers.get("x-trace-id", "unavailable"),
            "retryable": False,
        },
    )


ensure_artifact_dirs()
