"""
Unit tests for canonical approval digest computation and verification (TASK-AR-011).
Conforms to INV-ACT-001, INV-ACT-002, AC-008.
"""

from dataclasses import asdict
import hmac
from unittest.mock import patch
import pytest

from revpilot.modules.approval.digest import (
    ApprovalArtifact,
    compute_approval_digest,
    verify_approval_digest,
)


def _create_sample_artifact(**overrides) -> ApprovalArtifact:
    kwargs = {
        "tenant_id": "tenant_123",
        "action_type": "ISSUE_SERVICE_CREDIT_VOUCHER",
        "target_entities": ["cust_enterprise_alpha", "sub_arr_450k"],
        "payload": {"amount": 2500, "currency": "USD"},
        "policy_version": "v1.0.0",
        "required_tier": "TIER_2",
        "expires_at": "2026-09-09T12:00:00Z",
        "created_by": "usr_operator_1",
    }
    kwargs.update(overrides)
    return ApprovalArtifact(**kwargs)


def test_01_deterministic_digest():
    """Deterministic: same input always produces same 64-char SHA-256 digest."""
    art1 = _create_sample_artifact()
    art2 = _create_sample_artifact()

    digest1 = compute_approval_digest(art1)
    digest2 = compute_approval_digest(art2)

    assert digest1 == digest2
    assert len(digest1) == 64
    assert isinstance(digest1, str)
    assert all(c in "0123456789abcdef" for c in digest1)


def test_02_changed_field_produces_different_digest():
    """Changed field → different digest."""
    base = _create_sample_artifact()
    base_digest = compute_approval_digest(base)

    altered = _create_sample_artifact(payload={"amount": 2501, "currency": "USD"})
    alt_digest = compute_approval_digest(altered)

    assert alt_digest != base_digest


def test_03_all_eight_fields_included():
    """All 8 fields included: altering each field changes digest, missing field raises ValueError."""
    base = _create_sample_artifact()
    base_digest = compute_approval_digest(base)

    field_alterations = [
        {"tenant_id": "tenant_999"},
        {"action_type": "UPDATE_BILLING_TIER"},
        {"target_entities": ["cust_beta"]},
        {"payload": {"different": True}},
        {"policy_version": "v2.0.0"},
        {"required_tier": "TIER_3"},
        {"expires_at": "2026-10-01T00:00:00Z"},
        {"created_by": "usr_other"},
    ]

    for alt in field_alterations:
        alt_art = _create_sample_artifact(**alt)
        alt_digest = compute_approval_digest(alt_art)
        assert alt_digest != base_digest, f"Altering {list(alt.keys())[0]} did not change digest"

    # Verify missing fields raise ValueError
    class MockArtifactMissingField:
        pass

    for field in (
        "tenant_id",
        "action_type",
        "target_entities",
        "payload",
        "policy_version",
        "required_tier",
        "expires_at",
        "created_by",
    ):
        mock_obj = MockArtifactMissingField()
        for k, v in asdict(base).items():
            if k != field:
                setattr(mock_obj, k, v)
        with pytest.raises(ValueError):
            compute_approval_digest(mock_obj)


def test_04_constant_time_compare():
    """verify_approval_digest uses constant-time comparison (hmac.compare_digest)."""
    art = _create_sample_artifact()
    digest = compute_approval_digest(art)

    with patch("hmac.compare_digest", wraps=hmac.compare_digest) as mock_cmp:
        assert verify_approval_digest(art, digest) is True
        mock_cmp.assert_called_once()

    assert verify_approval_digest(art, "a" * 64) is False


def test_05_empty_payload_dict_works():
    """Empty payload dict works and produces deterministic digest."""
    art = _create_sample_artifact(payload={})
    digest = compute_approval_digest(art)

    assert len(digest) == 64
    assert verify_approval_digest(art, digest) is True


def test_06_unicode_payload_works():
    """Unicode payload works without encoding failure and remains deterministic."""
    unicode_payload = {
        "description": "Thanh toán hoá đơn dịch vụ khách hàng 🚀",
        "merchant": "Công ty TNHH Giải Pháp Số",
        "currency": "₫",
    }
    art = _create_sample_artifact(payload=unicode_payload)
    digest = compute_approval_digest(art)

    assert len(digest) == 64
    assert verify_approval_digest(art, digest) is True
