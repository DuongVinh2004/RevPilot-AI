"""
RevPilot AI — Seed Reproducibility and Sizing Unit Tests (Phase 01)
Verifies SYNTHETIC-DATASET-SPEC.md §3.1, AC-P01-003-01, and AC-P01-003-02.
"""

from __future__ import annotations
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.benchmark import (
    DatasetProfile,
    GeneratorConfig,
    SyntheticDataGenerator,
    ConfigValidationError,
)


def test_seed_reproducibility_identical_hashes():
    """
    AC-P01-003-01: Running generator twice with seed 42 produces
    identical SHA-256 hashes for all output entities.
    """
    config1 = GeneratorConfig(
        profile=DatasetProfile.DEVELOPMENT,
        seed=42,
        duration_days=14,
        tenants=[TenantId("tnt_alpha"), TenantId("tnt_beta")],
    )
    gen1 = SyntheticDataGenerator(config1)
    bundle1 = gen1.generate()
    manifest1 = bundle1.build_manifest()

    config2 = GeneratorConfig(
        profile=DatasetProfile.DEVELOPMENT,
        seed=42,
        duration_days=14,
        tenants=[TenantId("tnt_alpha"), TenantId("tnt_beta")],
    )
    gen2 = SyntheticDataGenerator(config2)
    bundle2 = gen2.generate()
    manifest2 = bundle2.build_manifest()

    # Assert exact match of all artifact hashes
    assert manifest1.artifact_hashes == manifest2.artifact_hashes
    for key, hash1 in manifest1.artifact_hashes.items():
        assert hash1 == manifest2.artifact_hashes[key]
        assert hash1.startswith("sha256:")

    # Assert exact equality of manifest IDs and entity counts
    assert manifest1.manifest_id == manifest2.manifest_id
    assert manifest1.entity_counts == manifest2.entity_counts


def test_different_seeds_produce_divergent_hashes():
    """Distinct seeds produce different random sequences and different artifact hashes."""
    gen_a = SyntheticDataGenerator(GeneratorConfig(seed=42))
    bundle_a = gen_a.generate()
    manifest_a = bundle_a.build_manifest()

    gen_b = SyntheticDataGenerator(GeneratorConfig(seed=43))
    bundle_b = gen_b.generate()
    manifest_b = bundle_b.build_manifest()

    assert manifest_a.artifact_hashes != manifest_b.artifact_hashes
    assert manifest_a.artifact_hashes["orders_json"] != manifest_b.artifact_hashes["orders_json"]


def test_development_profile_exact_entity_counts():
    """
    AC-P01-003-02: Generated dataset contains exactly the required entity counts
    for DEVELOPMENT profile (1,000 orders).
    """
    config = GeneratorConfig(
        profile=DatasetProfile.DEVELOPMENT,
        seed=42,
        duration_days=14,
    )
    gen = SyntheticDataGenerator(config)
    bundle = gen.generate()

    assert len(bundle.orders) == 1000
    assert len(bundle.customers) == 200
    assert len(bundle.order_lines) == 2400
    assert len(bundle.shipments) == 1020
    assert len(bundle.support_tickets) == 100
    assert len(bundle.maintenance_events) == 14
    assert len(bundle.contracts) == 40
    assert len(bundle.contract_clauses) == 40
    assert len(bundle.payment_references) == 1040


@pytest.mark.parametrize("invalid_kwargs", [
    {"seed": "not_an_int"},
    {"duration_days": 0},
    {"duration_days": -5},
    {"tenants": []},
])
def test_generator_config_validation_errors(invalid_kwargs):
    """GeneratorConfig rejects invalid parameters with ConfigValidationError."""
    with pytest.raises(ConfigValidationError):
        GeneratorConfig(**invalid_kwargs)
