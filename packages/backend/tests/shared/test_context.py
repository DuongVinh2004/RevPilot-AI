"""
Unit tests for Tenant and Principal Context Primitives (TASK-R01-003).
Validates INV-TEN-001, INV-TEN-002, INV-TEN-003, and INV-IAM-001.
"""

import pytest

from revpilot.shared.identifiers import TenantId, PrincipalId, OrganizationId
from revpilot.shared.errors import TenancyViolationError, AuthorizationError
from revpilot.shared.context import TenantContext, PrincipalContext, SecurityContext


# ==========================================
# 1. TenantContext Tests
# ==========================================

def test_tenant_context_valid():
    tid = TenantId.generate()
    oid = OrganizationId.generate()
    ctx = TenantContext(tenant_id=tid, organization_id=oid, tier="enterprise")

    assert ctx.tenant_id == tid
    assert ctx.organization_id == oid
    assert ctx.tier == "enterprise"
    assert ctx.is_active is True

    d = ctx.to_dict()
    assert d["tenant_id"] == str(tid)
    assert d["organization_id"] == str(oid)
    assert d["tier"] == "enterprise"


def test_tenant_context_inactive_rejected():
    tid = TenantId.generate()
    oid = OrganizationId.generate()
    with pytest.raises(TenancyViolationError, match="deactivated or suspended"):
        TenantContext(tenant_id=tid, organization_id=oid, is_active=False)


def test_tenant_context_type_validation():
    with pytest.raises(TypeError):
        TenantContext(tenant_id="invalid_str", organization_id=OrganizationId.generate())  # type: ignore


# ==========================================
# 2. PrincipalContext Tests
# ==========================================

def test_principal_context_valid_user():
    pid = PrincipalId.generate()
    tid = TenantId.generate()
    p = PrincipalContext(
        principal_id=pid,
        tenant_id=tid,
        roles=frozenset(["analyst", "viewer"]),
        permissions=frozenset(["investigation:read", "evidence:read"]),
    )

    assert p.principal_id == pid
    assert p.tenant_id == tid
    assert p.has_role("analyst") is True
    assert p.has_role("ADMIN") is False
    assert p.has_permission("investigation:read") is True
    assert p.has_permission("action:execute") is False

    # require_permission
    p.require_permission("investigation:read")
    with pytest.raises(AuthorizationError, match="lacks required permission"):
        p.require_permission("action:execute")


def test_principal_context_rejects_null_tenant_for_user():
    pid = PrincipalId.generate()
    with pytest.raises(TenancyViolationError, match="Non-system principal requires explicit tenant_id"):
        PrincipalContext(principal_id=pid, tenant_id=None, is_system=False)


def test_principal_context_system_principal_allowed_null_tenant():
    pid = PrincipalId.generate()
    sys_p = PrincipalContext(
        principal_id=pid,
        tenant_id=None,
        is_system=True,
        permissions=frozenset(["platform:admin"]),
    )
    assert sys_p.is_system is True
    assert sys_p.tenant_id is None
    assert sys_p.has_permission("platform:admin") is True


# ==========================================
# 3. SecurityContext Tests (INV-TEN-001)
# ==========================================

def test_security_context_valid():
    tid = TenantId.generate()
    oid = OrganizationId.generate()
    pid = PrincipalId.generate()

    tenant = TenantContext(tenant_id=tid, organization_id=oid)
    principal = PrincipalContext(principal_id=pid, tenant_id=tid)

    sec = SecurityContext.create(tenant=tenant, principal=principal)
    assert sec.tenant == tenant
    assert sec.principal == principal


def test_security_context_cross_tenant_mismatch_fails_closed():
    tid1 = TenantId.generate()
    tid2 = TenantId.generate()
    oid = OrganizationId.generate()
    pid = PrincipalId.generate()

    tenant = TenantContext(tenant_id=tid1, organization_id=oid)
    principal_foreign = PrincipalContext(principal_id=pid, tenant_id=tid2)

    with pytest.raises(TenancyViolationError, match="Cross-tenant context mismatch"):
        SecurityContext.create(tenant=tenant, principal=principal_foreign)


def test_security_context_system_principal_allowed():
    tid = TenantId.generate()
    oid = OrganizationId.generate()
    pid = PrincipalId.generate()

    tenant = TenantContext(tenant_id=tid, organization_id=oid)
    sys_principal = PrincipalContext(principal_id=pid, tenant_id=None, is_system=True)

    sec = SecurityContext.create(tenant=tenant, principal=sys_principal)
    assert sec.principal.is_system is True
