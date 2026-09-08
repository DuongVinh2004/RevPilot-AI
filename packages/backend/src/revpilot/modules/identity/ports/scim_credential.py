"""
RevPilot AI — SCIM Credential Repository Port
Conforms to TASK-AR-007, docs/14-iam/IAM-SPEC.md, and INV-IAM-001.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from revpilot.modules.identity.domain.scim_credential import ScimCredential


@runtime_checkable
class ScimCredentialPort(Protocol):
    """Protocol port for cryptographically verified SCIM credential lookups."""

    async def verify(self, token_hash: str) -> ScimCredential | None:
        """Look up credential by SHA-256 hash of raw token. Returns None if not found or inactive."""
        ...
