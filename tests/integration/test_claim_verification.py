"""
RevPilot AI — Integration Tests for Claim Verification Endpoint (AR-020)
Verifies deterministic artifact dereference, tenant ACL isolation, and citation span validation.
Enforces INV-AI-001 (ungrounded claim rejection) and INV-TEN-001 (strict tenant isolation).
"""

from __future__ import annotations

import pytest


@pytest.fixture
def client_fixture():
    from fastapi.testclient import TestClient
    from apps.api.main import app

    token = "token_usr_dev_01_tnt_dev_001"
    app.state.auth_adapter.issue_test_token(
        token,
        sub="usr_dev_01",
        tenant_id="tnt_dev_001",
        roles=frozenset(["SYSTEM_ADMIN", "ADMIN", "OPERATOR", "ANALYST", "INVESTIGATOR"]),
    )
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client, app
    if hasattr(app.state, "evidence_store"):
        delattr(app.state, "evidence_store")


def test_claim_verify_all_valid(client_fixture):
    client, app = client_fixture
    payload = {
        "statement": "Carrier SLA penalty increased churn by 14%",
        "epistemic_category": "CAUSAL_ESTIMATE",
        "evidence_references": ["evd_001", "evd_002"],
    }
    res = client.post("/api/v1/claims/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["statement"] == payload["statement"]
    assert data["epistemic_category"] == "CAUSAL_ESTIMATE"
    assert data["verifier_status"] == "VERIFIED"
    assert data["evidence_cited_count"] == 2
    assert data["citation_spans_valid"] is True
    assert data["temporal_leakage_detected"] is False
    assert data["rejection_reason"] is None


def test_claim_verify_nonexistent_artifact(client_fixture):
    client, app = client_fixture
    payload = {
        "statement": "Fraudulent return ring detected in Midwest",
        "epistemic_category": "CAUSAL_ESTIMATE",
        "evidence_references": ["evd_missing_404_not_found"],
    }
    res = client.post("/api/v1/claims/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["verifier_status"] == "UNVERIFIED"
    assert data["citation_spans_valid"] is False
    assert data["evidence_cited_count"] == 1
    assert data["rejection_reason"] is not None
    assert "not found" in data["rejection_reason"].lower()


def test_claim_verify_cross_tenant_artifact(client_fixture):
    client, app = client_fixture
    # Seed an evidence record owned by a foreign tenant
    app.state.evidence_store = {
        "evd_foreign_001": {
            "id": "evd_foreign_001",
            "tenant_id": "tnt_foreign_999",
            "citation_span": {"start": 0, "end": 100, "text": "Foreign tenant confidential evidence"},
        }
    }
    payload = {
        "statement": "Cross tenant leakage hypothesis",
        "epistemic_category": "CAUSAL_ESTIMATE",
        "evidence_references": ["evd_foreign_001"],
    }
    res = client.post("/api/v1/claims/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["verifier_status"] == "UNVERIFIED"
    assert data["citation_spans_valid"] is False
    assert data["rejection_reason"] is not None
    assert "does not belong to tenant" in data["rejection_reason"]


def test_claim_verify_empty_references(client_fixture):
    client, app = client_fixture
    payload = {
        "statement": "Ungrounded speculation without supporting evidence",
        "epistemic_category": "CAUSAL_ESTIMATE",
        "evidence_references": [],
    }
    res = client.post("/api/v1/claims/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["verifier_status"] == "NEED_MORE_EVIDENCE"
    assert data["citation_spans_valid"] is False
    assert data["evidence_cited_count"] == 0
    assert data["rejection_reason"] is None


def test_claim_verify_invalid_citation_span(client_fixture):
    client, app = client_fixture
    # Seed an evidence record with empty / invalid citation span
    app.state.evidence_store = {
        "evd_empty_span": {
            "id": "evd_empty_span",
            "tenant_id": "tnt_dev_001",
            "citation_span": {},
        }
    }
    payload = {
        "statement": "Claim with empty citation span record",
        "epistemic_category": "CAUSAL_ESTIMATE",
        "evidence_references": ["evd_empty_span"],
    }
    res = client.post("/api/v1/claims/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["verifier_status"] == "UNVERIFIED"
    assert data["citation_spans_valid"] is False
    assert data["rejection_reason"] is not None
    assert "invalid citation span" in data["rejection_reason"]
