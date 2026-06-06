from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import compute, copilot, core, experiments, files, registry, workflow_mgmt
from .services.artifacts import ensure_artifact_dirs

app = FastAPI(
    title="BDA API Gateway",
    version="0.1.0",
    description="MVP API gateway for BDA Workbench projects, workflows, candidates, compute, and plugin registry.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

app.include_router(core.router)
app.include_router(files.router)
app.include_router(experiments.router)
app.include_router(registry.router)
app.include_router(compute.router)
app.include_router(copilot.router)
app.include_router(workflow_mgmt.router)

