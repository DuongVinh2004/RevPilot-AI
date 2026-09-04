"""
RevPilot AI — Concurrency RLS Isolation and Load Profile Tests
Specification: docs/29-testing/TEST-STRATEGY.md §13.1
Specification: docs/24-sre/PRODUCTION-READINESS-GATE.md §9 (PRG-SRE-01)
Conforms to INV-TEN-001, AC-P08-006-02, and TC-P08-001.
"""

from __future__ import annotations

import pytest

from revpilot.modules.testing.resilience.harness import (
    BenchmarkResult,
    BenchmarkSloBreachError,
    IsolationLeakUnderLoadError,
    ResilienceTestHarness,
)


@pytest.fixture
def harness() -> ResilienceTestHarness:
    return ResilienceTestHarness()


def test_rls_isolation_under_500_concurrent_threads_zero_leak(
    harness: ResilienceTestHarness,
):
    """
    AC-P08-006-02: 500 concurrent threads competing for tenant database connections
    experience zero cross-tenant query leakage (INV-TEN-001).
    """
    report = harness.verify_rls_concurrency_isolation(
        tenant_count=25,
        concurrent_threads=500,
    )

    assert report["status"] == "PASS"
    assert report["concurrent_threads"] == 500
    assert report["total_queries"] == 500
    assert report["isolation_breaches"] == 0


def test_rls_isolation_leak_detection_raises_error(
    harness: ResilienceTestHarness,
):
    """
    Test that cross-tenant leakage under concurrent load triggers ISOLATION_LEAK_UNDER_LOAD (500).
    """
    with pytest.raises(IsolationLeakUnderLoadError) as exc_info:
        harness.verify_rls_concurrency_isolation(
            tenant_count=5,
            concurrent_threads=50,
            inject_leak_for_tenant="tnt_isolated_002",
        )

    err = exc_info.value
    assert err.code == "ISOLATION_LEAK_UNDER_LOAD"
    assert err.status_code == 500
    assert err.retryable is False
    assert err.details["isolation_breaches"] > 0


def test_sustained_load_profile_1000_rps(harness: ResilienceTestHarness):
    """
    Verify sustained load profile (1,000 req/s) satisfies P95 latency <= 1500ms SLO.
    """
    result = harness.execute_load_profile(
        target_rps=1000,
        duration_sec=2,
        tenant_count=50,
        concurrency=100,
        enforce_slo=True,
    )

    assert isinstance(result, BenchmarkResult)
    assert result.throughput_rps == 1000.0
    assert result.p95_latency_ms <= 1500.0
    assert result.error_rate_percent == 0.0
    assert result.isolation_breaches == 0


def test_spike_load_profile_5000_rps(harness: ResilienceTestHarness):
    """
    Verify spike load profile (5,000 req/s) executes within bounds.
    """
    result = harness.execute_load_profile(
        target_rps=5000,
        duration_sec=1,
        tenant_count=100,
        concurrency=250,
        enforce_slo=True,
    )

    assert isinstance(result, BenchmarkResult)
    assert result.throughput_rps == 5000.0
    assert result.p95_latency_ms <= 1500.0
    assert result.isolation_breaches == 0


def test_load_profile_slo_breach_raises_error(harness: ResilienceTestHarness):
    """
    Verify P95 latency > 1500ms raises BENCHMARK_SLO_BREACH (500).
    """
    with pytest.raises(BenchmarkSloBreachError) as exc_info:
        harness.execute_load_profile(
            target_rps=1000,
            duration_sec=1,
            tenant_count=10,
            force_breach=True,
            enforce_slo=True,
        )

    err = exc_info.value
    assert err.code == "BENCHMARK_SLO_BREACH"
    assert err.status_code == 500
    assert err.retryable is False
    assert err.details["p95_latency_ms"] > 1500.0
