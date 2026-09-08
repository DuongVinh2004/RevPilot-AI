"""
RevPilot AI — SCIM User Repository Port
Conforms to TASK-AR-008, docs/14-iam/IAM-SPEC.md, and INV-TEN-001.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from revpilot.shared.identifiers import TenantId


@runtime_checkable
class ScimUserRepositoryPort(Protocol):
    """Protocol port defining tenant-scoped SCIM user persistence operations."""

    async def create_user(self, tenant_id: TenantId, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create and persist a new SCIM user record under the specified tenant."""
        ...

    async def get_user(self, tenant_id: TenantId, user_id: str) -> dict[str, Any] | None:
        """Retrieve a user by ID within tenant boundary. Returns None if not found."""
        ...

    async def list_users(
        self,
        tenant_id: TenantId,
        start_index: int = 1,
        count: int = 100,
        filter_expr: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List users for a tenant with pagination and optional filter. Returns (users, total_count)."""
        ...

    async def update_user(
        self,
        tenant_id: TenantId,
        user_id: str,
        patch_ops: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Apply SCIM patch operations to a user within tenant boundary. Returns updated user or None."""
        ...

    async def delete_user(self, tenant_id: TenantId, user_id: str) -> bool:
        """Soft-delete user (set active=false) within tenant boundary. Returns True if found and updated."""
        ...

    async def get_user_by_external_id(self, tenant_id: TenantId, external_id: str) -> dict[str, Any] | None:
        """Lookup active user by externalId within tenant boundary."""
        ...
