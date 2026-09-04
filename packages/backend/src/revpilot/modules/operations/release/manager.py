"""
RevPilot AI — 13-Tier Release Governance & Manifest Manager
Specification: docs/30-deployment/RELEASE-CANARY-ROLLBACK-SPEC.md §5, §6
Conforms to ADR-0008, INV-REL-001, AC-011, AC-P08-003-01.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.errors import DomainError
from revpilot.shared.temporal import UtcDateTime

# --- Error Hierarchy ---

class IncompleteTierManifestError(DomainError):
    """Missing or empty version tag across T01..T13 artifact tiers (Status 422, Non-retryable)."""

    def __init__(
        self,
        message: str = "Incomplete artifact bundle",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="INCOMPLETE_TIER_MANIFEST",
            message=message,
            details=details,
            retryable=False,
        )
        self.status_code = 422


class CanaryHealthFailedError(DomainError):
    """Canary health check breach (5xx spike, latency, crash loops) (Status 500, Non-retryable)."""

    def __init__(
        self,
        message: str = "Canary health check failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="CANARY_HEALTH_FAILED",
            message=message,
            details=details,
            retryable=False,
        )
        self.status_code = 500


class RollbackExecutionError(DomainError):
    """Step execution failure in coordinated multi-tier rollback (Status 500, Retryable)."""

    def __init__(
        self,
        message: str = "Emergency escalation triggered",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="ROLLBACK_EXECUTION_ERROR",
            message=message,
            details=details,
            retryable=True,
        )
        self.status_code = 500


# --- 13 Artifact Tiers Definition (§5) ---

TIER_DEFINITIONS: dict[str, str] = {
    "t01_binary_digest": "T01 Application Binary",
    "t02_api_version": "T02 API Contract",
    "t03_schema_version": "T03 Database Schema",
    "t04_workflow_version": "T04 Workflow Definition",
    "t05_connector_version": "T05 Connector Adapter",
    "t06_prompt_digest": "T06 Prompt Template",
    "t07_model_snapshot": "T07 Foundation Model",
    "t08_embedding_model": "T08 Embedding Model",
    "t09_vector_index_version": "T09 Vector Index Projection",
    "t10_retrieval_config_digest": "T10 Retrieval Config",
    "t11_policy_digest": "T11 Governance Policy",
    "t12_feature_flags_digest": "T12 Feature Flag Manifest",
    "t13_tenant_config_version": "T13 Tenant Configuration",
}


class ReleaseManifest(BaseModel):
    """
    Immutable release bundle manifest encapsulating all 13 artifact tiers (AC-011).
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    bundle_id: str
    t01_binary_digest: str
    t02_api_version: str
    t03_schema_version: str
    t04_workflow_version: str
    t05_connector_version: str
    t06_prompt_digest: str
    t07_model_snapshot: str
    t08_embedding_model: str
    t09_vector_index_version: str
    t10_retrieval_config_digest: str
    t11_policy_digest: str
    t12_feature_flags_digest: str
    t13_tenant_config_version: str
    created_at: UtcDateTime = Field(default_factory=UtcDateTime.now)
    created_by: str = "release-lead"
    status: str = "QUALIFIED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "t01_binary_digest": self.t01_binary_digest,
            "t02_api_version": self.t02_api_version,
            "t03_schema_version": self.t03_schema_version,
            "t04_workflow_version": self.t04_workflow_version,
            "t05_connector_version": self.t05_connector_version,
            "t06_prompt_digest": self.t06_prompt_digest,
            "t07_model_snapshot": self.t07_model_snapshot,
            "t08_embedding_model": self.t08_embedding_model,
            "t09_vector_index_version": self.t09_vector_index_version,
            "t10_retrieval_config_digest": self.t10_retrieval_config_digest,
            "t11_policy_digest": self.t11_policy_digest,
            "t12_feature_flags_digest": self.t12_feature_flags_digest,
            "t13_tenant_config_version": self.t13_tenant_config_version,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status,
        }


class ReleaseManifestValidator:
    """
    Validates release bundles against the 13 required artifact tiers.
    Rejects bundles with missing or empty tiers (AC-P08-003-01).
    """

    @classmethod
    def validate(cls, manifest_data: ReleaseManifest | dict[str, Any]) -> ReleaseManifest:
        """
        Validate that every tier T01..T13 is present and non-empty.
        """
        if isinstance(manifest_data, dict):
            # Check bundle_id
            if not manifest_data.get("bundle_id") or not str(manifest_data["bundle_id"]).strip():
                raise IncompleteTierManifestError(
                    "Incomplete artifact bundle: missing bundle_id",
                    details={"missing_field": "bundle_id"},
                )

            # Check all 13 tiers
            for tier_key, tier_desc in TIER_DEFINITIONS.items():
                val = manifest_data.get(tier_key)
                if val is None or not str(val).strip():
                    raise IncompleteTierManifestError(
                        f"Incomplete artifact bundle: missing or empty tier '{tier_key}' ({tier_desc})",
                        details={"missing_tier": tier_key, "tier_desc": tier_desc},
                    )

            manifest = ReleaseManifest(**manifest_data)
        elif isinstance(manifest_data, ReleaseManifest):
            manifest = manifest_data
            for tier_key, tier_desc in TIER_DEFINITIONS.items():
                val = getattr(manifest, tier_key, None)
                if val is None or not str(val).strip():
                    raise IncompleteTierManifestError(
                        f"Incomplete artifact bundle: missing or empty tier '{tier_key}' ({tier_desc})",
                        details={"missing_tier": tier_key, "tier_desc": tier_desc},
                    )
        else:
            raise IncompleteTierManifestError(
                f"Invalid manifest data type: {type(manifest_data).__name__}",
                details={"provided_type": type(manifest_data).__name__},
            )

        return manifest


class ReleaseRegistry:
    """
    Registry for qualified, active, and quarantined release manifests.
    """

    def __init__(self) -> None:
        self._bundles: dict[str, ReleaseManifest] = {}
        self._quarantine_reasons: dict[str, str] = {}

    def register_bundle(self, manifest_data: ReleaseManifest | dict[str, Any]) -> ReleaseManifest:
        """Validate and register a release bundle."""
        manifest = ReleaseManifestValidator.validate(manifest_data)
        self._bundles[manifest.bundle_id] = manifest
        return manifest

    def get_bundle(self, bundle_id: str) -> ReleaseManifest | None:
        return self._bundles.get(bundle_id)

    def quarantine_bundle(self, bundle_id: str, reason: str) -> None:
        """Mark a failed release bundle as QUARANTINED (§9.3)."""
        if bundle_id in self._bundles:
            bundle = self._bundles[bundle_id]
            # Create updated manifest with QUARANTINED status
            updated = bundle.model_copy(update={"status": "QUARANTINED"})
            self._bundles[bundle_id] = updated
        self._quarantine_reasons[bundle_id] = reason

    def is_quarantined(self, bundle_id: str) -> bool:
        bundle = self._bundles.get(bundle_id)
        return bool(bundle and bundle.status == "QUARANTINED")

    def get_quarantine_reason(self, bundle_id: str) -> str | None:
        return self._quarantine_reasons.get(bundle_id)
