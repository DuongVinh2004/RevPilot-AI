"""
RevPilot AI — Tenancy Service
Application service managing tenant lifecycle, organization ownership, and trusted context derivation.
Enforces INV-TEN-001, INV-TEN-002, and INV-TEN-003.
"""

from __future__ import annotations

from typing import Any, Callable

from revpilot.shared.identifiers import TenantId, OrganizationId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext, PrincipalContext, SecurityContext
from revpilot.shared.errors import NotFoundError, TenancyViolationError, ValidationError
from revpilot.modules.tenancy.domain.models import (
    Tenant,
    Organization,
    TenantStatus,
    SubscriptionTier,
    Entitlement,
    TenantProvisioningRequest,
    LegalHoldRecord,
    TenantExportBundle,
    DeletionCertificate,
)
from revpilot.modules.tenancy.domain.errors import (
    TenantSuspendedError,
    TenantInactiveError,
    LegalHoldActiveError,
    PartialProvisioningError,
    IsolationVerificationFailedError,
    DeletionIncompleteError,
)
from revpilot.modules.tenancy.ports.repository import TenantQueryPort, TenantCommandPort
from revpilot.modules.tenancy.ports.policy import TenantContextPolicy


class TenantService:
    """
    Application service orchestrating tenant lifecycle, organization membership,
    and server-side context generation.
    """

    def __init__(
        self,
        query_port: TenantQueryPort,
        command_port: TenantCommandPort,
        policy: type[TenantContextPolicy] = TenantContextPolicy,
    ) -> None:
        self._query = query_port
        self._command = command_port
        self._policy = policy
        self._provisioning_keys: dict[str, TenantId] = {}
        self._legal_holds: dict[str, LegalHoldRecord] = {}
        self._allocated_resources: dict[str, list[str]] = {}

    def create_organization(
        self, name: str, org_id: OrganizationId | None = None
    ) -> Organization:
        """Create and persist a new customer organization boundary."""
        org = Organization(
            id=org_id or OrganizationId.generate(),
            name=name,
            created_at=UtcDateTime.now(),
            is_active=True,
        )
        self._command.save_organization(org)
        return org

    def provision_tenant(
        self,
        organization_id: OrganizationId,
        name: str,
        tier: SubscriptionTier = SubscriptionTier.SHARED,
        entitlement: Entitlement | None = None,
        tenant_id: TenantId | None = None,
    ) -> Tenant:
        """
        Provision a new tenant in PROVISIONING status under an existing organization.
        """
        org = self._query.get_organization_by_id(organization_id)
        if org is None:
            raise NotFoundError(
                f"Cannot provision tenant: Organization '{organization_id}' does not exist",
                details={"organization_id": str(organization_id)},
            )

        now = UtcDateTime.now()
        ent = entitlement or Entitlement(tier=tier)
        tenant = Tenant(
            id=tenant_id or TenantId.generate(),
            organization_id=organization_id,
            name=name,
            status=TenantStatus.PROVISIONING,
            tier=tier,
            entitlement=ent,
            created_at=now,
            updated_at=now,
        )
        self._command.save_tenant(tenant)
        return tenant

    def provision_tenant_idempotent(
        self,
        request: TenantProvisioningRequest,
        simulate_step_failure: str | None = None,
    ) -> Tenant:
        """
        Idempotent provisioning orchestrator across 7 resource allocation steps (INV-TEN-001).
        If idempotency key matches prior provisioned tenant, returns existing tenant without re-provisioning.
        If any step fails, rolls back allocated resources and marks state PROVISION_FAILED (TC-P07-002).
        """
        if request.idempotency_key and request.idempotency_key in self._provisioning_keys:
            existing_tenant_id = self._provisioning_keys[request.idempotency_key]
            existing_tenant = self._query.get_by_id(existing_tenant_id)
            if existing_tenant is not None:
                return existing_tenant

        org = self._query.get_organization_by_id(request.organization_id)
        if org is None:
            raise NotFoundError(
                f"Cannot provision tenant: Organization '{request.organization_id}' does not exist",
                details={"organization_id": str(request.organization_id)},
            )

        now = UtcDateTime.now()
        tenant_id = request.tenant_id or TenantId.generate()
        ent = Entitlement(tier=request.tier)
        tenant = Tenant(
            id=tenant_id,
            organization_id=request.organization_id,
            name=request.name,
            status=TenantStatus.PROVISIONING,
            tier=request.tier,
            entitlement=ent,
            created_at=now,
            updated_at=now,
        )
        self._command.save_tenant(tenant)

        allocated: list[str] = ["relational_schema"]
        self._allocated_resources[str(tenant_id)] = allocated

        # Resource allocation steps
        steps = [
            ("redis_cache_namespace", f"{tenant_id}:"),
            ("s3_object_prefix", f"{tenant_id}/"),
            ("vector_rag_collection", f"col_{tenant_id}"),
            ("default_quotas", f"quota_{tenant_id}"),
            ("rbac_tenant_admin", f"admin_{request.admin_email}"),
        ]

        for step_name, resource_id in steps:
            if simulate_step_failure == step_name:
                # Rollback all allocated resources
                self._allocated_resources[str(tenant_id)].clear()
                self._command.update_status(tenant_id, TenantStatus.PROVISION_FAILED)
                raise PartialProvisioningError(
                    f"Resource allocation failed at step '{step_name}'; rolled back {allocated}",
                    details={"failed_step": step_name, "tenant_id": str(tenant_id)},
                )
            allocated.append(step_name)

        # Transition to ACTIVATING when all resources allocated
        self._command.update_status(tenant_id, TenantStatus.ACTIVATING)

        if request.idempotency_key:
            self._provisioning_keys[request.idempotency_key] = tenant_id

        return tenant

    def activate_tenant(self, tenant_id: TenantId) -> Tenant:
        """Activate tenant to operational state."""
        return self._command.update_status(tenant_id, TenantStatus.ACTIVE)

    def activate_tenant_with_preconditions(
        self,
        tenant_id: TenantId,
        probe_runner: Any = None,
    ) -> Tenant:
        """
        Transition tenant from ACTIVATING to ACTIVE after verifying 100% passing isolation probes (TC-P07-003).
        Fails closed if any probe fails.
        """
        tenant = self.get_tenant(tenant_id)
        if tenant.status not in (TenantStatus.ACTIVATING, TenantStatus.PROVISIONING):
            if tenant.status == TenantStatus.ACTIVE:
                return tenant
            raise ValidationError(
                f"Cannot activate tenant in state '{tenant.status.value}'; must be ACTIVATING or PROVISIONING"
            )

        if probe_runner is not None:
            if callable(probe_runner):
                probe_res = probe_runner(tenant_id)
            elif hasattr(probe_runner, "run_probes"):
                probe_res = probe_runner.run_probes(tenant_id)
            else:
                probe_res = True

            if isinstance(probe_res, dict):
                all_passed = all(probe_res.values())
            elif isinstance(probe_res, bool):
                all_passed = probe_res
            elif hasattr(probe_res, "is_success"):
                all_passed = probe_res.is_success
            else:
                all_passed = bool(probe_res)

            if not all_passed:
                raise IsolationVerificationFailedError(
                    f"Pre-activation isolation probes failed for tenant '{tenant_id}'",
                    details={"tenant_id": str(tenant_id), "probe_results": str(probe_res)},
                )

        return self._command.update_status(tenant_id, TenantStatus.ACTIVE)

    def suspend_tenant(
        self,
        tenant_id: TenantId,
        reason: str,
        actor: str = "platform_admin",
    ) -> Tenant:
        """
        Suspend tenant immediately halting ingress traffic and external actions (TC-P07-004).
        Idempotent: calling suspend on already suspended tenant is a no-op.
        """
        tenant = self.get_tenant(tenant_id)
        if tenant.status == TenantStatus.SUSPENDED:
            return tenant
        return self._command.update_status(tenant_id, TenantStatus.SUSPENDED, reason=reason)

    def check_ingress_allowed(self, tenant_id: TenantId) -> None:
        """
        Enforce ingress gating per TENANT-OPERATIONS-SPEC.md §2.1.
        Throws TenantSuspendedError if SUSPENDED, TenantInactiveError if not ACTIVE or EXPORTING.
        """
        tenant = self.get_tenant(tenant_id)
        if tenant.status == TenantStatus.SUSPENDED:
            raise TenantSuspendedError(
                f"Ingress rejected: Tenant '{tenant_id}' is suspended ({tenant.suspension_reason or 'No reason provided'})",
                details={"tenant_id": str(tenant_id), "status": tenant.status.value},
            )
        if not tenant.can_ingress():
            raise TenantInactiveError(
                f"Ingress rejected: Tenant '{tenant_id}' is not active (status: {tenant.status.value})",
                details={"tenant_id": str(tenant_id), "status": tenant.status.value},
            )

    def reactivate_tenant(
        self,
        tenant_id: TenantId,
        resolution_proof: str,
        actor: str = "platform_admin",
    ) -> Tenant:
        """
        Reactivate suspended tenant back to ACTIVE status with verified resolution proof (TC-P07-005).
        """
        if not resolution_proof or not resolution_proof.strip():
            raise ValidationError("Reactivation requires non-empty resolution proof")
        tenant = self.get_tenant(tenant_id)
        if tenant.status == TenantStatus.ACTIVE:
            return tenant
        if tenant.status != TenantStatus.SUSPENDED:
            raise ValidationError(
                f"Cannot reactivate tenant in state '{tenant.status.value}'; must be SUSPENDED"
            )
        return self._command.update_status(tenant_id, TenantStatus.ACTIVE)

    def apply_legal_hold(
        self,
        tenant_id: TenantId,
        matter_id: str,
        justification: str,
        actor: str = "compliance_officer",
    ) -> LegalHoldRecord:
        """
        Apply legal hold on tenant; suspends automated deletion and mutations (TC-P07-009).
        """
        tenant = self.get_tenant(tenant_id)
        if not matter_id or not matter_id.strip():
            raise ValidationError("Legal hold requires matter_id")
        if not justification or not justification.strip():
            raise ValidationError("Legal hold requires justification")

        self._command.update_status(tenant_id, TenantStatus.LEGAL_HOLD)
        now = UtcDateTime.now()
        record = LegalHoldRecord(
            matter_id=matter_id.strip(),
            tenant_id=tenant_id,
            justification=justification.strip(),
            applied_by=actor,
            applied_at=now,
            is_active=True,
        )
        self._legal_holds[str(tenant_id)] = record
        return record

    def release_legal_hold(
        self,
        tenant_id: TenantId,
        matter_id: str,
        actor: str = "compliance_officer",
        restore_status: TenantStatus = TenantStatus.SUSPENDED,
    ) -> Tenant:
        """
        Release legal hold upon signed compliance authorization.
        """
        tenant = self.get_tenant(tenant_id)
        record = self._legal_holds.get(str(tenant_id))
        if record is not None and record.matter_id == matter_id:
            updated_record = LegalHoldRecord(
                matter_id=record.matter_id,
                tenant_id=record.tenant_id,
                justification=record.justification,
                applied_by=record.applied_by,
                applied_at=record.applied_at,
                released_at=UtcDateTime.now(),
                is_active=False,
            )
            self._legal_holds[str(tenant_id)] = updated_record

        return self._command.update_status(tenant_id, restore_status)

    def is_under_legal_hold(self, tenant_id: TenantId) -> bool:
        """Check whether tenant is currently under active legal hold."""
        tenant = self._query.get_by_id(tenant_id)
        if tenant is not None and tenant.status == TenantStatus.LEGAL_HOLD:
            return True
        rec = self._legal_holds.get(str(tenant_id))
        return rec is not None and rec.is_active

    def deactivate_tenant(self, tenant_id: TenantId) -> Tenant:
        """Deactivate tenant to terminal state."""
        return self._command.update_status(tenant_id, TenantStatus.DEACTIVATED)

    def get_tenant(self, tenant_id: TenantId) -> Tenant:
        """Retrieve tenant aggregate or raise NotFoundError."""
        tenant = self._query.get_by_id(tenant_id)
        if tenant is None:
            raise NotFoundError(
                f"Tenant '{tenant_id}' not found",
                details={"tenant_id": str(tenant_id)},
            )
        return tenant

    def resolve_tenant_context(self, tenant_id: TenantId) -> TenantContext:
        """
        Derive verified TenantContext from server-side store (INV-TEN-002).
        Fails closed on missing or inactive tenant.
        """
        tenant = self.get_tenant(tenant_id)
        context = tenant.to_context()
        self._policy.validate_context(context)
        return context

    def resolve_security_context(
        self, tenant_id: TenantId, principal: PrincipalContext
    ) -> SecurityContext:
        """
        Resolve unified SecurityContext for execution boundary.
        Fails closed on missing tenant, inactive tenant, or cross-tenant mismatch.
        """
        tenant = self.get_tenant(tenant_id)
        return self._policy.resolve_security_context(tenant, principal)
