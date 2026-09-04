"""
RevPilot AI — TC-P07-022: Quota Atomic Reservation Concurrency Race Test
Specification: docs/21-finops/FINOPS-SPEC.md §2.3
Conforms to AC-P07-007-01 and INV-COST-001.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId


@pytest.fixture(autouse=True)
def _isolate_finops_module():
    """Ensure finops module is clean in test environment."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.finops"):
            sys.modules.pop(mod, None)


def test_quota_atomic_reservation_race_prevents_overallocation():
    """
    TC-P07-022 / AC-P07-007-01:
    Concurrency race: 100 concurrent threads competing for final budget ($100 hard limit, $10 per request).
    Exactly 10 threads succeed ($100 total reserved); 90 threads are cleanly rejected with QUOTA_EXHAUSTED.
    Under-budget spend is zero; over-allocation is physically prevented.
    """
    from revpilot.modules.finops import (
        QuotaManager,
        QuotaExhaustedError,
        SpendReservationToken,
    )

    manager = QuotaManager()
    tenant_id = TenantId.generate()

    # Hard spend budget = $100.00
    hard_limit = Decimal("100.00")
    manager.set_quota_policy(tenant_id, hard_spend_limit_usd=hard_limit)

    request_amount = Decimal("10.00")
    num_threads = 100

    successful_tokens: list[SpendReservationToken] = []
    rejected_count = 0
    errors: list[Exception] = []

    def worker_attempt():
        try:
            token = manager.reserve_spend(tenant_id=tenant_id, estimated_usd=request_amount)
            return ("SUCCESS", token)
        except QuotaExhaustedError as exc:
            return ("REJECTED", exc)
        except Exception as exc:
            return ("ERROR", exc)

    with ThreadPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(worker_attempt) for _ in range(num_threads)]
        for f in futures:
            status, res = f.result()
            if status == "SUCCESS":
                successful_tokens.append(res)
            elif status == "REJECTED":
                rejected_count += 1
            else:
                errors.append(res)

    # 1. Verification of Atomic Concurrency Serialization (AC-P07-007-01)
    assert len(errors) == 0, f"Unexpected errors during concurrency: {errors}"
    assert len(successful_tokens) == 10, f"Expected exactly 10 successful reservations, got {len(successful_tokens)}"
    assert rejected_count == 90, f"Expected exactly 90 rejections, got {rejected_count}"

    # Verify policy counters: exactly $100 reserved, remaining = $0
    policy = manager.get_quota_policy(tenant_id)
    assert policy.reserved_spend_usd == Decimal("100.00")
    assert policy.committed_spend_usd == Decimal("0.00")

    # 2. Finalize all 10 reservations
    for tok in successful_tokens:
        manager.finalize_spend(tok, actual_usd=Decimal("10.00"))

    assert policy.reserved_spend_usd == Decimal("0.00")
    assert policy.committed_spend_usd == Decimal("100.00")

    # 3. Post-Exhaustion Verification: Any new attempt fails closed (402/429)
    with pytest.raises(QuotaExhaustedError) as exc_info:
        manager.reserve_spend(tenant_id=tenant_id, estimated_usd=Decimal("0.01"))
    assert exc_info.value.status_code == 402
    assert exc_info.value.code == "QUOTA_EXHAUSTED"
