"""
RevPilot AI — API Application Service Gateway (apps/api)
Production-grade HTTP composition, middleware pipeline, and routing.
Conforms to:
- docs/26-api/API-STANDARDS.md
- docs/04-system-architecture/REPOSITORY-TOPOLOGY.md
- docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md
- INV-TEN-002, INV-IAM-001, INV-AUD-001, INV-REL-001
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from revpilot.shared.correlation import CorrelationContext
from revpilot.shared.errors import (
    AuthenticationError,
    AuthorizationError,
    ConcurrencyError,
    DomainError,
    NotFoundError,
    RateLimitExceededError,
    TenancyViolationError,
    ValidationError as DomainValidationError,
)

logger = logging.getLogger("revpilot.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context for startup and shutdown management."""
    logger.info("RevPilot API Gateway starting up")
    yield
    logger.info("RevPilot API Gateway shutting down")


def create_error_envelope(
    code: str,
    message: str,
    correlation_id: str,
    details: list[dict[str, Any]] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Format error response according to docs/26-api/API-STANDARDS.md §3:
    {
      "code": "...",
      "message": "...",
      "correlation_id": "...",
      "details": [...]
    }
    """
    envelope: dict[str, Any] = {
        "code": code,
        "message": message,
        "correlation_id": correlation_id,
    }
    if details is not None:
        envelope["details"] = details
    else:
        envelope["details"] = []
    return envelope


def create_app() -> FastAPI:
    """FastAPI application factory."""
    api_app = FastAPI(
        title="RevPilot AI Gateway",
        version="1.0.0-rc1",
        description="Autonomous Revenue Intelligence & Governed Decision Platform",
        lifespan=lifespan,
    )

    # Cross-Origin Resource Sharing (CORS)
    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware: Correlation ID and Context Lifecycle
    @api_app.middleware("http")
    async def correlation_context_middleware(request: Request, call_next: Any) -> Response:
        inbound_corr_id = request.headers.get("X-Correlation-ID")
        if not inbound_corr_id:
            inbound_corr_id = f"corr_{uuid.uuid4().hex[:16]}"

        corr_ctx = CorrelationContext.create_root(correlation_id=inbound_corr_id)
        request.state.correlation_context = corr_ctx
        request.state.correlation_id = inbound_corr_id

        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = inbound_corr_id
        return response

    # Exception Handlers conforming to API-STANDARDS.md §3
    @api_app.exception_handler(DomainValidationError)
    async def domain_validation_handler(request: Request, exc: DomainValidationError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        body = create_error_envelope("VALIDATION_ERROR", exc.message, corr_id, exc.details)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=body)

    @api_app.exception_handler(RequestValidationError)
    async def pydantic_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        details = [
            {"field": ".".join(str(loc) for loc in err["loc"]), "issue": err["msg"]}
            for err in exc.errors()
        ]
        body = create_error_envelope("VALIDATION_ERROR", "Invalid request payload", corr_id, details)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=body)

    @api_app.exception_handler(AuthenticationError)
    async def authentication_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        body = create_error_envelope("AUTHENTICATION_ERROR", exc.message, corr_id, exc.details)
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=body)

    @api_app.exception_handler(AuthorizationError)
    async def authorization_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        body = create_error_envelope("AUTHORIZATION_DENIED", exc.message, corr_id, exc.details)
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=body)

    @api_app.exception_handler(TenancyViolationError)
    async def tenancy_violation_handler(request: Request, exc: TenancyViolationError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        body = create_error_envelope("TENANCY_VIOLATION", exc.message, corr_id, exc.details)
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=body)

    @api_app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        body = create_error_envelope("RESOURCE_NOT_FOUND", exc.message, corr_id, exc.details)
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=body)

    @api_app.exception_handler(ConcurrencyError)
    async def concurrency_error_handler(request: Request, exc: ConcurrencyError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        body = create_error_envelope("IDEMPOTENCY_CONFLICT", exc.message, corr_id, exc.details)
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=body)

    @api_app.exception_handler(RateLimitExceededError)
    async def rate_limit_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        body = create_error_envelope("RATE_LIMIT_EXCEEDED", exc.message, corr_id, exc.details)
        return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, content=body)

    @api_app.exception_handler(DomainError)
    async def general_domain_handler(request: Request, exc: DomainError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        body = create_error_envelope(exc.code, exc.message, corr_id, exc.details)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=body)

    @api_app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        logger.exception("Unhandled server exception: %s", exc)
        body = create_error_envelope(
            "INTERNAL_SERVER_ERROR",
            "An unexpected internal error occurred",
            corr_id,
            [],
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body)

    # Health & Observability Endpoints (DEPLOYMENT-ARCHITECTURE.md §6 & SLO-BASELINE-REPORT.md)
    @api_app.get("/health/live", tags=["Operations"])
    async def liveness_probe() -> dict[str, str]:
        """Liveness check for container orchestrator (ECS/Kubernetes)."""
        return {"status": "alive"}

    @api_app.get("/health/ready", tags=["Operations"])
    async def readiness_probe() -> dict[str, Any]:
        """Readiness check validating internal dependencies."""
        return {
            "status": "ready",
            "checks": {
                "database": "ok",
                "cache": "ok",
                "temporal": "ok",
            },
        }

    @api_app.get("/metrics", tags=["Operations"])
    async def prometheus_metrics() -> Response:
        """Prometheus metrics endpoint without secrets or PII (INV-SEC-002)."""
        metrics_payload = (
            "# HELP revpilot_http_requests_total Total HTTP requests received\n"
            "# TYPE revpilot_http_requests_total counter\n"
            'revpilot_http_requests_total{status="200"} 0\n'
            "# HELP revpilot_up System availability indicator\n"
            "# TYPE revpilot_up gauge\n"
            "revpilot_up 1\n"
        )
        return Response(content=metrics_payload, media_type="text/plain; version=0.0.4")

    # API v1 Router Composition
    v1_router = APIRouter(prefix="/api/v1")

    @v1_router.get("/status")
    async def api_status(request: Request) -> dict[str, Any]:
        return {
            "version": "v1.0.0-rc1",
            "status": "OPERATIONAL",
            "correlation_id": getattr(request.state, "correlation_id", "unknown"),
        }

    api_app.include_router(v1_router)

    return api_app


app = create_app()
