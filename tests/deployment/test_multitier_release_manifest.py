"""
RevPilot AI — Tests: 13-Tier Release Manifest Validation
Specification: docs/30-deployment/RELEASE-CANARY-ROLLBACK-SPEC.md §5
Conforms to ADR-0008, AC-011, AC-P08-003-01.
"""

from __future__ import annotations

import pytest

from revpilot.modules.operations.release import (
    IncompleteTierManifestError,
    ReleaseManifest,
    ReleaseManifestValidator,
    ReleaseRegistry,
    TIER_DEFINITIONS,
)


def _get_valid_manifest_dict() -> dict[str, str]:
    return {
        "bundle_id": "bundle_prod_20260904_rc1",
        "t01_binary_digest": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "t02_api_version": "v1.4.0",
        "t03_schema_version": "20260904_v08",
        "t04_workflow_version": "investigation_saga_v2",
        "t05_connector_version": "salesforce_v2.1.0",
        "t06_prompt_digest": "pr_sha256:8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
        "t07_model_snapshot": "claude-3-5-sonnet-20241022",
        "t08_embedding_model": "text-embedding-3-small-1536d",
        "t09_vector_index_version": "vec_v2_1536d",
        "t10_retrieval_config_digest": "rag_sha256:3b6a27bc19a8616ef9c2d1b5a593361e2fbe3a9e224e756c9a334860b7fc61ad",
        "t11_policy_digest": "pol_sha256:4d872c8466b0f0a4f5298a28e3b1c6d1d4e8c7c9a4c8a2b1d5e7a9b0c2e4f6a8",
        "t12_feature_flags_digest": "ff_sha256:7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b",
        "t13_tenant_config_version": "tenant_schema_v2",
    }


def test_valid_13_tier_manifest_passes_validation():
    """
    AC-P08-003-01: Bundle with all 13 tiers present and non-empty passes validation.
    """
    data = _get_valid_manifest_dict()
    manifest = ReleaseManifestValidator.validate(data)

    assert manifest.bundle_id == "bundle_prod_20260904_rc1"
    assert manifest.t01_binary_digest.startswith("sha256:")
    assert manifest.t02_api_version == "v1.4.0"
    assert manifest.t03_schema_version == "20260904_v08"
    assert manifest.t04_workflow_version == "investigation_saga_v2"
    assert manifest.t05_connector_version == "salesforce_v2.1.0"
    assert manifest.t06_prompt_digest.startswith("pr_sha256:")
    assert manifest.t07_model_snapshot == "claude-3-5-sonnet-20241022"
    assert manifest.t08_embedding_model == "text-embedding-3-small-1536d"
    assert manifest.t09_vector_index_version == "vec_v2_1536d"
    assert manifest.t10_retrieval_config_digest.startswith("rag_sha256:")
    assert manifest.t11_policy_digest.startswith("pol_sha256:")
    assert manifest.t12_feature_flags_digest.startswith("ff_sha256:")
    assert manifest.t13_tenant_config_version == "tenant_schema_v2"
    assert manifest.status == "QUALIFIED"


@pytest.mark.parametrize("missing_tier", list(TIER_DEFINITIONS.keys()))
def test_manifest_missing_single_tier_fails_closed(missing_tier: str):
    """
    AC-P08-003-01: Omitting any single tier from T01..T13 raises IncompleteTierManifestError (422).
    """
    data = _get_valid_manifest_dict()
    del data[missing_tier]

    with pytest.raises(IncompleteTierManifestError) as exc_info:
        ReleaseManifestValidator.validate(data)

    assert exc_info.value.code == "INCOMPLETE_TIER_MANIFEST"
    assert exc_info.value.status_code == 422
    assert exc_info.value.details["missing_tier"] == missing_tier


@pytest.mark.parametrize("empty_tier", list(TIER_DEFINITIONS.keys()))
def test_manifest_empty_tier_string_fails_closed(empty_tier: str):
    """
    AC-P08-003-01: An empty or whitespace-only tier value raises IncompleteTierManifestError (422).
    """
    data = _get_valid_manifest_dict()
    data[empty_tier] = "   "

    with pytest.raises(IncompleteTierManifestError) as exc_info:
        ReleaseManifestValidator.validate(data)

    assert exc_info.value.code == "INCOMPLETE_TIER_MANIFEST"
    assert exc_info.value.status_code == 422
    assert exc_info.value.details["missing_tier"] == empty_tier


def test_release_registry_registration_and_quarantine():
    """
    ReleaseRegistry registers valid bundles and marks failed ones as QUARANTINED (§9.3).
    """
    registry = ReleaseRegistry()
    data = _get_valid_manifest_dict()

    manifest = registry.register_bundle(data)
    assert registry.get_bundle(manifest.bundle_id) is not None
    assert registry.is_quarantined(manifest.bundle_id) is False

    # Quarantine bundle
    registry.quarantine_bundle(manifest.bundle_id, reason="5xx spike during Canary 5%")
    assert registry.is_quarantined(manifest.bundle_id) is True
    assert registry.get_quarantine_reason(manifest.bundle_id) == "5xx spike during Canary 5%"
    assert registry.get_bundle(manifest.bundle_id).status == "QUARANTINED"
