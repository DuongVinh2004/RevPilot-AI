"""
RevPilot AI — Blast Radius & Spend Limit Enforcement Tests
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §5.2
Specification: docs/21-finops/FINOPS-SPEC.md §3
Conforms to NFR-COST-001 and TC-P06-020.
"""

from __future__ import annotations
from decimal import Decimal
import pytest

from revpilot.modules.safety.blast_radius import (
    MAX_AFFECTED_ENTITIES,
    BlastRadiusLimiter,
    BlastRadiusExceededError,
)
from revpilot.modules.approval.policy.authority import (
    TIER_1_MAX_SPEND,
    TIER_2_MAX_SPEND,
    TIER_3_MAX_SPEND,
)


@pytest.fixture
def limiter() -> BlastRadiusLimiter:
    return BlastRadiusLimiter()


def test_entity_count_boundary_exact_ceiling_passes(limiter: BlastRadiusLimiter) -> None:
    """Target counts up to 500 entities must succeed."""
    result_500 = limiter.check_limits(
        target_count=MAX_AFFECTED_ENTITIES,
        estimated_cost_usd=Decimal("100.00"),
        tier=1,
    )
    assert result_500.is_success
    assert result_500.unwrap() is None

    result_zero = limiter.check_limits(
        target_count=0,
        estimated_cost_usd=Decimal("0.00"),
        tier=1,
    )
    assert result_zero.is_success


def test_entity_count_exceeding_ceiling_fails_closed(limiter: BlastRadiusLimiter) -> None:
    """Target counts exceeding 500 entities must fail closed with ERR_BLAST_RADIUS_EXCEEDED."""
    result_501 = limiter.check_limits(
        target_count=MAX_AFFECTED_ENTITIES + 1,
        estimated_cost_usd=Decimal("50.00"),
        tier=1,
    )
    assert result_501.is_failure
    err = result_501.unwrap_error()
    assert isinstance(err, BlastRadiusExceededError)
    assert err.code == "ERR_BLAST_RADIUS_EXCEEDED"
    assert "exceeds blast radius ceiling of 500 entities" in err.message

    result_large = limiter.check_limits(
        target_count=10000,
        estimated_cost_usd=Decimal("50.00"),
        tier=3,
    )
    assert result_large.is_failure
    assert result_large.unwrap_error().code == "ERR_BLAST_RADIUS_EXCEEDED"


def test_negative_entity_count_fails_closed(limiter: BlastRadiusLimiter) -> None:
    """Negative entity count must fail closed."""
    result = limiter.check_limits(
        target_count=-1,
        estimated_cost_usd=Decimal("10.00"),
        tier=1,
    )
    assert result.is_failure
    assert result.unwrap_error().code == "ERR_BLAST_RADIUS_EXCEEDED"


def test_tier_1_spend_ceiling_enforcement(limiter: BlastRadiusLimiter) -> None:
    """Tier 1 spend limit is strictly $250.00 USD."""
    # At exact limit
    assert limiter.check_limits(10, TIER_1_MAX_SPEND, tier=1).is_success

    # Below limit
    assert limiter.check_limits(10, Decimal("249.99"), tier=1).is_success

    # Above limit by 1 cent
    breach = limiter.check_limits(10, Decimal("250.01"), tier=1)
    assert breach.is_failure
    assert breach.unwrap_error().code == "ERR_BLAST_RADIUS_EXCEEDED"
    assert "exceeds Tier 1 spend ceiling of 250.00 USD" in breach.unwrap_error().message


def test_tier_2_spend_ceiling_enforcement(limiter: BlastRadiusLimiter) -> None:
    """Tier 2 spend limit is strictly $1,000.00 USD."""
    assert limiter.check_limits(50, TIER_2_MAX_SPEND, tier=2).is_success
    assert limiter.check_limits(50, Decimal("999.99"), tier=2).is_success

    breach = limiter.check_limits(50, Decimal("1000.01"), tier=2)
    assert breach.is_failure
    assert breach.unwrap_error().code == "ERR_BLAST_RADIUS_EXCEEDED"


def test_tier_3_spend_ceiling_enforcement(limiter: BlastRadiusLimiter) -> None:
    """Tier 3 spend limit is strictly $10,000.00 USD."""
    assert limiter.check_limits(100, TIER_3_MAX_SPEND, tier=3).is_success
    assert limiter.check_limits(100, Decimal("9999.99"), tier=3).is_success

    breach = limiter.check_limits(100, Decimal("10000.01"), tier=3)
    assert breach.is_failure
    assert breach.unwrap_error().code == "ERR_BLAST_RADIUS_EXCEEDED"


def test_invalid_tier_fails_closed(limiter: BlastRadiusLimiter) -> None:
    """Tiers outside 1, 2, 3 fail closed."""
    for invalid_tier in [0, 4, -1, 99]:
        result = limiter.check_limits(10, Decimal("10.00"), tier=invalid_tier)
        assert result.is_failure
        assert result.unwrap_error().code == "ERR_BLAST_RADIUS_EXCEEDED"


def test_negative_cost_fails_closed(limiter: BlastRadiusLimiter) -> None:
    """Negative estimated spend must fail closed."""
    result = limiter.check_limits(10, Decimal("-0.01"), tier=1)
    assert result.is_failure
    assert result.unwrap_error().code == "ERR_BLAST_RADIUS_EXCEEDED"
