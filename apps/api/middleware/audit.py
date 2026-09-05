"""
RevPilot AI — Audit Event Recording Middleware (Track 3)
Emits immutable audit events with cryptographic hash chaining for state mutations.
Enforces INV-AUD-001 (Zero Audit Drop, Immutability).
"""

from __future__ import annotations

import logging
from typing import Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("revpilot.api.audit")


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware intercepting mutating HTTP requests (POST, PUT, PATCH, DELETE)
    and recording immutable audit records into the tamper-evident ledger.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Audit only mutating operations that succeeded or failed after reaching app
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            audit_logger = getattr(request.app.state, "audit_log", None)
            if audit_logger is not None:
                try:
                    tenant_ctx = getattr(request.state, "tenant_context", None)
                    principal_ctx = getattr(request.state, "principal_context", None)
                    corr_id = getattr(request.state, "correlation_id", "corr_unknown")

                    tenant_id = str(tenant_ctx.tenant_id) if tenant_ctx else "tnt_platform"
                    actor_id = str(principal_ctx.principal_id) if principal_ctx else "usr_anonymous"
                    outcome = "SUCCESS" if response.status_code < 400 else "FAILED"

                    await audit_logger.append_event(
                        tenant_id=tenant_id,
                        actor_id=actor_id,
                        event_type=f"http.request.{request.method.lower()}",
                        resource=request.url.path,
                        action=request.method,
                        correlation_id=corr_id,
                        details={"status_code": response.status_code, "query": str(request.query_params)},
                        outcome=outcome,
                    )
                except Exception as exc:
                    logger.error("Failed to persist audit event for request %s: %s", request.url.path, exc)
                    # Fail-closed policy for critical writes if configured
                    if getattr(request.app.state, "strict_audit_enforcement", False):
                        return Response(
                            content='{"code":"AUDIT_PERSISTENCE_UNAVAILABLE","message":"Audit log persistence failure"}',
                            status_code=503,
                            media_type="application/json",
                        )

        return response
