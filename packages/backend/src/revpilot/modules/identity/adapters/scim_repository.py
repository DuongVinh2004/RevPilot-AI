"""
RevPilot AI — In-Memory SCIM User Repository Adapter
Conforms to TASK-AR-008, docs/14-iam/IAM-SPEC.md, RFC 7644, and INV-TEN-001.
"""

from __future__ import annotations

import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from revpilot.modules.identity.ports.scim_repository import ScimUserRepositoryPort
from revpilot.shared.identifiers import TenantId


class InMemoryScimUserRepository(ScimUserRepositoryPort):
    """Test-safe, in-memory tenant-isolated implementation of ScimUserRepositoryPort."""

    def __init__(self) -> None:
        # storage format: dict[tenant_id_str, dict[user_id, dict]]
        self._storage: dict[str, dict[str, dict[str, Any]]] = {}

    def _get_tenant_store(self, tenant_id: TenantId | str) -> dict[str, dict[str, Any]]:
        t_key = str(tenant_id)
        if t_key not in self._storage:
            self._storage[t_key] = {}
        return self._storage[t_key]

    async def create_user(self, tenant_id: TenantId, user_data: dict[str, Any]) -> dict[str, Any]:
        store = self._get_tenant_store(tenant_id)
        user_id = user_data.get("id") or f"usr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        record = deepcopy(user_data)
        record["id"] = user_id
        record["schemas"] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
        if "active" not in record:
            record["active"] = True

        record["meta"] = {
            "resourceType": "User",
            "created": now,
            "lastModified": now,
            "location": f"/scim/v2/{tenant_id}/Users/{user_id}",
            "version": 'W/"1"',
        }

        store[user_id] = record
        return deepcopy(record)

    async def get_user(self, tenant_id: TenantId, user_id: str) -> dict[str, Any] | None:
        store = self._get_tenant_store(tenant_id)
        record = store.get(user_id)
        return deepcopy(record) if record else None

    async def get_user_by_external_id(self, tenant_id: TenantId, external_id: str) -> dict[str, Any] | None:
        store = self._get_tenant_store(tenant_id)
        for user in store.values():
            if not user.get("active", True):
                continue
            if user.get("externalId") == external_id:
                return deepcopy(user)
            if user.get("userName") == external_id and not user.get("externalId"):
                return deepcopy(user)
        return None

    async def list_users(
        self,
        tenant_id: TenantId,
        start_index: int = 1,
        count: int = 100,
        filter_expr: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        store = self._get_tenant_store(tenant_id)
        all_users = list(store.values())

        filtered: list[dict[str, Any]] = []
        if filter_expr:
            # Match e.g. userName eq "foo@example.com" or userName eq foo@example.com
            m = re.match(r'userName\s+eq\s+["\']?([^"\'\s]+)["\']?', filter_expr.strip(), re.IGNORECASE)
            if m:
                target_username = m.group(1).lower()
                for u in all_users:
                    if u.get("userName", "").lower() == target_username:
                        filtered.append(u)
            else:
                filtered = all_users
        else:
            filtered = all_users

        total_results = len(filtered)
        # SCIM startIndex is 1-based
        zero_index = max(0, start_index - 1)
        sliced = filtered[zero_index : zero_index + max(0, count)]
        return deepcopy(sliced), total_results

    async def update_user(
        self,
        tenant_id: TenantId,
        user_id: str,
        patch_ops: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        store = self._get_tenant_store(tenant_id)
        record = store.get(user_id)
        if not record:
            return None

        now = datetime.now(timezone.utc).isoformat()
        for op in patch_ops:
            operation = op.get("op", "").lower()
            path = op.get("path")
            value = op.get("value")

            if operation in ("replace", "add"):
                if path:
                    if path.lower() == "active":
                        record["active"] = bool(value)
                    elif path.lower() == "displayname":
                        record["displayName"] = str(value)
                    elif path.lower() == "username":
                        record["userName"] = str(value)
                elif isinstance(value, dict):
                    for k, v in value.items():
                        if k.lower() == "active":
                            record["active"] = bool(v)
                        else:
                            record[k] = v

        record["meta"]["lastModified"] = now
        return deepcopy(record)

    async def delete_user(self, tenant_id: TenantId, user_id: str) -> bool:
        store = self._get_tenant_store(tenant_id)
        record = store.get(user_id)
        if not record:
            return False
        # Soft-delete: active = False per RFC 7644 & enterprise spec
        record["active"] = False
        record["meta"]["lastModified"] = datetime.now(timezone.utc).isoformat()
        return True
