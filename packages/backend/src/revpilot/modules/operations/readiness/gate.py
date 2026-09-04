"""
RevPilot AI — Production Readiness Gate Verification Service
Specification: docs/24-sre/PRODUCTION-READINESS-GATE.md §1..§11
Conforms to INV-REL-001, INV-AUD-001, AC-P08-001-01, AC-P08-001-02.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import stat
from pathlib import Path
from typing import Any
from uuid import uuid4

from revpilot.modules.operations.readiness.models import (
    CANONICAL_GATE_CONTROLS,
    EvidenceDigestMismatchError,
    EvidenceItem,
    GateControlFailedError,
    GateControlResult,
    GateControlStatus,
    GateVerdict,
    IncompleteEvaluationError,
    ReadinessGateManifest,
)
from revpilot.shared.temporal import UtcDateTime

logger = logging.getLogger(__name__)


class ProductionReadinessGateService:
    """
    Automated Production Readiness Gate verification harness.
    Evaluates 31 canonical controls, verifies evidence SHA-256 digests,
    enforces fail-closed evaluation, and issues cryptographically signed manifests.
    """

    def __init__(
        self,
        evaluator_principal: str = "principal:sre-lead",
        audit_emitter: Any | None = None,
    ) -> None:
        self._evaluator_principal = evaluator_principal
        self._audit_emitter = audit_emitter
        self._audit_logs: list[dict[str, Any]] = []
        self._controls: dict[str, GateControlResult] = {}
        self._initialize_canonical_controls()

    def _initialize_canonical_controls(self) -> None:
        """Initialize all 31 canonical controls in their default unverified state."""
        for control_id, definition in CANONICAL_GATE_CONTROLS.items():
            self._controls[control_id] = GateControlResult(
                control_id=control_id,
                status=definition.default_status,
                evaluated_at=UtcDateTime.now(),
                evaluator_principal=self._evaluator_principal,
                evidence=None,
                message=f"Initialized with canonical default status: {definition.default_status.value}",
            )

    def _emit_audit(self, event_type: str, entity_id: str, details: dict[str, Any]) -> None:
        """Record an immutable, unsampled audit event (INV-AUD-001)."""
        event = {
            "event_id": f"aud_prg_{uuid4().hex}",
            "occurred_at": UtcDateTime.now().isoformat(),
            "event_type": event_type,
            "entity_id": entity_id,
            "actor_id": self._evaluator_principal,
            "details": details,
        }
        self._audit_logs.append(event)
        if self._audit_emitter is not None and hasattr(self._audit_emitter, "emit"):
            self._audit_emitter.emit(event)
        logger.info("READINESS_AUDIT: %s for %s: %s", event_type, entity_id, details)

    @property
    def audit_logs(self) -> list[dict[str, Any]]:
        """Return full audit log stream for verification."""
        return list(self._audit_logs)

    def get_control_result(self, control_id: str) -> GateControlResult | None:
        """Retrieve evaluation result for a control."""
        return self._controls.get(control_id)

    def evaluate_control(
        self,
        control_id: str,
        evidence_artifact_path: Path | str,
        expected_digest: str | None = None,
        passed: bool = True,
        message: str = "",
    ) -> GateControlResult:
        """
        Evaluate an individual readiness gate control with empirical evidence artifact.
        Verifies SHA-256 digest, catches tampering, and logs immutable audit record.
        """
        if control_id not in CANONICAL_GATE_CONTROLS:
            raise GateControlFailedError(
                f"Control '{control_id}' is not in CANONICAL_GATE_CONTROLS (PRG-TEN-01..PRG-INC-01)",
                details={"control_id": control_id},
            )

        path = Path(evidence_artifact_path)
        if not path.exists() or not path.is_file():
            self._emit_audit(
                "GATE_CONTROL_ARTIFACT_MISSING",
                control_id,
                {"path": str(path)},
            )
            raise GateControlFailedError(
                f"Evidence artifact not found or invalid: {path}",
                details={"control_id": control_id, "path": str(path)},
            )

        # Read artifact and compute SHA-256 digest
        content = path.read_bytes()
        computed_digest = hashlib.sha256(content).hexdigest()

        # Tamper detection check
        if expected_digest is not None and computed_digest.lower() != expected_digest.lower():
            self._emit_audit(
                "EVIDENCE_TAMPERING_DETECTED",
                control_id,
                {
                    "expected_digest": expected_digest,
                    "computed_digest": computed_digest,
                    "artifact_path": str(path),
                },
            )
            raise EvidenceDigestMismatchError(
                f"Evidence tampering detected for {control_id}: digest mismatch "
                f"(expected={expected_digest}, computed={computed_digest})",
                details={
                    "control_id": control_id,
                    "expected_digest": expected_digest,
                    "computed_digest": computed_digest,
                    "path": str(path),
                },
            )

        evidence_item = EvidenceItem(
            artifact_path=str(path.resolve()),
            sha256_digest=computed_digest,
            size_bytes=len(content),
            collected_at=UtcDateTime.now(),
            collector_principal=self._evaluator_principal,
            metadata={"filename": path.name},
        )

        if not passed:
            result = GateControlResult(
                control_id=control_id,
                status=GateControlStatus.BLOCKED,
                evaluated_at=UtcDateTime.now(),
                evaluator_principal=self._evaluator_principal,
                evidence=evidence_item,
                message=message or "Control validation check failed",
            )
            self._controls[control_id] = result
            self._emit_audit(
                "GATE_CONTROL_FAILED",
                control_id,
                {"status": "BLOCKED", "message": message, "digest": computed_digest},
            )
            raise GateControlFailedError(
                f"Production control {control_id} validation failed: {message}",
                details={"control_id": control_id, "message": message},
            )

        result = GateControlResult(
            control_id=control_id,
            status=GateControlStatus.PASS,
            evaluated_at=UtcDateTime.now(),
            evaluator_principal=self._evaluator_principal,
            evidence=evidence_item,
            message=message or "Control empirically verified and evidenced",
        )
        self._controls[control_id] = result
        self._emit_audit(
            "GATE_CONTROL_EVIDENCED",
            control_id,
            {"status": "PASS", "digest": computed_digest},
        )
        return result

    def get_composite_verdict(self) -> GateVerdict:
        """
        Evaluate composite release readiness verdict (INV-REL-001, AC-P08-001-01).
        Fail-closed: returns PRODUCTION_READY strictly if and only if all 31 canonical controls
        have status == PASS with verified evidence. Otherwise returns PRODUCTION_BLOCKED.
        """
        for control_id in CANONICAL_GATE_CONTROLS.keys():
            result = self._controls.get(control_id)
            if result is None or result.status != GateControlStatus.PASS or result.evidence is None:
                return GateVerdict.PRODUCTION_BLOCKED

        return GateVerdict.PRODUCTION_READY

    def _compute_manifest_hash_and_signature(
        self,
        manifest_id: str,
        evaluator_principal: str,
        total_controls: int,
        passed_controls: int,
        blocked_controls: int,
        verdict: GateVerdict,
        signing_key: str,
    ) -> tuple[str, str]:
        """Compute canonical deterministic hash and HMAC signature over all control states."""
        canonical_data = {
            "manifest_id": manifest_id,
            "version": "1.0.0",
            "evaluator_principal": evaluator_principal,
            "total_controls": total_controls,
            "passed_controls": passed_controls,
            "blocked_controls": blocked_controls,
            "verdict": verdict.value,
            "controls": {
                cid: {
                    "status": self._controls[cid].status.value if cid in self._controls else "UNKNOWN",
                    "sha256": (
                        self._controls[cid].evidence.sha256_digest
                        if (cid in self._controls and self._controls[cid].evidence)
                        else None
                    ),
                    "artifact_path": (
                        self._controls[cid].evidence.artifact_path
                        if (cid in self._controls and self._controls[cid].evidence)
                        else None
                    ),
                }
                for cid in sorted(CANONICAL_GATE_CONTROLS.keys())
            },
        }
        serialized = json.dumps(canonical_data, sort_keys=True).encode("utf-8")
        manifest_hash = hashlib.sha256(serialized).hexdigest()
        signature = hmac.new(
            signing_key.encode("utf-8"),
            manifest_hash.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return manifest_hash, signature

    def generate_gate_manifest(
        self,
        signing_key: str = "revpilot-production-gate-key",
        evaluator_principal: str | None = None,
        require_all_pass: bool = False,
    ) -> ReadinessGateManifest:
        """
        Generate a cryptographically sealed ReadinessGateManifest over all 31 controls.
        Emits immutable audit event with manifest hash (INV-AUD-001).
        """
        evaluator = evaluator_principal or self._evaluator_principal
        total_controls = len(CANONICAL_GATE_CONTROLS)
        passed_controls = sum(
            1
            for cid in CANONICAL_GATE_CONTROLS.keys()
            if (
                self._controls.get(cid)
                and self._controls[cid].status == GateControlStatus.PASS
                and self._controls[cid].evidence is not None
            )
        )
        blocked_controls = total_controls - passed_controls
        verdict = self.get_composite_verdict()

        if require_all_pass and verdict != GateVerdict.PRODUCTION_READY:
            unpassed = [
                cid
                for cid in CANONICAL_GATE_CONTROLS.keys()
                if not (
                    self._controls.get(cid)
                    and self._controls[cid].status == GateControlStatus.PASS
                    and self._controls[cid].evidence is not None
                )
            ]
            self._emit_audit(
                "GATE_MANIFEST_GENERATION_REJECTED",
                "gate_manifest",
                {"unpassed_controls": unpassed, "unpassed_count": len(unpassed)},
            )
            raise IncompleteEvaluationError(
                f"Not all controls evaluated to PASS: {len(unpassed)} remaining unverified",
                details={"unpassed_controls": unpassed},
            )

        manifest_id = f"prg_man_{uuid4().hex}"
        manifest_hash, signature = self._compute_manifest_hash_and_signature(
            manifest_id=manifest_id,
            evaluator_principal=evaluator,
            total_controls=total_controls,
            passed_controls=passed_controls,
            blocked_controls=blocked_controls,
            verdict=verdict,
            signing_key=signing_key,
        )

        manifest = ReadinessGateManifest(
            manifest_id=manifest_id,
            version="1.0.0",
            generated_at=UtcDateTime.now(),
            evaluator_principal=evaluator,
            total_controls=total_controls,
            passed_controls=passed_controls,
            blocked_controls=blocked_controls,
            controls=dict(self._controls),
            manifest_hash=manifest_hash,
            signature=signature,
            verdict=verdict,
        )

        self._emit_audit(
            "GATE_MANIFEST_GENERATED",
            manifest_id,
            {
                "manifest_hash": manifest_hash,
                "signature": signature,
                "verdict": verdict.value,
                "total_controls": total_controls,
                "passed_controls": passed_controls,
                "blocked_controls": blocked_controls,
            },
        )
        return manifest

    def archive_manifest(
        self,
        manifest: ReadinessGateManifest,
        sink_dir: Path | str,
    ) -> Path:
        """
        Archive manifest to an immutable evidence sink file (AC-P08-001-02).
        Enforces read-only persistence permissions and emits audit log.
        """
        sink = Path(sink_dir)
        sink.mkdir(parents=True, exist_ok=True)
        dest_file = sink / f"readiness_gate_manifest_{manifest.manifest_id}.json"

        # Write serialized JSON representation
        data = manifest.to_dict()
        dest_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Set read-only permissions to ensure immutability
        try:
            current_mode = dest_file.stat().st_mode
            dest_file.chmod(current_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        except OSError as e:
            logger.warning("Could not set strict read-only permissions on %s: %s", dest_file, e)

        self._emit_audit(
            "GATE_MANIFEST_ARCHIVED",
            manifest.manifest_id,
            {
                "sink_path": str(dest_file.resolve()),
                "manifest_hash": manifest.manifest_hash,
                "size_bytes": dest_file.stat().st_size,
            },
        )
        return dest_file

    @staticmethod
    def verify_manifest_signature(
        manifest: ReadinessGateManifest,
        signing_key: str,
    ) -> bool:
        """
        Verify that a ReadinessGateManifest signature matches its canonical contents.
        """
        canonical_data = {
            "manifest_id": manifest.manifest_id,
            "version": manifest.version,
            "evaluator_principal": manifest.evaluator_principal,
            "total_controls": manifest.total_controls,
            "passed_controls": manifest.passed_controls,
            "blocked_controls": manifest.blocked_controls,
            "verdict": manifest.verdict.value,
            "controls": {
                cid: {
                    "status": manifest.controls[cid].status.value if cid in manifest.controls else "UNKNOWN",
                    "sha256": (
                        manifest.controls[cid].evidence.sha256_digest
                        if (cid in manifest.controls and manifest.controls[cid].evidence)
                        else None
                    ),
                    "artifact_path": (
                        manifest.controls[cid].evidence.artifact_path
                        if (cid in manifest.controls and manifest.controls[cid].evidence)
                        else None
                    ),
                }
                for cid in sorted(CANONICAL_GATE_CONTROLS.keys())
            },
        }
        serialized = json.dumps(canonical_data, sort_keys=True).encode("utf-8")
        computed_hash = hashlib.sha256(serialized).hexdigest()
        if not hmac.compare_digest(computed_hash, manifest.manifest_hash):
            return False

        expected_sig = hmac.new(
            signing_key.encode("utf-8"),
            computed_hash.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_sig, manifest.signature)
