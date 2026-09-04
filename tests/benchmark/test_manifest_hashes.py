"""
RevPilot AI — Benchmark Manifest Hashes and Multi-Tenant Isolation Tests (Phase 01)
Verifies SYNTHETIC-DATASET-SPEC.md §3.2, §4, AC-P01-003-03, and AC-P01-003-04.
"""

from __future__ import annotations
import re
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.modules.benchmark import (
    DatasetProfile,
    GeneratorConfig,
    SyntheticDataGenerator,
    BenchmarkManifest,
)

_SHA256_HEX_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")


@pytest.fixture(scope="module")
def generated_bundle():
    config = GeneratorConfig(
        profile=DatasetProfile.DEVELOPMENT,
        seed=42,
        duration_days=14,
        tenants=[TenantId("tnt_alpha"), TenantId("tnt_beta")],
    )
    gen = SyntheticDataGenerator(config)
    return gen.generate()


def test_zero_cross_tenant_references(generated_bundle):
    """
    AC-P01-003-03: 0 cross-tenant references exist between ten_alpha and ten_beta.
    """
    bundle = generated_bundle

    alpha_customers = {c.id for c in bundle.customers if c.tenant_id == TenantId("tnt_alpha")}
    beta_customers = {c.id for c in bundle.customers if c.tenant_id == TenantId("tnt_beta")}
    assert alpha_customers.isdisjoint(beta_customers)

    alpha_orders = {o.id for o in bundle.orders if o.tenant_id == TenantId("tnt_alpha")}
    beta_orders = {o.id for o in bundle.orders if o.tenant_id == TenantId("tnt_beta")}
    assert alpha_orders.isdisjoint(beta_orders)

    alpha_contracts = {c.id for c in bundle.contracts if c.tenant_id == TenantId("tnt_alpha")}
    beta_contracts = {c.id for c in bundle.contracts if c.tenant_id == TenantId("tnt_beta")}
    assert alpha_contracts.isdisjoint(beta_contracts)

    # Orders must reference own tenant customers
    for o in bundle.orders:
        if o.tenant_id == TenantId("tnt_alpha"):
            assert o.customer_id in alpha_customers
            assert o.customer_id not in beta_customers
        elif o.tenant_id == TenantId("tnt_beta"):
            assert o.customer_id in beta_customers
            assert o.customer_id not in alpha_customers

    # Order lines must reference own tenant orders
    for ol in bundle.order_lines:
        if ol.tenant_id == TenantId("tnt_alpha"):
            assert ol.order_id in alpha_orders
            assert ol.order_id not in beta_orders
        elif ol.tenant_id == TenantId("tnt_beta"):
            assert ol.order_id in beta_orders
            assert ol.order_id not in alpha_orders

    # Shipments must reference own tenant orders
    for s in bundle.shipments:
        if s.tenant_id == TenantId("tnt_alpha"):
            assert s.order_id in alpha_orders
            assert s.order_id not in beta_orders
        elif s.tenant_id == TenantId("tnt_beta"):
            assert s.order_id in beta_orders
            assert s.order_id not in alpha_orders

    # Support tickets must reference own tenant customers/orders
    for t in bundle.support_tickets:
        if t.tenant_id == TenantId("tnt_alpha"):
            assert t.customer_id in alpha_customers
            assert t.customer_id not in beta_customers
            if t.order_id:
                assert t.order_id in alpha_orders
        elif t.tenant_id == TenantId("tnt_beta"):
            assert t.customer_id in beta_customers
            assert t.customer_id not in alpha_customers
            if t.order_id:
                assert t.order_id in beta_orders

    # Contracts must reference own tenant customers
    for ctr in bundle.contracts:
        if ctr.tenant_id == TenantId("tnt_alpha"):
            assert ctr.customer_id in alpha_customers
        elif ctr.tenant_id == TenantId("tnt_beta"):
            assert ctr.customer_id in beta_customers

    # Contract clauses must reference own tenant contracts
    for cl in bundle.contract_clauses:
        if cl.tenant_id == TenantId("tnt_alpha"):
            assert cl.contract_id in alpha_contracts
        elif cl.tenant_id == TenantId("tnt_beta"):
            assert cl.contract_id in beta_contracts

    # Payments must reference own tenant orders
    for p in bundle.payment_references:
        if p.tenant_id == TenantId("tnt_alpha"):
            assert p.order_id in alpha_orders
        elif p.tenant_id == TenantId("tnt_beta"):
            assert p.order_id in beta_orders


def test_manifest_artifact_hashes_valid_format(generated_bundle):
    """
    AC-P01-003-04: Generated manifest contains valid SHA-256 strings for all artifacts.
    """
    manifest = generated_bundle.build_manifest()

    expected_artifacts = {
        "customers_json",
        "orders_json",
        "order_lines_json",
        "shipments_json",
        "support_tickets_json",
        "maintenance_events_json",
        "contracts_json",
        "contract_clauses_json",
        "payment_references_json",
    }
    assert expected_artifacts.issubset(set(manifest.artifact_hashes.keys()))

    for artifact_name, hash_val in manifest.artifact_hashes.items():
        assert _SHA256_HEX_PATTERN.match(hash_val), f"Invalid hash format for {artifact_name}: {hash_val}"


def test_manifest_serialization_round_trip(generated_bundle):
    """Verify BenchmarkManifest serializes to dict and JSON and reconstructs losslessly."""
    manifest = generated_bundle.build_manifest()

    # to_dict / from_dict
    m_dict = manifest.to_dict()
    assert m_dict["profile"] == "DEVELOPMENT"
    assert m_dict["seed"] == 42
    reconstructed = BenchmarkManifest.from_dict(m_dict)
    assert reconstructed == manifest

    # to_json / from_json
    json_str = manifest.to_json()
    assert "artifact_hashes" in json_str
    reconstructed_json = BenchmarkManifest.from_json(json_str)
    assert reconstructed_json == manifest


def test_no_ground_truth_leakage_in_identifiers(generated_bundle):
    """INV-DATA-001: Entity primary keys and names must not leak scenario words."""
    forbidden_tokens = ["incident", "truck_delay", "ground_truth", "root_cause"]
    for o in generated_bundle.orders:
        for token in forbidden_tokens:
            assert token not in o.id.lower()
            assert token not in o.order_number.lower()

    for s in generated_bundle.shipments:
        for token in forbidden_tokens:
            assert token not in s.id.lower()
            assert token not in s.tracking_number.lower()

    for c in generated_bundle.customers:
        for token in forbidden_tokens:
            assert token not in c.id.lower()
            assert token not in c.email.lower()
