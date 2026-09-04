"""
RevPilot AI — Audit Stream Zero Drop and Compliance Evidence Packaging Tests
Specification: docs/25-compliance/COMPLIANCE-EVIDENCE-RUNBOOK.md §5, §6
Specification: docs/22-billing/AUDIT-LOG-SPEC.md §2, §3
Conforms to INV-AUD-001, ADR-0010, AC-P08-007-01, TC-P08-010, and TC-P08-011.
"""

from __future__ import annotations

import json
from pathlib import Path
import tarfile
import tempfile
import pytest

from revpilot.modules.compliance.evidence.collector import (
    CANONICAL_COMPLIANCE_CONTROLS,
    BundleIntegrityCompromisedError,
    EvidenceCollector,
    UnresolvedControlGapError,
)
from revpilot.modules.compliance.evidence.signer import EvidenceSigner
from revpilot.modules.finops import AuditHashChainService
from revpilot.shared.identifiers import PrincipalId, TenantId


@pytest.fixture
def collector() -> EvidenceCollector:
    return EvidenceCollector()


def test_package_all_16_controls_sealed_archive_valid_manifest(
    collector: EvidenceCollector,
    tmp_path: Path,
):
    """
    AC-P08-007-01: Evidence collector packages all 16 required controls
    into a sealed archive with valid SHA-256 manifest (TC-P08-010).
    """
    tar_path = tmp_path / "compliance_bundle.tar.gz"
    result_path = collector.collect_period_evidence(
        period_id="2026-Q3",
        output_tar_path=tar_path,
    )

    assert result_path.exists()
    assert result_path.stat().st_size > 0

    # Verify integrity using collector
    is_valid = collector.verify_bundle_integrity(result_path)
    assert is_valid is True

    # Inspect contents directly
    with tarfile.open(result_path, "r:gz") as tar:
        names = tar.getnames()
        assert "evidence-manifest.json" in names

        manifest_f = tar.extractfile("evidence-manifest.json")
        assert manifest_f is not None
        manifest_data = json.loads(manifest_f.read().decode("utf-8"))

        assert manifest_data["period"] == "2026-Q3"
        assert len(manifest_data["artifacts"]) == 16

        packaged_controls = {item["control_id"] for item in manifest_data["artifacts"]}
        assert packaged_controls == set(CANONICAL_COMPLIANCE_CONTROLS)

        for item in manifest_data["artifacts"]:
            assert item["sha256"]
            assert item["result"] == "PASS"
            assert f"artifacts/{item['filename']}" in names


def test_bundle_integrity_tampering_raises_error(
    collector: EvidenceCollector,
    tmp_path: Path,
):
    """
    Verify that altering artifact content after packaging triggers BUNDLE_INTEGRITY_COMPROMISED (422).
    """
    tar_path = tmp_path / "bundle_to_tamper.tar.gz"
    collector.collect_period_evidence(period_id="2026-Q3", output_tar_path=tar_path)

    # Extract, tamper with an artifact, and repack
    extract_dir = tmp_path / "extracted"
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(extract_dir)

    # Tamper with first artifact
    manifest_path = extract_dir / "evidence-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_artifact_filename = manifest["artifacts"][0]["filename"]

    target_file = extract_dir / "artifacts" / first_artifact_filename
    target_file.write_text('{"tampered": true}', encoding="utf-8")

    tampered_tar = tmp_path / "tampered_bundle.tar.gz"
    with tarfile.open(tampered_tar, "w:gz") as tar:
        tar.add(manifest_path, arcname="evidence-manifest.json")
        for f in (extract_dir / "artifacts").iterdir():
            tar.add(f, arcname=f"artifacts/{f.name}")

    with pytest.raises(BundleIntegrityCompromisedError) as exc_info:
        collector.verify_bundle_integrity(tampered_tar)

    err = exc_info.value
    assert err.code == "BUNDLE_INTEGRITY_COMPROMISED"
    assert err.status_code == 422


def test_missing_control_gap_raises_error(
    collector: EvidenceCollector,
    tmp_path: Path,
):
    """
    Verify that omitting any of the 16 controls triggers UNRESOLVED_CONTROL_GAP (422).
    """
    partial_dir = tmp_path / "partial"
    partial_dir.mkdir()
    # Provide only 15 controls (omit CTL-GOV-01)
    partial_map: dict[str, Path] = {}
    for c_id in CANONICAL_COMPLIANCE_CONTROLS[:-1]:
        p = partial_dir / f"{c_id}.json"
        p.write_text('{"test": true}', encoding="utf-8")
        partial_map[c_id] = p

    out_tar = tmp_path / "partial_bundle.tar.gz"
    with pytest.raises(UnresolvedControlGapError) as exc_info:
        collector.collect_period_evidence(
            period_id="2026-Q3",
            output_tar_path=out_tar,
            artifacts_map=partial_map,
        )

    err = exc_info.value
    assert err.code == "UNRESOLVED_CONTROL_GAP"
    assert err.status_code == 422
    assert "CTL-GOV-01" in err.details["missing_controls"]


def test_audit_stream_unbroken_hash_chain_zero_drop():
    """
    TC-P08-011 & INV-AUD-001: 100% unsampled audit logging maintains unbroken
    cryptographic SHA-256 hash chains with zero dropped security events.
    """
    audit_chain = AuditHashChainService()
    tenant_id = TenantId.generate()
    actor_id = PrincipalId.generate()

    # Log 100 sequential audit events
    for i in range(100):
        audit_chain.append_event(
            tenant_id=tenant_id,
            actor_id=actor_id,
            event_type="identity.auth.success",
            action="LOGIN",
            details={"seq": i, "client": "revpilot-web"},
        )

    # Verify unbroken chain
    is_valid, err_msg = audit_chain.verify_chain_integrity()
    assert is_valid is True
    assert err_msg is None

    # Simulate dropping an event in the middle (index 45)
    audit_chain._chain.pop(45)

    # Chain verification must immediately fail with zero-drop violation
    is_valid_after_drop, drop_err = audit_chain.verify_chain_integrity()
    assert is_valid_after_drop is False
    assert drop_err is not None
    assert "Broken hash chain" in drop_err
