"""
RevPilot AI — In-Memory SCIM Credential Adapter (Rail 16)
Conforms to TASK-AR-007, docs/14-iam/IAM-SPEC.md, and INV-IAM-001.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from revpilot.shared.identifiers import TenantId
from revpilot.modules.identity.domain.scim_credential import ScimCredential
from revpilot.modules.identity.ports.scim_credential import ScimCredentialPort


class InMemoryScimCredentialAdapter(ScimCredentialPort):
    """Test-safe, in-memory implementation of ScimCredentialPort."""

    def __init__(self) -> None:
        self._credentials: dict[str, ScimCredential] = {}

    def register_credential(
        self,
        raw_token: str,
        tenant_id: str | TenantId,
        credential_id: str = "scim_cred_001",
        scopes: frozenset[str] = frozenset(["scim:read", "scim:write"]),
        expires_at: datetime | None = None,
        is_active: bool = True,
        rotated_from: str | None = None,
    ) -> ScimCredential:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        t_id = TenantId(str(tenant_id))
        exp = expires_at or datetime(2099, 1, 1, tzinfo=timezone.utc)
        cred = ScimCredential(
            credential_id=credential_id,
            tenant_id=t_id,
            scopes=scopes,
            expires_at=exp,
            created_at=datetime.now(timezone.utc),
            rotated_from=rotated_from,
            is_active=is_active,
        )
        self._credentials[token_hash] = cred
        return cred

    async def verify(self, token_hash: str) -> ScimCredential | None:
        return self._credentials.get(token_hash)
