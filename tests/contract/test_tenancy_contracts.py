"""
Architectural Contract Tests for Tenancy Module.
Verifies MODULE-BOUNDARIES.md, DEPENDENCY-RULES.md, and MULTI-TENANCY-SPEC.md compliance.
"""

import sys
import inspect
import revpilot.modules.tenancy as tenancy
from revpilot.modules.tenancy import (
    TenantStatus,
    SubscriptionTier,
    Entitlement,
    Organization,
    Tenant,
    TenantQueryPort,
    TenantCommandPort,
    TenantContextPolicy,
    InMemoryTenantRepository,
    TenantService,
)


def test_tenancy_module_public_exports_contract() -> None:
    """Verify tenancy module exports match architectural contract."""
    expected_exports = {
        "TenantStatus",
        "SubscriptionTier",
        "Entitlement",
        "Organization",
        "Tenant",
        "TenantQueryPort",
        "TenantCommandPort",
        "TenantContextPolicy",
        "InMemoryTenantRepository",
        "TenantService",
    }
    actual_exports = set(tenancy.__all__)
    assert expected_exports.issubset(actual_exports), (
        f"Missing expected exports: {expected_exports - actual_exports}"
    )


def test_tenancy_module_dependency_rules_contract() -> None:
    """
    Verify tenancy module obeys DEPENDENCY-RULES.md:
    Allowed dependencies: shared kernel, standard library.
    Forbidden dependencies: business modules, provider SDKs, external frameworks.
    """
    forbidden_modules = [
        "revpilot.modules.investigations",
        "revpilot.modules.actions",
        "revpilot.modules.analytics",
        "revpilot.modules.evidence",
        "revpilot.modules.decisions",
        "revpilot.modules.policy",
        "revpilot.modules.connectors",
        "revpilot.modules.billing",
        "temporalio",
        "langgraph",
        "sqlalchemy",
        "psycopg",
    ]

    for mod_name in forbidden_modules:
        assert mod_name not in sys.modules or not any(
            mod_name in getattr(val, "__module__", "")
            for val in vars(tenancy).values()
        ), f"Tenancy module illegally depends on forbidden module: {mod_name}"


def test_ports_signature_contract() -> None:
    """Verify TenantQueryPort and TenantCommandPort expose all required protocol methods."""
    query_methods = [m for m, _ in inspect.getmembers(TenantQueryPort, predicate=inspect.isfunction)]
    assert "get_by_id" in query_methods
    assert "get_by_organization" in query_methods
    assert "get_organization_by_id" in query_methods
    assert "exists" in query_methods

    cmd_methods = [m for m, _ in inspect.getmembers(TenantCommandPort, predicate=inspect.isfunction)]
    assert "save_tenant" in cmd_methods
    assert "save_organization" in cmd_methods
    assert "update_status" in cmd_methods
