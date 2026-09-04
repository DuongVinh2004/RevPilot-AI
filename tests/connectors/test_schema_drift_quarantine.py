"""
RevPilot AI — TC-P07-021: Schema Drift Quarantine & Reconciliation Test
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §5
Conforms to AC-P07-006-02 and INV-REL-001.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.modules.security.secrets.broker import SecretReference


@pytest.fixture(autouse=True)
def _isolate_connectors_module():
    """Ensure connectors module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.connectors"):
            sys.modules.pop(mod, None)


def test_schema_drift_classification_quarantine_and_reconciliation():
    """
    TC-P07-021 / AC-P07-006-02:
    - Breaking schema drift is quarantined with SHA-256 hash.
    - Connector lifecycle transitions from ACTIVE -> SCHEMA_DRIFT -> QUARANTINED.
    - Reprocessing quarantined records transitions connector through RECONCILIATION_REQUIRED -> ACTIVE.
    """
    from revpilot.modules.connectors import (
        ConnectorLifecycleService,
        ConnectorStatus,
    )
    from revpilot.modules.connectors.ingestion import (
        SchemaDriftClassifier,
        QuarantineService,
        DriftClassification,
    )

    lifecycle = ConnectorLifecycleService()
    classifier = SchemaDriftClassifier()
    quarantine = QuarantineService(lifecycle_service=lifecycle)

    tenant_id = TenantId.generate()
    secret_ref = SecretReference.generate()

    # 1. Setup Active Connector
    cid = lifecycle.register_connector(
        tenant_id=tenant_id,
        provider="salesforce",
        capability="crm_sync",
    )
    lifecycle.configure_credentials(cid, secret_ref=secret_ref, scopes=["contacts:read"])
    lifecycle.validate_connectivity(cid, probe_fn=lambda: True)

    rec = lifecycle.get_connector(cid)
    assert rec.status == ConnectorStatus.ACTIVE

    expected_schema = {
        "required_fields": {"id": str, "amount": (int, float), "currency": str},
        "optional_fields": {"description": str},
    }

    # 2. Fully Compatible Payload
    valid_payload = {"id": "lead_100", "amount": 25000.50, "currency": "USD"}
    res_valid = classifier.evaluate_payload(cid, valid_payload, expected_schema)
    assert res_valid.classification == DriftClassification.COMPATIBLE

    # 3. Additive Benign Payload (Non-destructive extra fields)
    benign_payload = {
        "id": "lead_101",
        "amount": 12000,
        "currency": "EUR",
        "custom_crm_tracking_tag": "marketing_campaign_q3",
    }
    res_benign = classifier.evaluate_payload(cid, benign_payload, expected_schema)
    assert res_benign.classification == DriftClassification.BENIGN
    assert "custom_crm_tracking_tag" in res_benign.extra_fields

    # 4. Breaking Schema Drift (Type mismatch on amount: dictionary instead of float/int)
    breaking_payload = {
        "id": "lead_102",
        "amount": {"nested_currency_object": 5000},  # Breaking type change!
        "currency": "USD",
    }
    res_breaking = classifier.evaluate_payload(cid, breaking_payload, expected_schema)
    assert res_breaking.classification == DriftClassification.BREAKING
    assert len(res_breaking.type_mismatches) >= 1

    # 5. Divert to Quarantine (AC-P07-006-02)
    qid = quarantine.divert_to_quarantine(
        tenant_id=tenant_id,
        connector_id=cid,
        raw_payload=breaking_payload,
        evaluation=res_breaking,
    )

    # Invariants Verification
    q_records = quarantine.get_quarantine_records(cid)
    assert len(q_records) == 1
    assert q_records[0].quarantine_id == qid
    assert len(q_records[0].payload_hash) == 64  # SHA-256 hex digest
    assert q_records[0].classification == DriftClassification.BREAKING

    # Connector State Machine Verification
    assert rec.status == ConnectorStatus.QUARANTINED
    assert rec.quarantine_count == 1

    # 6. Reconciliation Replay Workflow
    quarantine.reprocess_quarantine(quarantine_id=qid, new_mapping_version="2.0.0")

    # Verify reconciliation recovery back to ACTIVE
    assert q_records[0].reprocessed_at is not None
    assert q_records[0].mapping_version == "2.0.0"
    assert rec.status == ConnectorStatus.ACTIVE
