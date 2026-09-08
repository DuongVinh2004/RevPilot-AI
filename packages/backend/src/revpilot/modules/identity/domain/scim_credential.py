"""
RevPilot AI — SCIM Credential Domain Model
Conforms to TASK-AR-007, docs/14-iam/IAM-SPEC.md, and INV-IAM-001.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from revpilot.shared.identifiers import TenantId


@dataclass(frozen=True, slots=True)
class ScimCredential:
    """Immutable domain entity representing an enterprise SCIM provisioning credential."""
    credential_id: str
    tenant_id: TenantId
    scopes: frozenset[str]
    expires_at: datetime
    created_at: datetime
    rotated_from: str | None
    is_active: bool
