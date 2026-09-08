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
import os
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
from apps.api.middleware.audit import AuditMiddleware
from apps.api.routers.analytics import router as analytics_router
from apps.api.routers.investigations import router as investigations_router
from apps.api.routers.causal import router as causal_router
from apps.api.routers.decisions import router as decisions_router
from apps.api.routers.approvals import router as approvals_router
from apps.api.routers.admin import router as admin_router
from apps.api.routers.connectors import router as connectors_router
from apps.api.routers.scim import router as scim_router
from apps.api.routers.mfa import router as mfa_router

logger = logging.getLogger("revpilot.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context for startup, database pooling, and graceful shutdown."""
    logger.info("RevPilot API Gateway starting up")

    env = os.getenv("ENVIRONMENT", "production")
    if env not in ("production", "staging", "test"):
        raise SystemExit(f"Unknown ENVIRONMENT value: {env!r}")

    db_url = os.getenv("DATABASE_URL")
    pool = None

    if env == "test":
        logger.info("Test environment: skipping database pool initialization")
    else:
        if not db_url:
            raise SystemExit("FATAL: DATABASE_URL is required for non-test environments")
        try:
            from revpilot.infrastructure.database import create_database_pool
            pool = await create_database_pool(db_url, min_size=2, max_size=10)
            app.state.db_pool = pool
            logger.info("Database pool initialized successfully")
        except Exception as exc:
            raise SystemExit(f"FATAL: Database initialization failed: {exc}") from exc

    # Initialize repository adapters
    if pool is not None:
        from revpilot.modules.tenancy.adapters.postgres_repository import PostgresTenantRepository
        from revpilot.modules.identity.adapters.postgres_repository import PostgresAuthAdapter
        from revpilot.modules.analytics.adapters.postgres_repository import PostgresAnomalyRepository
        from revpilot.modules.investigation.adapters.postgres_repository import PostgresInvestigationRepository
        from revpilot.modules.retrieval.adapters.postgres_evidence_repository import PostgresEvidenceRepository
        from revpilot.modules.hypothesis.adapters.postgres_repository import PostgresHypothesisRepository
        from revpilot.modules.causal.adapters.postgres_repository import PostgresCausalStudyRepository
        from revpilot.modules.decision.adapters.postgres_repository import PostgresDecisionRepository
        from revpilot.modules.approval.adapters.postgres_repository import PostgresApprovalRepository
        from revpilot.modules.action.adapters.postgres_ledger import PostgresActionLedger
        from revpilot.modules.safety.adapters.postgres_killswitch import PostgresKillSwitchRepository
        from revpilot.modules.connectors.adapters.postgres_repository import PostgresConnectorRepository
        from revpilot.modules.connectors.adapters.postgres_inbox import PostgresConnectorInbox
        from revpilot.modules.finops.adapters.postgres_audit_log import PostgresAuditLog

        app.state.tenant_repo = PostgresTenantRepository(pool)
        app.state.auth_adapter = PostgresAuthAdapter(pool)
        app.state.anomaly_repo = PostgresAnomalyRepository(pool)
        app.state.investigation_repo = PostgresInvestigationRepository(pool)
        app.state.evidence_repo = PostgresEvidenceRepository(pool)
        app.state.hypothesis_repo = PostgresHypothesisRepository(pool)
        app.state.causal_repo = PostgresCausalStudyRepository(pool)
        app.state.decision_repo = PostgresDecisionRepository(pool)
        app.state.approval_repo = PostgresApprovalRepository(pool)
        app.state.action_ledger_repo = PostgresActionLedger(pool)
        app.state.killswitch_repo = PostgresKillSwitchRepository(pool)
        app.state.connector_repo = PostgresConnectorRepository(pool)
        app.state.connector_inbox = PostgresConnectorInbox(pool)
        app.state.audit_log = PostgresAuditLog(pool)
    else:
        # Hermetic local/test initialization using InMemoryAuthAdapter (INV-IAM-001)
        from revpilot.modules.identity.adapters.in_memory_auth_adapter import InMemoryAuthAdapter
        dev_auth = InMemoryAuthAdapter()
        dev_auth.issue_test_token(
            "token_usr_analyst_001_tnt_dev_001",
            sub="usr_analyst_001",
            tenant_id="tnt_dev_001",
            roles=frozenset(["OPERATOR", "ANALYST", "INVESTIGATOR"]),
        )
        dev_auth.issue_test_token(
            "token_usr_admin_001_tnt_dev_001",
            sub="usr_admin_001",
            tenant_id="tnt_dev_001",
            roles=frozenset(["SYSTEM_ADMIN", "ADMIN"]),
        )
        app.state.auth_adapter = dev_auth

    yield

    if pool is not None:
        logger.info("Closing database pool...")
        await pool.close()
    logger.info("RevPilot API Gateway shutting down")


def create_error_envelope(
    code: str,
    message: str,
    correlation_id: str,
    details: list[dict[str, Any]] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Format standard error response according to docs/26-api/API-STANDARDS.md §3."""
    envelope: dict[str, Any] = {
        "code": code,
        "message": message,
        "correlation_id": correlation_id,
        "details": details if details is not None else [],
    }
    return envelope


def create_app() -> FastAPI:
    """FastAPI application factory."""
    api_app = FastAPI(
        title="RevPilot AI Gateway",
        version="1.0.0-rc1",
        description="Autonomous Revenue Intelligence & Governed Decision Platform",
        lifespan=lifespan,
    )

    # Initialize default fail-closed InMemoryAuthAdapter for tests/local initialization
    from revpilot.modules.identity.adapters.in_memory_auth_adapter import InMemoryAuthAdapter
    dev_auth = InMemoryAuthAdapter()
    dev_auth.issue_test_token(
        "token_usr_analyst_001_tnt_dev_001",
        sub="usr_analyst_001",
        tenant_id="tnt_dev_001",
        roles=frozenset(["OPERATOR", "ANALYST", "INVESTIGATOR"]),
    )
    dev_auth.issue_test_token(
        "token_usr_admin_001_tnt_dev_001",
        sub="usr_admin_001",
        tenant_id="tnt_dev_001",
        roles=frozenset(["SYSTEM_ADMIN", "ADMIN"]),
    )
    api_app.state.auth_adapter = dev_auth
    api_app.state.request_count_200 = 0
    api_app.state.metrics_request_counts = {}

    # 1. Audit Middleware
    api_app.add_middleware(AuditMiddleware)

    # 2. CORS (INV-SEC-002: Disallow wildcard with credentials)
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    cors_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    allow_wildcard = "*" in cors_origins
    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_wildcard else cors_origins,
        allow_credentials=not allow_wildcard,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 3. Correlation Middleware
    @api_app.middleware("http")
    async def correlation_middleware(request: Request, call_next: Any) -> Response:
        inbound_corr = request.headers.get("X-Correlation-ID")
        correlation_id = inbound_corr if inbound_corr else f"corr_{uuid.uuid4().hex[:18]}"
        request.state.correlation_id = correlation_id
        request.state.correlation_context = CorrelationContext.create_root(correlation_id=correlation_id)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        if response.status_code == 200:
            request.app.state.request_count_200 = getattr(request.app.state, "request_count_200", 0) + 1
        counts = getattr(request.app.state, "metrics_request_counts", None)
        if counts is not None:
            c_str = str(response.status_code)
            counts[c_str] = counts.get(c_str, 0) + 1
        return response

    # Standard Exception Handlers
    @api_app.exception_handler(DomainValidationError)
    async def domain_validation_handler(request: Request, exc: DomainValidationError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        body = create_error_envelope("VALIDATION_ERROR", exc.message, corr_id, exc.details)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=body)

    @api_app.exception_handler(RequestValidationError)
    async def fastapi_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        body = create_error_envelope("VALIDATION_ERROR", "Invalid request payload schema", corr_id, exc.errors())
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=body)

    @api_app.exception_handler(AuthenticationError)
    async def authentication_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", "unknown")
        body = create_error_envelope("AUTHENTICATION_ERROR", exc.message, corr_id, exc.details)
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=body)

    @api_app.exception_handler(AuthorizationError)
    async def authorization_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
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
    async def concurrency_handler(request: Request, exc: ConcurrencyError) -> JSONResponse:
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
        body = create_error_envelope("INTERNAL_SERVER_ERROR", "An unexpected internal error occurred", corr_id, [])
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body)

    # Health & Observability Endpoints
    @api_app.get("/health/live", tags=["Operations"])
    async def liveness_probe() -> dict[str, str]:
        """Liveness check for container orchestrator (ECS/Kubernetes)."""
        return {"status": "alive"}

    @api_app.get("/health/ready", tags=["Operations"])
    async def readiness_probe(request: Request) -> JSONResponse:
        """Readiness check validating internal dependencies (PostgreSQL, Auth, Temporal)."""
        checks = {}
        is_ready = True

        # Database check
        pool = getattr(request.app.state, "db_pool", None)
        if pool is None:
            checks["database"] = "degraded"
            is_ready = False
        else:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                checks["database"] = "ok"
            except Exception as exc:
                logger.warning("Readiness: database check failed: %s", exc)
                checks["database"] = "degraded"
                is_ready = False

        # Auth adapter check
        auth_adapter = getattr(request.app.state, "auth_adapter", None)
        if auth_adapter is None:
            checks["auth"] = "degraded"
            is_ready = False
        else:
            checks["auth"] = "ok"

        # Temporal check (optional for MVP)
        temporal = getattr(request.app.state, "temporal_client", None)
        checks["temporal"] = "ok" if temporal else "not_configured"

        status_code = 200 if is_ready else 503
        payload = {"status": "ready" if is_ready else "not_ready", "checks": checks}
        return JSONResponse(status_code=status_code, content=payload)

    @api_app.get("/metrics", tags=["Operations"])
    async def prometheus_metrics(request: Request) -> Response:
        """Prometheus exposition metrics endpoint conforming to format 0.0.4."""
        is_enabled = getattr(request.app.state, "metrics_enabled", None)
        if is_enabled is None:
            is_enabled = os.getenv("METRICS_ENABLED", "").lower() in ("true", "1", "yes")

        if not is_enabled:
            return JSONResponse(
                status_code=501,
                content={"error": "Metrics instrumentation not configured. Integrate prometheus_client for real metrics."},
            )

        count_200 = getattr(request.app.state, "request_count_200", 0)
        lines = [
            "# HELP revpilot_http_requests_total Total HTTP requests received",
            "# TYPE revpilot_http_requests_total counter",
            f'revpilot_http_requests_total{{status="200"}} {count_200}',
            "# HELP revpilot_up System availability indicator",
            "# TYPE revpilot_up gauge",
            "revpilot_up 1",
            "",
        ]
        return Response(content="\n".join(lines), media_type="text/plain; version=0.0.4")

    # API v1 Router Composition
    v1_router = APIRouter(prefix="/api/v1")

    @v1_router.get("/status")
    async def api_status(request: Request) -> dict[str, Any]:
        return {
            "version": "v1.0.0-rc1",
            "status": "OPERATIONAL",
            "correlation_id": getattr(request.state, "correlation_id", "unknown"),
        }

    # Mount domain routers under /api/v1
    v1_router.include_router(analytics_router)
    v1_router.include_router(investigations_router)
    v1_router.include_router(causal_router)
    v1_router.include_router(decisions_router)
    v1_router.include_router(approvals_router)
    v1_router.include_router(admin_router)
    v1_router.include_router(connectors_router)
    v1_router.include_router(mfa_router)

    api_app.include_router(v1_router)
    api_app.include_router(scim_router)

    return api_app


app = create_app()
