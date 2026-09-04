"""
RevPilot AI — TC-P07-025: Cryptographic Audit Hash Chain Integrity Test
Specification: docs/22-billing/AUDIT-LOG-SPEC.md §3
Conforms to INV-AUD-001, NFR-AUD-001, and TC-P07-025.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId, PrincipalId


@pytest.fixture(autouse=True)
def _isolate_finops_module():
    """Ensure finops module is clean in test environment."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.finops"):
            sys.modules.pop(mod, None)


def test_audit_hash_chain_integrity_and_tamper_detection():
    """
    TC-P07-025:
    - Cryptographic SHA-256 hash chaining binds each audit record to its predecessor.
    - An unaltered log chain verifies cleanly (100% integrity).
    - Any unauthorized historical record alteration is detected immediately.
    """
    from revpilot.modules.finops import AuditHashChainService

    audit_service = AuditHashChainService()
    tenant_id = TenantId.generate()
    actor_id = PrincipalId.generate()

    # 1. Append Sequence of Canonical Audit Events
    events_data = [
        ("identity.principal.created", "CREATE", {"username": "pilot_admin"}),
        ("identity.auth.success", "LOGIN", {"ip": "192.168.1.1"}),
        ("connector.activated", "ACTIVATE", {"provider": "stripe"}),
        ("finops.spend.reserved", "RESERVE", {"amount_usd": 15.00}),
        ("tenancy.lifecycle.activated", "ACTIVATE", {"tier": "pilot"}),
    ]

    for ev_type, action, details in events_data:
        audit_service.append_event(
            tenant_id=tenant_id,
            actor_id=actor_id,
            event_type=ev_type,
            action=action,
            details=details,
        )

    # 2. Verify Pristine Chain Integrity
    is_valid, error = audit_service.verify_chain_integrity()
    assert is_valid is True
    assert error is None

    # 3. Simulate Malicious Tampering of Historical Event (Node at index 2)
    # Attacker attempts to modify details to conceal an unauthorized action
    tampered_record = audit_service._chain[2]
    # Inject forged details without updating hash chain
    tampered_record.details["forged_attribute"] = "malicious_actor_injected"

    # 4. Verify Immediate Tamper Detection (TC-P07-025)
    tamper_detected, tamper_error = audit_service.verify_chain_integrity()
    assert tamper_detected is False
    assert tamper_error is not None
    assert "Tamper detected at index 2" in tamper_error
