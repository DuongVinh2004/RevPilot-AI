"""
RevPilot AI — Production Readiness Gate Data Models & Canonical Controls
Specification: docs/24-sre/PRODUCTION-READINESS-GATE.md §1..§11
Conforms to INV-REL-001, INV-AUD-001, AC-P08-001-01, AC-P08-001-02.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.errors import DomainError
from revpilot.shared.temporal import UtcDateTime


class GateControlStatus(str, Enum):
    """Execution and verification status of an individual gate control."""
    PLANNED = "PLANNED"
    NOT_EXECUTED = "NOT_EXECUTED"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"
    EVIDENCED = "EVIDENCED"
    PASS = "PASS"


class GateVerdict(str, Enum):
    """Composite release determination verdict."""
    PRODUCTION_READY = "PRODUCTION_READY"
    PRODUCTION_BLOCKED = "PRODUCTION_BLOCKED"
    PASS = "PASS"
    BLOCKED = "BLOCKED"


# --- Error Hierarchy ---

class GateControlFailedError(DomainError):
    """Check fails validation (Status 500, Non-retryable, INV-REL-001)."""

    def __init__(
        self,
        message: str = "Production control failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="GATE_CONTROL_FAILED",
            message=message,
            details=details,
            retryable=False,
        )
        self.status_code = 500


class EvidenceDigestMismatchError(DomainError):
    """Artifact SHA-256 altered, indicating evidence tampering (Status 422, Non-retryable)."""

    def __init__(
        self,
        message: str = "Evidence tampering detected",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="EVIDENCE_DIGEST_MISMATCH",
            message=message,
            details=details,
            retryable=False,
        )
        self.status_code = 422


class IncompleteEvaluationError(DomainError):
    """Control missing required result or evaluation incomplete (Status 422, Non-retryable)."""

    def __init__(
        self,
        message: str = "Not all controls evaluated",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="INCOMPLETE_EVALUATION",
            message=message,
            details=details,
            retryable=False,
        )
        self.status_code = 422


# --- Data Models ---

class EvidenceItem(BaseModel):
    """Cryptographically verifiable evidence artifact associated with a gate control."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    artifact_path: str
    sha256_digest: str
    size_bytes: int
    collected_at: UtcDateTime
    collector_principal: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_path": self.artifact_path,
            "sha256_digest": self.sha256_digest,
            "size_bytes": self.size_bytes,
            "collected_at": self.collected_at.isoformat(),
            "collector_principal": self.collector_principal,
            "metadata": self.metadata,
        }


class GateControlDefinition(BaseModel):
    """Specification of an immutable canonical production readiness control."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    control_id: str
    domain: str
    target_requirement: str
    description: str
    required_evidence_artifact: str
    owner_role: str
    validation_method: str
    default_status: GateControlStatus = GateControlStatus.PLANNED
    blocking_impact: str
    exit_condition: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id,
            "domain": self.domain,
            "target_requirement": self.target_requirement,
            "description": self.description,
            "required_evidence_artifact": self.required_evidence_artifact,
            "owner_role": self.owner_role,
            "validation_method": self.validation_method,
            "default_status": self.default_status.value,
            "blocking_impact": self.blocking_impact,
            "exit_condition": self.exit_condition,
        }


class GateControlResult(BaseModel):
    """Evaluation result for an individual readiness gate control."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    control_id: str
    status: GateControlStatus
    evaluated_at: UtcDateTime
    evaluator_principal: str
    evidence: EvidenceItem | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id,
            "status": self.status.value,
            "evaluated_at": self.evaluated_at.isoformat(),
            "evaluator_principal": self.evaluator_principal,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "message": self.message,
        }


class ReadinessGateManifest(BaseModel):
    """
    Authoritative, cryptographically sealed production readiness gate manifest.
    Conforms to AC-P08-001-01 and AC-P08-001-02.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    manifest_id: str
    version: str = "1.0.0"
    generated_at: UtcDateTime
    evaluator_principal: str
    total_controls: int
    passed_controls: int
    blocked_controls: int
    controls: dict[str, GateControlResult]
    manifest_hash: str
    signature: str
    verdict: GateVerdict

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "version": self.version,
            "generated_at": self.generated_at.isoformat(),
            "evaluator_principal": self.evaluator_principal,
            "total_controls": self.total_controls,
            "passed_controls": self.passed_controls,
            "blocked_controls": self.blocked_controls,
            "controls": {cid: r.to_dict() for cid, r in sorted(self.controls.items())},
            "manifest_hash": self.manifest_hash,
            "signature": self.signature,
            "verdict": self.verdict.value,
        }


# --- Canonical 31 Gate Controls (PRODUCTION-READINESS-GATE.md §9) ---

CANONICAL_GATE_CONTROLS: dict[str, GateControlDefinition] = {
    "PRG-TEN-01": GateControlDefinition(
        control_id="PRG-TEN-01",
        domain="Tenancy",
        target_requirement="INV-TEN-001, NFR-TEN-001",
        description="Hard PostgreSQL RLS & Schema Isolation",
        required_evidence_artifact="Cross-tenant negative suite log (TEST-TEN-001..011)",
        owner_role="Tenancy Lead",
        validation_method="Adversarial automated SQL injection probe",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="CRITICAL (Halts Release)",
        exit_condition="0 rows leaked across 100,000 synthetic queries",
    ),
    "PRG-TEN-02": GateControlDefinition(
        control_id="PRG-TEN-02",
        domain="Tenancy",
        target_requirement="INV-TEN-002",
        description="Server-derived tenant context binding",
        required_evidence_artifact="Middleware token claim verification test report",
        owner_role="IAM Lead",
        validation_method="Header spoofing negative test suite",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="CRITICAL",
        exit_condition="100% rejection of X-Tenant-ID overrides",
    ),
    "PRG-IAM-01": GateControlDefinition(
        control_id="PRG-IAM-01",
        domain="Identity",
        target_requirement="INV-IAM-001, NFR-SEC-001",
        description="OIDC PKCE & JWKS Key Rotation",
        required_evidence_artifact="Cryptographic test log with key rollover",
        owner_role="Security Lead",
        validation_method="Automated IdP key rollover emulation",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="Zero downtime on rotation; 100% signature verify",
    ),
    "PRG-IAM-02": GateControlDefinition(
        control_id="PRG-IAM-02",
        domain="Identity",
        target_requirement="INV-IAM-002",
        description="Scoped Agent Delegation Token TTL <= 24h",
        required_evidence_artifact="Token expiry and privilege escalation test run",
        owner_role="Security Lead",
        validation_method="Adversarial agent privilege escalation test",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="CRITICAL",
        exit_condition="Agents strictly barred from exceeding delegator role",
    ),
    "PRG-SEC-01": GateControlDefinition(
        control_id="PRG-SEC-01",
        domain="Secrets",
        target_requirement="INV-SEC-001, NFR-SEC-002",
        description="Credential Broker ephemeral scoping",
        required_evidence_artifact="Memory dump & log scanner report",
        owner_role="Security Lead",
        validation_method="Automated entropy/credential regex scanner",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="CRITICAL",
        exit_condition="0 secrets found in logs, prompts, or workflows",
    ),
    "PRG-SEC-02": GateControlDefinition(
        control_id="PRG-SEC-02",
        domain="Secrets",
        target_requirement="ADR-0009",
        description="Secret service outage fail-closed behavior",
        required_evidence_artifact="Chaos fault injection test report",
        owner_role="SRE Lead",
        validation_method="Secret store socket blackhole emulation",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="100% external mutations blocked upon outage",
    ),
    "PRG-CON-01": GateControlDefinition(
        control_id="PRG-CON-01",
        domain="Connectors",
        target_requirement="INV-SEC-003, FR-ACT-001",
        description="Connector egress read-only barrier",
        required_evidence_artifact="Egress proxy firewall policy audit",
        owner_role="Integrations Lead",
        validation_method="Direct socket connection attempt test",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="CRITICAL",
        exit_condition="100% outbound mutations outside Tool Gateway blocked",
    ),
    "PRG-CON-02": GateControlDefinition(
        control_id="PRG-CON-02",
        domain="Connectors",
        target_requirement="INV-DATA-002",
        description="Webhook HMAC verification & anti-replay",
        required_evidence_artifact="Webhook replay test suite manifest",
        owner_role="Integrations Lead",
        validation_method="Replay of 1,000 recorded webhook payloads",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="100% duplicate/tampered events rejected",
    ),
    "PRG-CON-03": GateControlDefinition(
        control_id="PRG-CON-03",
        domain="Connectors",
        target_requirement="INV-DATA-002",
        description="Schema drift quarantine & alerting",
        required_evidence_artifact="Schema drift injection test output",
        owner_role="Data Lead",
        validation_method="Injection of altered payload columns",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="Breaking schemas diverted to quarantine; 0 corruption",
    ),
    "PRG-WF-01": GateControlDefinition(
        control_id="PRG-WF-01",
        domain="Workflows",
        target_requirement="INV-WF-001, NFR-DUR-001",
        description="Temporal Saga crash recovery & replay",
        required_evidence_artifact="Worker kill/restart test execution log",
        owner_role="SRE Lead",
        validation_method="SIGKILL worker injection during active Saga",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="CRITICAL",
        exit_condition="100% workflows resume from history; 0 duplicate tasks",
    ),
    "PRG-WF-02": GateControlDefinition(
        control_id="PRG-WF-02",
        domain="Workflows",
        target_requirement="INV-WF-002",
        description="Deterministic workflow compensation",
        required_evidence_artifact="Saga compensation execution ledger",
        owner_role="Architecture Lead",
        validation_method="Simulated step failure in multi-step action",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="Prior actions compensated in reverse order",
    ),
    "PRG-ACT-01": GateControlDefinition(
        control_id="PRG-ACT-01",
        domain="Approval",
        target_requirement="INV-ACT-002, AC-008",
        description="Cryptographic approval digest binding",
        required_evidence_artifact="SHA-256 payload tampering test report",
        owner_role="Security Lead",
        validation_method="Modified payload dispatch verification",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="CRITICAL",
        exit_condition="Digest mismatch rejects action dispatch",
    ),
    "PRG-ACT-02": GateControlDefinition(
        control_id="PRG-ACT-02",
        domain="Approval",
        target_requirement="INV-ACT-003",
        description="Agent self-approval strict block",
        required_evidence_artifact="Negative test run with agent identity",
        owner_role="IAM Lead",
        validation_method="Agent principal signing attempt",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="CRITICAL",
        exit_condition="100% agent approval attempts blocked with 403",
    ),
    "PRG-ACT-03": GateControlDefinition(
        control_id="PRG-ACT-03",
        domain="Approval",
        target_requirement="INV-ACT-004",
        description="Immutable Action Ledger progression",
        required_evidence_artifact="Ledger audit trail checksum dump",
        owner_role="Audit Lead",
        validation_method="Read-only verification of ledger rows",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="Append-only ledger; zero mutating updates",
    ),
    "PRG-AUD-01": GateControlDefinition(
        control_id="PRG-AUD-01",
        domain="Audit",
        target_requirement="INV-AUD-001, NFR-AUD-001",
        description="100% Unsampled security audit logging",
        required_evidence_artifact="Audit event stream parity verification",
        owner_role="Audit Lead",
        validation_method="Automated event count reconciliation",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="Zero dropped audit records; hash chain intact",
    ),
    "PRG-AUD-02": GateControlDefinition(
        control_id="PRG-AUD-02",
        domain="Audit",
        target_requirement="INV-AUD-002, INV-PRV-001",
        description="PII and secret stripping from audit",
        required_evidence_artifact="DLP scan report over 50,000 audit rows",
        owner_role="Privacy Lead",
        validation_method="Automated pattern and PII validator",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="0 PII or secret instances in audit payloads",
    ),
    "PRG-EVD-01": GateControlDefinition(
        control_id="PRG-EVD-01",
        domain="Lineage",
        target_requirement="INV-EVD-001, AC-005",
        description="End-to-end evidence citation provenance",
        required_evidence_artifact="Investigation citation audit report",
        owner_role="AI Lead",
        validation_method="Automated citation accuracy benchmark",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="100% claims linked to valid evidence spans",
    ),
    "PRG-DAT-01": GateControlDefinition(
        control_id="PRG-DAT-01",
        domain="Data Gov",
        target_requirement="INV-DATA-001",
        description="Temporal anti-leakage (:as_of_time)",
        required_evidence_artifact="Temporal boundary unit & query test",
        owner_role="Data Lead",
        validation_method="Future-dated record query test",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="CRITICAL",
        exit_condition="Zero future-dated records consumed",
    ),
    "PRG-DAT-02": GateControlDefinition(
        control_id="PRG-DAT-02",
        domain="Data Gov",
        target_requirement="FR-CTL-003",
        description="Irreversible tenant deletion cascade",
        required_evidence_artifact="Cascade deletion verification probe",
        owner_role="Data Lead",
        validation_method="Post-deletion multi-store query probe",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="Zero residual records across all 10 datastores",
    ),
    "PRG-DAT-03": GateControlDefinition(
        control_id="PRG-DAT-03",
        domain="Data Gov",
        target_requirement="FR-CTL-003",
        description="Legal hold deletion blockage",
        required_evidence_artifact="Legal hold negative test execution",
        owner_role="Legal Lead",
        validation_method="Deletion request on hold-locked tenant",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="CRITICAL",
        exit_condition="100% deletion requests rejected with 409 Conflict",
    ),
    "PRG-OBS-01": GateControlDefinition(
        control_id="PRG-OBS-01",
        domain="Observability",
        target_requirement="NFR-OBS-001",
        description="End-to-end correlation ID propagation",
        required_evidence_artifact="Distributed trace span continuity log",
        owner_role="SRE Lead",
        validation_method="Trace ID propagation verification suite",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="MEDIUM",
        exit_condition="100% trace spans carry tenant and correlation IDs",
    ),
    "PRG-OBS-02": GateControlDefinition(
        control_id="PRG-OBS-02",
        domain="Observability",
        target_requirement="NFR-OBS-002",
        description="Zero-sampling for security/audit telemetry",
        required_evidence_artifact="OTel Collector pipeline configuration audit",
        owner_role="SRE Lead",
        validation_method="Pipeline load test with dropped-event counter",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="Zero dropped spans for high-priority routes",
    ),
    "PRG-SRE-01": GateControlDefinition(
        control_id="PRG-SRE-01",
        domain="SRE",
        target_requirement="NFR-AVL-001, NFR-LAT-001",
        description="API availability >= 99.9% under soak; synchronous API p95 < 500ms",
        required_evidence_artifact="72-hour synthetic soak test dashboard plus 30-day SLI",
        owner_role="SRE Lead",
        validation_method="Continuous synthetic traffic runner",
        default_status=GateControlStatus.NOT_EXECUTED,
        blocking_impact="HIGH",
        exit_condition="Measured uptime >= 99.9%, p95 latency < 500ms",
    ),
    "PRG-SRE-02": GateControlDefinition(
        control_id="PRG-SRE-02",
        domain="SRE",
        target_requirement="INV-REL-001",
        description="Fail-closed kill switches (< 500ms)",
        required_evidence_artifact="Kill-switch propagation latency benchmark",
        owner_role="SRE Lead",
        validation_method="Cluster-wide kill-switch trigger test",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="CRITICAL",
        exit_condition="All tool executions halt within 500ms",
    ),
    "PRG-DR-01": GateControlDefinition(
        control_id="PRG-DR-01",
        domain="Recovery",
        target_requirement="NFR-REC-001",
        description="Target RPO <= 5m, RTO <= 30m",
        required_evidence_artifact="Staging DR exercise report (REH-P07-04)",
        owner_role="SRE Lead",
        validation_method="Cold restore into isolated staging target",
        default_status=GateControlStatus.NOT_EXECUTED,
        blocking_impact="HIGH",
        exit_condition="Measured RPO <= 5m, RTO <= 30m",
    ),
    "PRG-FIN-01": GateControlDefinition(
        control_id="PRG-FIN-01",
        domain="FinOps",
        target_requirement="INV-COST-001, NFR-COST-001",
        description="Atomic spend reservation (zero overspend)",
        required_evidence_artifact="500-thread concurrent spend race test",
        owner_role="FinOps Lead",
        validation_method="Thread contention load test script",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="Zero over-allocation beyond hard budget",
    ),
    "PRG-FIN-02": GateControlDefinition(
        control_id="PRG-FIN-02",
        domain="FinOps",
        target_requirement="NFR-COST-002",
        description="Usage attribution precision >= 99.5%",
        required_evidence_artifact="Daily billing reconciliation report",
        owner_role="FinOps Lead",
        validation_method="Provider bill vs internal usage ledger diff",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="MEDIUM",
        exit_condition="Attribution reconciliation variance < 0.5%",
    ),
    "PRG-AI-01": GateControlDefinition(
        control_id="PRG-AI-01",
        domain="AI Quality",
        target_requirement="NFR-AI-001, AC-011",
        description="Immutable artifact versioning",
        required_evidence_artifact="Model/Prompt registry integrity manifest",
        owner_role="AI Lead",
        validation_method="Hash validation against golden artifact store",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="100% models/prompts pinned to digest",
    ),
    "PRG-AI-02": GateControlDefinition(
        control_id="PRG-AI-02",
        domain="AI Quality",
        target_requirement="NFR-AI-002..007",
        description="Golden test set regression & safety gates",
        required_evidence_artifact="Golden set evaluation benchmark run",
        owner_role="AI Lead",
        validation_method="Automated benchmark suite execution",
        default_status=GateControlStatus.NOT_EXECUTED,
        blocking_impact="HIGH",
        exit_condition="Uplift, calibration, and safety pass baseline",
    ),
    "PRG-REL-01": GateControlDefinition(
        control_id="PRG-REL-01",
        domain="Release",
        target_requirement="ADR-0008",
        description="Automated canary & multi-tier rollback",
        required_evidence_artifact="Staging canary deploy & rollback run",
        owner_role="Release Lead",
        validation_method="Canary rollback trigger test script",
        default_status=GateControlStatus.PLANNED,
        blocking_impact="HIGH",
        exit_condition="Zero-downtime rollback; 0 schema conflict",
    ),
    "PRG-INC-01": GateControlDefinition(
        control_id="PRG-INC-01",
        domain="Ops",
        target_requirement="INV-REL-002",
        description="On-call rotation & paging runbook tested",
        required_evidence_artifact="Mock P0 incident paging drill report",
        owner_role="SRE Lead",
        validation_method="Simulated production P0 paging drill",
        default_status=GateControlStatus.NOT_EXECUTED,
        blocking_impact="HIGH",
        exit_condition="Pager escalation acknowledged within 15 minutes",
    ),
}
