"""
RevPilot AI — Unit Tests for Permission, Role, and PolicyAttributes (Rail 4).
Validates AC-R04-001-01 through AC-R04-001-06.
"""

from dataclasses import FrozenInstanceError
import pytest

from revpilot.modules.identity.domain.permissions import Permission, PolicyAttributes
from revpilot.modules.identity.domain.roles import Role, StandardRoles
from revpilot.shared.errors import ValidationError
from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


# ==============================================================================
# Permission Tests (AC-R04-001-01, AC-R04-001-02)
# ==============================================================================

def test_permission_creation_and_immutability():
    perm = Permission("investigation", "read")
    assert perm.resource == "investigation"
    assert perm.action == "read"
    assert str(perm) == "investigation:read"
    assert repr(perm) == "Permission('investigation', 'read')"

    # Immutability
    with pytest.raises(FrozenInstanceError):
        perm.resource = "evidence"  # type: ignore


def test_permission_case_normalization():
    perm = Permission("Investigation", "READ")
    assert perm.resource == "investigation"
    assert perm.action == "read"
    assert str(perm) == "investigation:read"


def test_permission_from_string_valid():
    perm = Permission.from_string("investigation:create")
    assert perm.resource == "investigation"
    assert perm.action == "create"

    wildcard_perm = Permission.from_string("*:*")
    assert wildcard_perm.resource == "*"
    assert wildcard_perm.action == "*"

    action_wildcard = Permission.from_string("evidence:*")
    assert action_wildcard.resource == "evidence"
    assert action_wildcard.action == "*"


@pytest.mark.parametrize(
    "invalid_input",
    [
        "",
        "   ",
        "investigation",
        "investigation:read:extra",
        ":read",
        "investigation:",
        ":",
        "   :read",
        "investigation:   ",
        "inv estigation:read",
        "investigation:re ad",
        "inv@est:read",
    ],
)
def test_permission_from_string_invalid(invalid_input: str):
    with pytest.raises(ValidationError):
        Permission.from_string(invalid_input)


def test_permission_from_string_non_string():
    with pytest.raises(ValidationError):
        Permission.from_string(123)  # type: ignore


def test_permission_constructor_validation():
    with pytest.raises(ValidationError):
        Permission("", "read")

    with pytest.raises(ValidationError):
        Permission("investigation", "")

    with pytest.raises(ValidationError):
        Permission("inv:est", "read")

    with pytest.raises(TypeError):
        Permission(123, "read")  # type: ignore

    with pytest.raises(TypeError):
        Permission("investigation", None)  # type: ignore


def test_permission_exact_matching():
    p1 = Permission("investigation", "read")
    p2 = Permission("investigation", "read")
    p3 = Permission("investigation", "write")
    p4 = Permission("evidence", "read")

    assert p1.matches(p2) is True
    assert p1.matches(p3) is False
    assert p1.matches(p4) is False
    assert p1.matches("investigation:read") is False  # type: ignore
    assert p1.matches(None) is False  # type: ignore


def test_permission_wildcard_matching():
    full_wildcard = Permission("*", "*")
    req1 = Permission("investigation", "read")
    req2 = Permission("evidence", "attach")
    req3 = Permission("system", "admin")

    assert full_wildcard.matches(req1) is True
    assert full_wildcard.matches(req2) is True
    assert full_wildcard.matches(req3) is True

    action_wildcard = Permission("investigation", "*")
    assert action_wildcard.matches(Permission("investigation", "read")) is True
    assert action_wildcard.matches(Permission("investigation", "delete")) is True
    assert action_wildcard.matches(Permission("evidence", "read")) is False

    resource_wildcard = Permission("*", "read")
    assert resource_wildcard.matches(Permission("investigation", "read")) is True
    assert resource_wildcard.matches(Permission("evidence", "read")) is True
    assert resource_wildcard.matches(Permission("investigation", "write")) is False


# ==============================================================================
# Role Tests (AC-R04-001-03)
# ==============================================================================

def test_role_creation_and_immutability():
    perms = frozenset({
        Permission("investigation", "read"),
        Permission("evidence", "read"),
    })
    role = Role(name="test_role", permissions=perms, description="A test role")
    assert role.name == "test_role"
    assert role.permissions == perms
    assert role.description == "A test role"

    with pytest.raises(FrozenInstanceError):
        role.name = "new_name"  # type: ignore


def test_role_validation():
    perms = frozenset({Permission("investigation", "read")})

    with pytest.raises(ValidationError):
        Role(name="", permissions=perms)

    with pytest.raises(ValidationError):
        Role(name="Invalid-Role-Name", permissions=perms)

    with pytest.raises(ValidationError):
        Role(name="invalid role", permissions=perms)

    with pytest.raises(TypeError):
        Role(name=123, permissions=perms)  # type: ignore

    with pytest.raises(TypeError):
        Role(name="valid_role", permissions=frozenset({"not_a_permission"}))  # type: ignore


def test_role_has_permission():
    role = Role(
        name="reader",
        permissions=frozenset({
            Permission("investigation", "read"),
            Permission("evidence", "*"),
        }),
    )

    assert role.has_permission(Permission("investigation", "read")) is True
    assert role.has_permission("investigation:read") is True
    assert role.has_permission(Permission("investigation", "write")) is False
    assert role.has_permission("investigation:write") is False
    assert role.has_permission(Permission("evidence", "read")) is True
    assert role.has_permission(Permission("evidence", "attach")) is True
    assert role.has_permission("evidence:delete") is True
    assert role.has_permission("invalid_perm_format") is False
    assert role.has_permission(None) is False  # type: ignore


def test_standard_roles_canonical_definitions():
    # AC-R04-001-03: defines all 6 canonical roles
    all_roles = StandardRoles.all_roles()
    assert len(all_roles) == 6

    platform_admin = StandardRoles.get_role("platform_admin")
    assert platform_admin.name == "platform_admin"
    assert platform_admin.has_permission(Permission("any", "thing")) is True
    assert platform_admin.has_permission("anything:*") is True

    tenant_admin = StandardRoles.get_role("tenant_admin")
    assert tenant_admin.name == "tenant_admin"
    assert tenant_admin.has_permission("tenant:manage") is True
    assert tenant_admin.has_permission("user:manage") is True
    assert tenant_admin.has_permission("investigation:create") is True
    assert tenant_admin.has_permission("investigation:delete") is True
    assert tenant_admin.has_permission("evidence:attach") is True
    assert tenant_admin.has_permission("audit:read") is True
    assert tenant_admin.has_permission("policy:read") is True
    assert tenant_admin.has_permission("policy:write") is False

    operator = StandardRoles.get_role("operator")
    assert operator.name == "operator"
    assert operator.has_permission("investigation:create") is True
    assert operator.has_permission("investigation:read") is True
    assert operator.has_permission("evidence:read") is True
    assert operator.has_permission("tool:invoke") is True
    assert operator.has_permission("approval:request") is True
    assert operator.has_permission("approval:grant") is False

    analyst = StandardRoles.get_role("analyst")
    assert analyst.name == "analyst"
    assert analyst.has_permission("investigation:read") is True
    assert analyst.has_permission("evidence:read") is True
    assert analyst.has_permission("analytics:read") is True
    assert analyst.has_permission("audit:read") is True
    assert analyst.has_permission("tool:invoke") is False

    auditor = StandardRoles.get_role("auditor")
    assert auditor.name == "auditor"
    assert auditor.has_permission("audit:read") is True
    assert auditor.has_permission("compliance:read") is True
    assert auditor.has_permission("investigation:read") is True
    assert auditor.has_permission("evidence:read") is True
    assert auditor.has_permission("investigation:create") is False

    agent_delegate = StandardRoles.get_role("agent_delegate")
    assert agent_delegate.name == "agent_delegate"
    assert agent_delegate.has_permission("investigation:read") is True
    assert agent_delegate.has_permission("evidence:read") is True
    assert agent_delegate.has_permission("tool:invoke") is True
    assert agent_delegate.has_permission("approval:request") is False
    assert agent_delegate.has_permission("approval:grant") is False


def test_standard_roles_case_insensitivity_and_unknown():
    role = StandardRoles.get_role("TENANT_ADMIN")
    assert role == StandardRoles.TENANT_ADMIN

    with pytest.raises(ValidationError):
        StandardRoles.get_role("super_user")

    with pytest.raises(ValidationError):
        StandardRoles.get_role("")

    with pytest.raises(ValidationError):
        StandardRoles.get_role(123)  # type: ignore


# ==============================================================================
# PolicyAttributes Tests (AC-R04-001-04)
# ==============================================================================

def test_policy_attributes_creation_and_immutability():
    tenant_id = TenantId("tnt_01j9b4c6e8f01a2b3c4d5e6f7a")
    now = UtcDateTime.now()
    attrs = PolicyAttributes(
        tenant_id=tenant_id,
        resource_id="res_123",
        resource_tenant_id=tenant_id,
        task_id="tsk_456",
        as_of=now,
    )

    assert attrs.tenant_id == tenant_id
    assert attrs.resource_id == "res_123"
    assert attrs.resource_tenant_id == tenant_id
    assert attrs.task_id == "tsk_456"
    assert attrs.as_of == now

    with pytest.raises(FrozenInstanceError):
        attrs.task_id = "other"  # type: ignore


def test_policy_attributes_minimal_and_string_coercion():
    tenant_id_str = "tnt_01j9b4c6e8f01a2b3c4d5e6f7a"
    attrs = PolicyAttributes(tenant_id=tenant_id_str)  # type: ignore
    assert isinstance(attrs.tenant_id, TenantId)
    assert str(attrs.tenant_id) == tenant_id_str
    assert attrs.resource_id is None
    assert attrs.resource_tenant_id is None
    assert attrs.task_id is None
    assert attrs.as_of is None


def test_policy_attributes_validation():
    with pytest.raises(TypeError):
        PolicyAttributes(tenant_id=123)  # type: ignore

    tenant_id = TenantId("tnt_01j9b4c6e8f01a2b3c4d5e6f7a")

    with pytest.raises(ValidationError):
        PolicyAttributes(tenant_id=tenant_id, resource_id="")

    with pytest.raises(ValidationError):
        PolicyAttributes(tenant_id=tenant_id, task_id="   ")

    with pytest.raises(TypeError):
        PolicyAttributes(tenant_id=tenant_id, as_of="not_a_time")  # type: ignore
