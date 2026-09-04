"""
RevPilot AI — Contract Tests: Production Readiness Gate & Evidence Matrix
Specification: docs/24-sre/PRODUCTION-READINESS-GATE.md §1..§11
Specification: tasks/PHASE-08/TASK-P08-001.md
Conforms to INV-REL-001, INV-AUD-001, AC-P08-001-01, AC-P08-001-02.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

from revpilot.modules.operations.readiness import (
    CANONICAL_GATE_CONTROLS,
    EvidenceDigestMismatchError,
    EvidenceItem,
    GateControlDefinition,
    GateControlFailedError,
    GateControlResult,
    GateControlStatus,
    GateVerdict,
    IncompleteEvaluationError,
    ProductionReadinessGateService,
    ReadinessGateManifest,
)


def test_canonical_31_controls_completeness():
    """
    Verifies that CANONICAL_GATE_CONTROLS contains exactly 31 controls
    matching PRODUCTION-READINESS-GATE.md §9 matrix.
    """
    assert len(CANONICAL_GATE_CONTROLS) == 31

    expected_control_ids = [
        "PRG-TEN-01", "PRG-TEN-02",
        "PRG-IAM-01", "PRG-IAM-02",
        "PRG-SEC-01", "PRG-SEC-02",
        "PRG-CON-01", "PRG-CON-02", "PRG-CON-03",
        "PRG-WF-01", "PRG-WF-02",
        "PRG-ACT-01", "PRG-ACT-02", "PRG-ACT-03",
        "PRG-AUD-01", "PRG-AUD-02",
        "PRG-EVD-01",
        "PRG-DAT-01", "PRG-DAT-02", "PRG-DAT-03",
        "PRG-OBS-01", "PRG-OBS-02",
        "PRG-SRE-01", "PRG-SRE-02",
        "PRG-DR-01",
        "PRG-FIN-01", "PRG-FIN-02",
        "PRG-AI-01", "PRG-AI-02",
        "PRG-REL-01",
        "PRG-INC-01",
    ]

    for cid in expected_control_ids:
        assert cid in CANONICAL_GATE_CONTROLS, f"Missing canonical control: {cid}"
        ctrl: GateControlDefinition = CANONICAL_GATE_CONTROLS[cid]
        assert ctrl.control_id == cid
        assert bool(ctrl.domain)
        assert bool(ctrl.target_requirement)
        assert bool(ctrl.description)
        assert bool(ctrl.required_evidence_artifact)
        assert bool(ctrl.owner_role)
        assert bool(ctrl.validation_method)
        assert bool(ctrl.blocking_impact)
        assert bool(ctrl.exit_condition)

    # Verify canonical defaults per matrix (§9)
    not_executed_ids = {"PRG-SRE-01", "PRG-DR-01", "PRG-AI-02", "PRG-INC-01"}
    for cid, ctrl in CANONICAL_GATE_CONTROLS.items():
        if cid in not_executed_ids:
            assert ctrl.default_status == GateControlStatus.NOT_EXECUTED
        else:
            assert ctrl.default_status == GateControlStatus.PLANNED


def test_fail_closed_initial_verdict_blocked():
    """
    INV-REL-001 / AC-P08-001-01:
    Initial unverified service strictly evaluates to PRODUCTION_BLOCKED.
    """
    service = ProductionReadinessGateService()
    verdict = service.get_composite_verdict()
    assert verdict == GateVerdict.PRODUCTION_BLOCKED

    # Generating manifest with require_all_pass=True must raise IncompleteEvaluationError (422)
    with pytest.raises(IncompleteEvaluationError) as exc_info:
        service.generate_gate_manifest(require_all_pass=True)

    assert exc_info.value.code == "INCOMPLETE_EVALUATION"
    assert exc_info.value.status_code == 422
    assert "unpassed_controls" in exc_info.value.details
    assert len(exc_info.value.details["unpassed_controls"]) == 31


def test_missing_or_invalid_evidence_artifact_fails_closed(tmp_path: Path):
    """
    Missing artifact path raises GateControlFailedError (500).
    """
    service = ProductionReadinessGateService()
    non_existent = tmp_path / "non_existent_artifact.log"

    with pytest.raises(GateControlFailedError) as exc_info:
        service.evaluate_control("PRG-TEN-01", non_existent)

    assert exc_info.value.code == "GATE_CONTROL_FAILED"
    assert exc_info.value.status_code == 500


def test_evidence_tamper_detection_mismatch(tmp_path: Path):
    """
    INV-AUD-001 / Error contract:
    Altered artifact SHA-256 raises EvidenceDigestMismatchError (422)
    and emits EVIDENCE_TAMPERING_DETECTED audit event.
    """
    service = ProductionReadinessGateService()

    artifact = tmp_path / "rls_injection_test.log"
    artifact.write_text("Original genuine RLS audit test output: 0 leaks", encoding="utf-8")
    actual_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

    tampered_expected_digest = "a" * 64

    with pytest.raises(EvidenceDigestMismatchError) as exc_info:
        service.evaluate_control(
            control_id="PRG-TEN-01",
            evidence_artifact_path=artifact,
            expected_digest=tampered_expected_digest,
        )

    assert exc_info.value.code == "EVIDENCE_DIGEST_MISMATCH"
    assert exc_info.value.status_code == 422
    assert exc_info.value.details["expected_digest"] == tampered_expected_digest
    assert exc_info.value.details["computed_digest"] == actual_digest

    # Audit event must be emitted
    tamper_events = [
        e for e in service.audit_logs if e["event_type"] == "EVIDENCE_TAMPERING_DETECTED"
    ]
    assert len(tamper_events) == 1
    assert tamper_events[0]["entity_id"] == "PRG-TEN-01"


def test_control_failed_validation_marks_blocked(tmp_path: Path):
    """
    Failed validation check raises GateControlFailedError and sets status to BLOCKED.
    """
    service = ProductionReadinessGateService()

    artifact = tmp_path / "token_drift.log"
    artifact.write_text("Token revocation drift observed: 2500ms > 1000ms", encoding="utf-8")

    with pytest.raises(GateControlFailedError) as exc_info:
        service.evaluate_control(
            control_id="PRG-IAM-02",
            evidence_artifact_path=artifact,
            passed=False,
            message="Privilege escalation guard failed latency boundary",
        )

    assert exc_info.value.code == "GATE_CONTROL_FAILED"
    ctrl_res = service.get_control_result("PRG-IAM-02")
    assert ctrl_res is not None
    assert ctrl_res.status == GateControlStatus.BLOCKED

    # Composite verdict remains PRODUCTION_BLOCKED
    assert service.get_composite_verdict() == GateVerdict.PRODUCTION_BLOCKED


def test_full_31_controls_pass_manifest_signing_and_archive(tmp_path: Path):
    """
    AC-P08-001-01 & AC-P08-001-02:
    Evaluating all 31 controls with valid evidence transitions composite verdict
    to PRODUCTION_READY, generates HMAC-signed manifest, and archives immutable file.
    """
    service = ProductionReadinessGateService(evaluator_principal="principal:lead-sre")
    evidence_dir = tmp_path / "artifacts"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # 1. Provide authentic evidence for each canonical control
    for idx, (cid, definition) in enumerate(CANONICAL_GATE_CONTROLS.items()):
        art_path = evidence_dir / f"{cid.lower()}_evidence.log"
        content = f"VERIFIED: {cid} - {definition.description} - Exit condition met: {definition.exit_condition}"
        art_path.write_text(content, encoding="utf-8")
        expected_digest = hashlib.sha256(art_path.read_bytes()).hexdigest()

        # Partial evaluation should still be PRODUCTION_BLOCKED until all 31 pass
        if idx < 30:
            assert service.get_composite_verdict() == GateVerdict.PRODUCTION_BLOCKED

        result = service.evaluate_control(
            control_id=cid,
            evidence_artifact_path=art_path,
            expected_digest=expected_digest,
            passed=True,
            message=f"Verified {definition.description}",
        )
        assert result.status == GateControlStatus.PASS
        assert result.evidence is not None
        assert result.evidence.sha256_digest == expected_digest

    # 2. All 31 controls evaluated to PASS -> verdict must be PRODUCTION_READY
    assert service.get_composite_verdict() == GateVerdict.PRODUCTION_READY

    # 3. Generate sealed manifest
    signing_key = "prg-super-secret-hmac-key-2026"
    manifest: ReadinessGateManifest = service.generate_gate_manifest(
        signing_key=signing_key,
        require_all_pass=True,
    )

    assert manifest.verdict == GateVerdict.PRODUCTION_READY
    assert manifest.total_controls == 31
    assert manifest.passed_controls == 31
    assert manifest.blocked_controls == 0
    assert len(manifest.manifest_hash) == 64
    assert len(manifest.signature) == 64

    # 4. Cryptographic signature verification
    valid_sig = ProductionReadinessGateService.verify_manifest_signature(manifest, signing_key)
    assert valid_sig is True

    # Bad key must fail verification
    invalid_sig = ProductionReadinessGateService.verify_manifest_signature(manifest, "wrong-key")
    assert invalid_sig is False

    # 5. Archive manifest to immutable sink (AC-P08-001-02)
    sink_dir = tmp_path / "evidence_sink"
    archived_file = service.archive_manifest(manifest, sink_dir)

    assert archived_file.exists()
    assert archived_file.is_file()

    # Verify archived file content matches manifest
    archived_data = json.loads(archived_file.read_text(encoding="utf-8"))
    assert archived_data["manifest_id"] == manifest.manifest_id
    assert archived_data["manifest_hash"] == manifest.manifest_hash
    assert archived_data["verdict"] == "PRODUCTION_READY"
    assert len(archived_data["controls"]) == 31

    # 6. Audit Trail verification (INV-AUD-001)
    audit_logs = service.audit_logs
    assert len(audit_logs) >= 33  # 31 control evaluations + 1 manifest generated + 1 manifest archived

    manifest_generated_event = next(
        e for e in audit_logs if e["event_type"] == "GATE_MANIFEST_GENERATED"
    )
    assert manifest_generated_event["details"]["manifest_hash"] == manifest.manifest_hash
    assert manifest_generated_event["details"]["verdict"] == "PRODUCTION_READY"

    manifest_archived_event = next(
        e for e in audit_logs if e["event_type"] == "GATE_MANIFEST_ARCHIVED"
    )
    assert manifest_archived_event["details"]["manifest_hash"] == manifest.manifest_hash
