"""
Contract tests for RevPilot AI Shared Kernel (TASK-R01-004).
Verifies the Rail 1 Exit Gate: IDs, money, time, errors, and tenant primitives pass contracts.
"""

from decimal import Decimal
import pytest

# Verify direct importability from root of shared package
import revpilot.shared as shared
from revpilot.shared import (
    EntityId,
    TenantId,
    PrincipalId,
    OrganizationId,
    InvestigationId,
    EvidenceId,
    ActionId,
    ApprovalId,
    UtcDateTime,
    TimeWindow,
    Currency,
    Money,
    DomainError,
    NotFoundError,
    ValidationError,
    TenancyViolationError,
    AuthorizationError,
    Result,
    Success,
    Failure,
    CorrelationContext,
    TenantContext,
    PrincipalContext,
    SecurityContext,
)


def test_shared_kernel_exports_contract():
    """Verify all symbols defined in __all__ exist and are accessible."""
    assert len(shared.__all__) == 28
    for symbol_name in shared.__all__:
        assert hasattr(shared, symbol_name), f"Missing exported symbol: {symbol_name}"



def test_rail_1_identifiers_contract():
    """Verify typed entity identifiers contract."""
    tid = TenantId.generate()
    pid = PrincipalId.generate()
    oid = OrganizationId.generate()
    inv = InvestigationId.generate()
    evd = EvidenceId.generate()
    act = ActionId.generate()
    app = ApprovalId.generate()

    assert str(tid).startswith("tnt_")
    assert str(pid).startswith("usr_")
    assert str(oid).startswith("org_")
    assert str(inv).startswith("inv_")
    assert str(evd).startswith("evd_")
    assert str(act).startswith("act_")
    assert str(app).startswith("app_")

    # Immutability
    with pytest.raises(Exception):
        tid.value = "mutated"  # type: ignore


def test_rail_1_monetary_contract():
    """Verify precision monetary contract and currency isolation."""
    m1 = Money("1500.00", Currency.USD)
    m2 = Money("250.50", "USD")

    total = m1 + m2
    assert total.amount == Decimal("1750.5000")
    assert total.currency == Currency.USD
    assert str(total) == "USD 1,750.50"

    # Float rejection
    with pytest.raises(TypeError, match="Float amounts are strictly forbidden"):
        Money(100.5, Currency.USD)

    # Cross-currency arithmetic rejection
    m_eur = Money("100.00", Currency.EUR)
    with pytest.raises(ValueError, match="Currency mismatch"):
        _ = m1 + m_eur


def test_rail_1_temporal_contract():
    """Verify UTC-only temporal contract and time window invariants."""
    now = UtcDateTime.now()
    t1 = UtcDateTime.from_iso("2026-06-01T00:00:00Z")
    t2 = UtcDateTime.from_iso("2026-06-02T00:00:00Z")

    window = TimeWindow(start=t1, end=t2)
    assert window.duration_seconds() == 86400.0

    # Inverted window rejected
    with pytest.raises(ValueError, match="must precede or equal end"):
        TimeWindow(start=t2, end=t1)


def test_rail_1_errors_and_results_contract():
    """Verify domain error hierarchy and functional result chaining."""
    def divide(a: int, b: int) -> Result[int, DomainError]:
        if b == 0:
            return Failure(ValidationError("Division by zero", {"numerator": a}))
        return Success(a // b)

    res_ok = divide(10, 2).map(lambda x: x * 5)
    assert res_ok.is_success is True
    assert res_ok.unwrap() == 25

    res_err = divide(10, 0).map(lambda x: x * 5)
    assert res_err.is_failure is True
    err = res_err.unwrap_error()
    assert err.code == "VALIDATION_ERROR"
    assert err.retryable is False
    assert err.to_dict()["code"] == "VALIDATION_ERROR"


def test_rail_1_tenancy_and_security_contract():
    """Verify tenancy invariants (INV-TEN-001, INV-TEN-002, INV-TEN-003, INV-IAM-001)."""
    tid = TenantId.generate()
    oid = OrganizationId.generate()
    pid = PrincipalId.generate()

    tenant_ctx = TenantContext(tenant_id=tid, organization_id=oid, tier="enterprise")
    principal_ctx = PrincipalContext(
        principal_id=pid,
        tenant_id=tid,
        roles=frozenset(["analyst"]),
        permissions=frozenset(["investigation:read"]),
    )

    security_ctx = SecurityContext.create(tenant=tenant_ctx, principal=principal_ctx)
    assert security_ctx.tenant.tenant_id == tid
    assert security_ctx.principal.has_permission("investigation:read") is True

    # Cross-tenant breach attempt fails closed
    foreign_tid = TenantId.generate()
    foreign_principal = PrincipalContext(principal_id=pid, tenant_id=foreign_tid)
    with pytest.raises(TenancyViolationError, match="Cross-tenant context mismatch"):
        SecurityContext.create(tenant=tenant_ctx, principal=foreign_principal)


def test_rail_1_correlation_contract():
    """Verify distributed correlation propagation contract (ADR-0010)."""
    root = CorrelationContext.create_root()
    child = root.create_child()

    assert child.trace_id == root.trace_id
    assert child.correlation_id == root.correlation_id
    assert child.causation_id == root.span_id
    assert child.span_id != root.span_id

    d = child.to_dict()
    assert d["trace_id"] == root.trace_id
    assert d["causation_id"] == root.span_id
