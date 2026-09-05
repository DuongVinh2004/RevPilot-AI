"""
RevPilot AI — Connectors & Webhook Ingestion Router (Phase 07)
Conforms to docs/26-api/API-STANDARDS.md §10 and docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, status, Header
from pydantic import BaseModel, Field

from apps.api.middleware.authentication import get_current_tenant
from apps.api.middleware.authorization import require_roles
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import ValidationError

router = APIRouter(prefix="/connectors", tags=["Connectors & Webhooks"])


class ConnectorCreateRequest(BaseModel):
    provider: str
    sync_mode: str = "BATCH_PULL"
    auth_method: str = "api_key_vault"
    secret_ref: str
    scopes: list[str] = Field(default_factory=list)


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_connector(
    payload: ConnectorCreateRequest,
    request: Request,
    tenant: TenantContext = Depends(get_current_tenant),
    principal=Depends(require_roles("TENANT_ADMIN", "SYSTEM_ADMIN")),
) -> dict[str, Any]:
    """Register SaaS connector instance."""
    conn_id = f"conn_{payload.provider}_{uuid.uuid4().hex[:8]}"
    repo = getattr(request.app.state, "connector_repo", None)

    if repo is not None:
        await repo.create_connector(
            tenant,
            {
                "id": conn_id,
                "provider": payload.provider,
                "sync_mode": payload.sync_mode,
                "auth_method": payload.auth_method,
                "secret_ref": payload.secret_ref,
            },
        )

    return {
        "connector_id": conn_id,
        "provider": payload.provider,
        "status": "CONFIGURED",
        "sync_mode": payload.sync_mode,
    }


@router.post("/{connector_id}/webhooks", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(
    connector_id: str,
    payload: dict[str, Any],
    request: Request,
    x_signature: str | None = Header(None, alias="X-Signature-SHA256"),
    x_event_id: str | None = Header(None, alias="X-Event-ID"),
    tenant: TenantContext = Depends(get_current_tenant),
) -> dict[str, Any]:
    """Ingest inbound webhook into transactional anti-replay inbox."""
    event_id = x_event_id or f"evt_{uuid.uuid4().hex[:12]}"
    digest = hashlib.sha256(str(payload).encode()).hexdigest()

    inbox = getattr(request.app.state, "connector_inbox", None)
    is_duplicate = False
    inbox_id = f"inbox_{event_id}"

    if inbox is not None:
        inbox_id, is_duplicate = await inbox.ingest_webhook_event(
            tenant, connector_id, event_id, payload, digest
        )

    return {
        "status": "ACCEPTED",
        "inbox_id": inbox_id,
        "is_duplicate": is_duplicate,
    }
