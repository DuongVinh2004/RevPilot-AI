"""
Unit tests for Error Hierarchy, Result Types, and Correlation Context (TASK-R01-002).
"""

import pytest

from revpilot.shared.errors import (
    DomainError,
    NotFoundError,
    ValidationError,
    ConflictError,
    AuthorizationError,
    AuthenticationError,
    TenancyViolationError,
    ConcurrencyError,
    RateLimitExceededError,
)
from revpilot.shared.results import Result, Success, Failure
from revpilot.shared.correlation import CorrelationContext


# ==========================================
# 1. Error Hierarchy Tests
# ==========================================

def test_domain_error_base():
    err = DomainError(code="TEST_ERROR", message="Something broke", details={"field": "test"}, retryable=True)
    d = err.to_dict()
    assert d["code"] == "TEST_ERROR"
    assert d["message"] == "Something broke"
    assert d["details"] == {"field": "test"}
    assert d["retryable"] is True
    assert "TEST_ERROR" in repr(err)


def test_standard_subclasses():
    nf = NotFoundError("Entity not found", {"id": "123"})
    assert nf.code == "NOT_FOUND"
    assert nf.retryable is False

    val = ValidationError("Invalid parameter")
    assert val.code == "VALIDATION_ERROR"
    assert val.retryable is False

    conf = ConflictError("State conflict")
    assert conf.code == "CONFLICT"
    assert conf.retryable is False

    authz = AuthorizationError("Permission denied")
    assert authz.code == "FORBIDDEN"
    assert authz.retryable is False

    authn = AuthenticationError("Unauthenticated")
    assert authn.code == "UNAUTHORIZED"
    assert authn.retryable is False


def test_tenancy_violation_error():
    t_err = TenancyViolationError("Cross-tenant access detected", {"tenant": "tnt_999"})
    assert t_err.code == "TENANCY_VIOLATION"
    assert t_err.retryable is False
    assert t_err.details["tenant"] == "tnt_999"


def test_retryable_errors():
    conc = ConcurrencyError("Lock timeout")
    assert conc.code == "CONCURRENCY_CONFLICT"
    assert conc.retryable is True

    rl = RateLimitExceededError("Rate limit exceeded")
    assert rl.code == "RATE_LIMITED"
    assert rl.retryable is True


# ==========================================
# 2. Functional Result Tests
# ==========================================

def test_success_branch():
    s = Success(42)
    assert s.is_success is True
    assert s.is_failure is False
    assert s.unwrap() == 42

    with pytest.raises(ValueError, match="Cannot unwrap_error on Success"):
        s.unwrap_error()

    # Map
    s_mapped = s.map(lambda x: str(x * 2))
    assert s_mapped.is_success is True
    assert s_mapped.unwrap() == "84"

    # Map err does nothing to Success
    s_err = s.map_err(lambda e: "new_err")
    assert s_err.unwrap() == 42

    # and_then
    s_chained = s.and_then(lambda x: Success(f"val: {x}"))
    assert s_chained.unwrap() == "val: 42"


def test_failure_branch():
    err = NotFoundError("Item not found")
    f: Result[int, DomainError] = Failure(err)
    assert f.is_success is False
    assert f.is_failure is True
    assert f.unwrap_error() is err

    with pytest.raises(NotFoundError, match="Item not found"):
        f.unwrap()

    # Map does nothing to Failure
    f_mapped = f.map(lambda x: x + 10)
    assert f_mapped.is_failure is True

    # Map err transforms the error
    f_err = f.map_err(lambda e: f"wrapped: {e.message}")
    assert f_err.unwrap_error() == "wrapped: Item not found"

    # and_then does nothing to Failure
    f_chained = f.and_then(lambda x: Success(x * 2))
    assert f_chained.is_failure is True


# ==========================================
# 3. Correlation Context Tests
# ==========================================

def test_correlation_root():
    root = CorrelationContext.create_root("custom_corr_id")
    assert root.correlation_id == "custom_corr_id"
    assert len(root.trace_id) == 32
    assert len(root.span_id) == 16
    assert root.causation_id is None

    d = root.to_dict()
    assert d["trace_id"] == root.trace_id
    assert d["span_id"] == root.span_id
    assert d["correlation_id"] == "custom_corr_id"
    assert "causation_id" not in d


def test_correlation_child():
    root = CorrelationContext.create_root()
    child = root.create_child()

    assert child.trace_id == root.trace_id
    assert child.correlation_id == root.correlation_id
    assert child.causation_id == root.span_id
    assert child.span_id != root.span_id

    d = child.to_dict()
    assert d["causation_id"] == root.span_id


def test_correlation_validation():
    with pytest.raises(ValueError, match="trace_id"):
        CorrelationContext(trace_id="", span_id="s1", correlation_id="c1")
    with pytest.raises(ValueError, match="span_id"):
        CorrelationContext(trace_id="t1", span_id="", correlation_id="c1")
    with pytest.raises(ValueError, match="correlation_id"):
        CorrelationContext(trace_id="t1", span_id="s1", correlation_id="")
