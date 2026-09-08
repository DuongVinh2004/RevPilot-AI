"""
RevPilot AI — SCIM 2.0 User & Group Provisioning Service
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §4
Conforms to INV-IAM-001, INV-TEN-002, and NFR-SEC-001.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import secrets
import time
from typing import Any, Callable

from revpilot.shared.identifiers import TenantId, PrincipalId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError


class ScimError(DomainError):
    """Base exception for SCIM operations."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)


class ScimConflictError(ScimError):
    """Duplicate user or email conflict (409 Conflict)."""

    def __init__(self, message: str = "User already exists", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="SCIM_CONFLICT", message=message, details=details)


class ScimUserNotFoundError(ScimError):
    """Target user not found for deprovisioning or update (404)."""

    def __init__(self, message: str = "SCIM user not found", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="SCIM_USER_NOT_FOUND", message=message, details=details)


@dataclass
class ScimUserRecord:
    """Canonical SCIM 2.0 user aggregate representation."""
    id: str
    userName: str
    email: str
    tenant_id: TenantId
    active: bool = True
    roles: set[str] = field(default_factory=set)
    created_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    updated_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    version: int = 1


@dataclass
class ScimGroupRecord:
    """Canonical SCIM 2.0 group representation."""
    id: str
    displayName: str
    tenant_id: TenantId
    members: list[str] = field(default_factory=list)
    version: int = 1


class ScimProvisioningService:
    """
    Authoritative service executing SCIM 2.0 REST provisioning and deprovisioning operations.
    Enforces tenant-partitioned storage and rapid session revocation (< 1000ms) upon offboarding (TC-P07-015).
    """

    def __init__(
        self,
        session_revoker: Callable[[TenantId, str], None] | None = None,
        tenant_service: Any = None,
    ) -> None:
        self.session_revoker = session_revoker
        self.tenant_service = tenant_service
        # tenant_id -> user_id -> ScimUserRecord
        self._users: dict[str, dict[str, ScimUserRecord]] = {}
        # tenant_id -> group_id -> ScimGroupRecord
        self._groups: dict[str, dict[str, ScimGroupRecord]] = {}
        # Set of deactivated (tenant_id, user_id)
        self._revoked_users: set[str] = set()
        self.audit_events: list[dict[str, Any]] = []

    def create_user(
        self,
        tenant_id: TenantId,
        user_payload: dict[str, Any],
    ) -> ScimUserRecord:
        """
        Provision new user via SCIM 2.0.
        Fails closed with 409 SCIM_CONFLICT on duplicate userName or primary email.
        """
        tenant_str = str(tenant_id)
        tenant_store = self._users.setdefault(tenant_str, {})

        raw_user_name = user_payload.get("userName", "").strip().lower()
        if not raw_user_name:
            raise ScimError(code="VALIDATION_ERROR", message="SCIM userName cannot be empty")

        emails = user_payload.get("emails", [])
        if emails and isinstance(emails, list):
            primary_email = emails[0].get("value", "").strip().lower()
        else:
            primary_email = user_payload.get("email", raw_user_name).strip().lower()

        # Check duplicate username or email within tenant boundary
        for existing in tenant_store.values():
            if existing.userName.lower() == raw_user_name:
                raise ScimConflictError(
                    f"User with userName '{raw_user_name}' already exists for tenant",
                    details={"userName": raw_user_name, "tenant_id": tenant_str},
                )
            if existing.email.lower() == primary_email:
                raise ScimConflictError(
                    f"User with email '{primary_email}' already exists for tenant",
                    details={"email": primary_email, "tenant_id": tenant_str},
                )

        custom_id = user_payload.get("id")
        user_id = custom_id if custom_id and custom_id.startswith("usr_") else f"usr_scim_{secrets.token_hex(8)}"

        now = UtcDateTime.now()
        record = ScimUserRecord(
            id=user_id,
            userName=raw_user_name,
            email=primary_email,
            tenant_id=tenant_id,
            active=user_payload.get("active", True),
            roles=set(user_payload.get("roles", ["operator"])),
            created_at=now,
            updated_at=now,
            version=1,
        )

        tenant_store[user_id] = record
        self.audit_events.append({
            "event": "identity.scim.user_provisioned",
            "tenant_id": tenant_str,
            "user_id": user_id,
            "email": primary_email,
            "roles": list(record.roles),
        })

        return record

    def update_user(
        self,
        tenant_id: TenantId,
        user_id: str,
        patch_operations: list[dict[str, Any]],
    ) -> ScimUserRecord:
        """
        Execute partial SCIM update (PATCH).
        If 'active' is set to False, immediately triggers deprovisioning flow.
        """
        tenant_str = str(tenant_id)
        tenant_store = self._users.get(tenant_str, {})
        user = tenant_store.get(user_id)
        if user is None:
            raise ScimUserNotFoundError(
                f"Cannot update: SCIM user '{user_id}' not found in tenant",
                details={"user_id": user_id, "tenant_id": tenant_str},
            )

        for op in patch_operations:
            path = op.get("path", "").lower()
            val = op.get("value")

            if path == "active" or (isinstance(val, dict) and "active" in val):
                active_flag = val if path == "active" else val["active"]
                if active_flag is False:
                    self.deprovision_user(tenant_id, user_id)
                    user = tenant_store[user_id]
            elif path == "roles" and isinstance(val, list):
                user.roles = set(val)

        user.version += 1
        user.updated_at = UtcDateTime.now()
        return user

    def deprovision_user(
        self,
        tenant_id: TenantId,
        user_id: str,
    ) -> None:
        """
        Rapid user deprovisioning protocol (INV-IAM-001, TC-P07-015).
        Transitions user to inactive and immediately revokes all active sessions and approval authorities (< 1000ms).
        """
        start_time = time.perf_counter()
        tenant_str = str(tenant_id)
        tenant_store = self._users.get(tenant_str, {})
        user = tenant_store.get(user_id)
        if user is None:
            raise ScimUserNotFoundError(
                f"Cannot deprovision: SCIM user '{user_id}' not found in tenant",
                details={"user_id": user_id, "tenant_id": tenant_str},
            )

        # 1. Deactivate User
        user.active = False
        user.version += 1
        user.updated_at = UtcDateTime.now()

        # 2. Record in Revocation Store
        revocation_key = f"{tenant_str}:{user_id}"
        self._revoked_users.add(revocation_key)

        # 3. Terminate Active Sessions
        if self.session_revoker is not None:
            self.session_revoker(tenant_id, user_id)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        self.audit_events.append({
            "event": "identity.scim.user_deactivated",
            "tenant_id": tenant_str,
            "user_id": user_id,
            "deprovision_duration_ms": elapsed_ms,
        })

    def is_user_active(self, tenant_id: TenantId, user_id: str) -> bool:
        """Check if user is active and has not been deprovisioned."""
        revocation_key = f"{tenant_id}:{user_id}"
        if revocation_key in self._revoked_users:
            return False
        tenant_store = self._users.get(str(tenant_id), {})
        user = tenant_store.get(user_id)
        return user is not None and user.active

    def sync_group_members(
        self,
        tenant_id: TenantId,
        group_id: str,
        member_ids: list[str],
        role_binding: str | None = None,
    ) -> ScimGroupRecord:
        """
        Sync SCIM group membership and synchronize assigned role to members.
        """
        tenant_str = str(tenant_id)
        group_store = self._groups.setdefault(tenant_str, {})
        group = group_store.get(group_id)

        if group is None:
            group = ScimGroupRecord(
                id=group_id,
                displayName=group_id,
                tenant_id=tenant_id,
                members=member_ids,
            )
            group_store[group_id] = group
        else:
            group.members = member_ids
            group.version += 1

        # Synchronize roles on user records
        if role_binding:
            user_store = self._users.get(tenant_str, {})
            for uid in member_ids:
                if uid in user_store:
                    user_store[uid].roles.add(role_binding)

        self.audit_events.append({
            "event": "identity.scim.group_updated",
            "tenant_id": tenant_str,
            "group_id": group_id,
            "member_count": len(member_ids),
        })
        return group
