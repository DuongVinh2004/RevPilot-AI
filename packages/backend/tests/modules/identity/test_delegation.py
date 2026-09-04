"""
RevPilot AI — Unit Tests for DelegationToken, Issuance, Expiry, and Revocation (Rail 4).
Validates AC-R04-002-01 through AC-R04-002-07.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from datetime import timedelta
import pytest

from revpilot.modules.identity.domain.delegation import (
    DelegationRevocationRegistry,
    DelegationToken,
    issue_delegation,
)
from revpilot.modules.identity.domain.models import Principal, PrincipalType
from revpilot.modules.identity.domain.permissions import Permission
from revpilot.shared.errors import (
    AuthorizationError,
    TenancyViolationError,
    ValidationError,
)
from revpilot.shared.identifiers import PrincipalId, TenantId
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_01j9b4c6e8f01a2b3c4d5e6f7a")


@pytest.fixture
def other_tenant() -> TenantId:
    return TenantId("tnt_01j9b4c6e8f01a2b3c4d5e6f7b")


@pytest.fixture
def human_operator(sample_tenant: TenantId) -> Principal:
    return Principal(
        id=PrincipalId("usr_01j9b4c6e8f01a2b3c4d5e6f88"),
        type=PrincipalType.USER,
        tenant_id=sample_tenant,
        roles=frozenset({"operator"}),
        permissions=frozenset({
            "investigation:create",
            "investigation:read",
            "evidence:read",
            "tool:invoke",
            "approval:request",
        }),
    )


@pytest.fixture
def agent_principal(sample_tenant: TenantId) -> Principal:
    return Principal(
        id=PrincipalId("usr_01j9b4c6e8f01a2b3c4d5e6f99"),
        type=PrincipalType.AGENT,
        tenant_id=sample_tenant,
        roles=frozenset({"agent_delegate"}),
        permissions=frozenset({
            "investigation:read",
            "evidence:read",
            "tool:invoke",
        }),
    )


# ==============================================================================
# DelegationToken Unit Tests (AC-R04-002-04, AC-R04-002-07)
# ==============================================================================

def test_delegation_token_immutability(sample_tenant: TenantId):
    now = UtcDateTime.now()
    token = DelegationToken(
        delegation_id="del_1234567890abcdef",
        delegator_id=PrincipalId("usr_01j9b4c6e8f01a2b3c4d5e6f88"),
        tenant_id=sample_tenant,
        task_id="tsk_inv_001",
        allowed_capabilities=frozenset({Permission("investigation", "read")}),
        target_resources=frozenset({"/tenant/a"}),
        issued_at=now,
        expires_at=UtcDateTime(now.value + timedelta(hours=1)),
    )

    with pytest.raises(FrozenInstanceError):
        token.task_id = "tsk_inv_002"  # type: ignore


def test_delegation_token_is_expired(sample_tenant: TenantId):
    # AC-R04-002-04: is_expired correctly evaluates expiration
    now = UtcDateTime.now()
    issued_at = UtcDateTime(now.value - timedelta(hours=2))
    expires_at = UtcDateTime(now.value - timedelta(hours=1))

    expired_token = DelegationToken(
        delegation_id="del_expired12345678",
        delegator_id=PrincipalId("usr_01j9b4c6e8f01a2b3c4d5e6f88"),
        tenant_id=sample_tenant,
        task_id="tsk_001",
        allowed_capabilities=frozenset({Permission("evidence", "read")}),
        target_resources=frozenset({"/evidence"}),
        issued_at=issued_at,
        expires_at=expires_at,
    )

    # Past expiration
    assert expired_token.is_expired(now) is True
    # At exact expiration
    assert expired_token.is_expired(expires_at) is True
    # Before expiration
    assert expired_token.is_expired(issued_at) is False


def test_delegation_token_allows_capability(sample_tenant: TenantId):
    now = UtcDateTime.now()
    token = DelegationToken(
        delegation_id="del_capcheck1234567",
        delegator_id=PrincipalId("usr_01j9b4c6e8f01a2b3c4d5e6f88"),
        tenant_id=sample_tenant,
        task_id="tsk_001",
        allowed_capabilities=frozenset({
            Permission("investigation", "read"),
            Permission("evidence", "*"),
        }),
        target_resources=frozenset({"/inv/1"}),
        issued_at=now,
        expires_at=UtcDateTime(now.value + timedelta(hours=1)),
    )

    assert token.allows_capability(Permission("investigation", "read")) is True
    assert token.allows_capability("investigation:read") is True
    assert token.allows_capability(Permission("investigation", "create")) is False
    assert token.allows_capability("evidence:read") is True
    assert token.allows_capability("evidence:attach") is True
    assert token.allows_capability("tool:invoke") is False
    assert token.allows_capability("invalid_string") is False


def test_delegation_token_allows_target_safe_segment_boundary(sample_tenant: TenantId):
    now = UtcDateTime.now()
    token = DelegationToken(
        delegation_id="del_targetcheck1234",
        delegator_id=PrincipalId("usr_01j9b4c6e8f01a2b3c4d5e6f88"),
        tenant_id=sample_tenant,
        task_id="tsk_001",
        allowed_capabilities=frozenset({Permission("investigation", "read")}),
        target_resources=frozenset({
            "/tenant/a",
            "/tenant/b/*",
            "doc_exact_123",
        }),
        issued_at=now,
        expires_at=UtcDateTime(now.value + timedelta(hours=1)),
    )

    # Exact matches
    assert token.allows_target("/tenant/a") is True
    assert token.allows_target("doc_exact_123") is True

    # Safe segment-boundary prefix matches for /tenant/a
    assert token.allows_target("/tenant/a/subresource") is True
    assert token.allows_target("/tenant/a/doc/456") is True
    assert token.allows_target("/tenant/a:sub") is True

    # CRITICAL: Path traversal / unsafe prefix must NOT match
    assert token.allows_target("/tenant/abc") is False
    assert token.allows_target("/tenant/a_other") is False

    # Wildcard suffix /* for /tenant/b/*
    assert token.allows_target("/tenant/b/file1") is True
    assert token.allows_target("/tenant/b/folder/sub") is True
    assert token.allows_target("/tenant/bc") is False

    # Non-matching resources
    assert token.allows_target("doc_exact_1234") is False
    assert token.allows_target("/other/path") is False
    assert token.allows_target("") is False


# ==============================================================================
# issue_delegation Tests (AC-R04-002-01, AC-R04-002-02, AC-R04-002-03)
# ==============================================================================

def test_issue_delegation_duration_bounds(
    human_operator: Principal, sample_tenant: TenantId
):
    # AC-R04-002-01: Duration must be between 60 and 86400 seconds
    caps = {Permission("investigation", "read")}
    targets = {"/inv/1"}

    # Valid duration
    t1 = issue_delegation(human_operator, sample_tenant, "tsk_1", caps, targets, duration_seconds=60)
    assert (t1.expires_at.value - t1.issued_at.value).total_seconds() == 60

    t2 = issue_delegation(human_operator, sample_tenant, "tsk_1", caps, targets, duration_seconds=86400)
    assert (t2.expires_at.value - t2.issued_at.value).total_seconds() == 86400

    # Below minimum
    with pytest.raises(ValidationError):
        issue_delegation(human_operator, sample_tenant, "tsk_1", caps, targets, duration_seconds=59)

    # Above maximum (24 hours + 1 second)
    with pytest.raises(ValidationError):
        issue_delegation(human_operator, sample_tenant, "tsk_1", caps, targets, duration_seconds=86401)

    # Invalid type
    with pytest.raises(ValidationError):
        issue_delegation(human_operator, sample_tenant, "tsk_1", caps, targets, duration_seconds="3600")  # type: ignore


def test_issue_delegation_prohibits_approval_authority(
    human_operator: Principal, sample_tenant: TenantId
):
    # AC-R04-002-02: Enforces INV-ACT-003: approval:grant or approval:* is prohibited
    targets = {"/inv/1"}

    with pytest.raises(AuthorizationError) as exc_info:
        issue_delegation(
            human_operator,
            sample_tenant,
            "tsk_1",
            {Permission("approval", "grant")},
            targets,
        )
    assert "approval authority" in str(exc_info.value)

    with pytest.raises(AuthorizationError):
        issue_delegation(
            human_operator,
            sample_tenant,
            "tsk_1",
            {Permission("approval", "*")},
            targets,
        )


def test_issue_delegation_prohibits_privilege_escalation(
    human_operator: Principal, sample_tenant: TenantId
):
    # AC-R04-002-03: Enforces INV-IAM-002: cannot delegate permission not held by delegator
    # human_operator does NOT possess 'tenant:manage' or 'user:manage'
    with pytest.raises(AuthorizationError) as exc_info:
        issue_delegation(
            human_operator,
            sample_tenant,
            "tsk_1",
            {Permission("tenant", "manage")},
            {"/tenant"},
        )
    assert "exceeds delegator permissions" in str(exc_info.value)


def test_issue_delegation_prohibits_sub_delegation(
    agent_principal: Principal, sample_tenant: TenantId
):
    # Agents cannot sub-delegate
    with pytest.raises(AuthorizationError) as exc_info:
        issue_delegation(
            agent_principal,
            sample_tenant,
            "tsk_sub",
            {Permission("investigation", "read")},
            {"/inv"},
        )
    assert "cannot sub-delegate" in str(exc_info.value)


def test_issue_delegation_prohibits_cross_tenant(
    human_operator: Principal, other_tenant: TenantId
):
    # Delegation tenant must match delegator tenant
    with pytest.raises(TenancyViolationError):
        issue_delegation(
            human_operator,
            other_tenant,
            "tsk_cross",
            {Permission("investigation", "read")},
            {"/inv"},
        )


def test_issue_delegation_empty_parameters(
    human_operator: Principal, sample_tenant: TenantId
):
    with pytest.raises(ValidationError):
        issue_delegation(
            human_operator, sample_tenant, "tsk_1", set(), {"/inv"}
        )

    with pytest.raises(ValidationError):
        issue_delegation(
            human_operator, sample_tenant, "tsk_1", {Permission("investigation", "read")}, set()
        )

    with pytest.raises(ValidationError):
        issue_delegation(
            human_operator, sample_tenant, "   ", {Permission("investigation", "read")}, {"/inv"}
        )


# ==============================================================================
# DelegationRevocationRegistry Unit Tests (AC-R04-002-05)
# ==============================================================================

def test_delegation_revocation_registry():
    # AC-R04-002-05: marks and verifies revocation state
    registry = DelegationRevocationRegistry()
    del_id = "del_revocation_test_123"

    assert registry.is_revoked(del_id) is False
    assert registry.get_revocation_reason(del_id) is None

    registry.revoke(del_id, reason="Security incident isolation")
    assert registry.is_revoked(del_id) is True
    assert registry.get_revocation_reason(del_id) == "Security incident isolation"

    # Blank/whitespace revocation
    with pytest.raises(ValidationError):
        registry.revoke("")


def test_delegation_revocation_registry_thread_safety():
    registry = DelegationRevocationRegistry()
    token_ids = [f"del_thread_test_{i}" for i in range(100)]

    def revoke_token(tid: str) -> None:
        registry.revoke(tid, reason="Concurrent test")

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(revoke_token, token_ids))

    for tid in token_ids:
        assert registry.is_revoked(tid) is True
