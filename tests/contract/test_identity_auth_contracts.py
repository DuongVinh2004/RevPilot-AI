"""
RevPilot AI — Architectural Contract Tests for Identity Module (Rail 3).
Verifies MODULE-BOUNDARIES.md, DEPENDENCY-RULES.md, IAM-SPEC.md, and MULTI-TENANCY-SPEC.md compliance.
"""

from __future__ import annotations
import inspect
import sys
from typing import get_type_hints

import revpilot.modules.identity as identity
from revpilot.modules.identity.adapters.in_memory_auth_adapter import InMemoryAuthAdapter
from revpilot.modules.identity.domain.models import (
    AuthTokenClaims,
    Principal,
    PrincipalType,
    PrivilegedContext,
    VerifiedClaimsToken,
    create_principal_from_verified_claims,
)
from revpilot.modules.identity.domain.token_policy import (
    SessionPolicy,
    TokenValidationPolicy,
    VerifiedSessionEvidence,
)
from revpilot.modules.identity.ports.authentication import AuthenticationPort
from revpilot.modules.identity.service import IdentityService
from revpilot.shared.errors import (
    AuthenticationError,
    AuthorizationError,
    TenancyViolationError,
    ValidationError,
)


def test_identity_module_public_exports_contract() -> None:
    """Verify identity module public exports match architectural contract."""
    expected_exports = {
        "Principal",
        "PrincipalType",
        "AuthTokenClaims",
        "VerifiedClaimsToken",
        "PrivilegedContext",
        "create_principal_from_verified_claims",
    }
    actual_exports = set(identity.__all__)
    assert expected_exports.issubset(actual_exports), (
        f"Missing expected exports from revpilot.modules.identity: {expected_exports - actual_exports}"
    )


def test_identity_module_dependency_rules_contract() -> None:
    """
    Verify identity module obeys DEPENDENCY-RULES.md:
    Allowed dependencies: shared kernel, tenancy ports/domain, standard library.
    Forbidden dependencies: business modules, external SDKs, web frameworks.
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
        "fastapi",
        "starlette",
        "boto3",
        "requests",
        "urllib3",
        "httpx",
    ]

    loaded_modules = set(sys.modules.keys())
    for forbidden in forbidden_modules:
        assert forbidden not in loaded_modules, (
            f"DEPENDENCY RULE VIOLATION: Forbidden module '{forbidden}' loaded in test environment"
        )


def test_authentication_port_protocol_contract() -> None:
    """
    Verify AuthenticationPort protocol signature and verified boundary.
    verify_token MUST return VerifiedClaimsToken, never raw Principal.
    """
    assert hasattr(AuthenticationPort, "_is_runtime_protocol")
    assert isinstance(InMemoryAuthAdapter(), AuthenticationPort)

    sig_verify = inspect.signature(AuthenticationPort.verify_token)
    assert "token" in sig_verify.parameters
    assert "expected_issuer" in sig_verify.parameters
    assert "expected_audience" in sig_verify.parameters
    assert "as_of" in sig_verify.parameters

    hints = get_type_hints(AuthenticationPort.verify_token)
    assert hints.get("return") is VerifiedClaimsToken, (
        f"verify_token return type must be VerifiedClaimsToken, got {hints.get('return')}"
    )

    sig_revoke = inspect.signature(AuthenticationPort.revoke_session)
    assert "session_id" in sig_revoke.parameters

    sig_evidence = inspect.signature(AuthenticationPort.get_session_evidence)
    assert "session_id" in sig_evidence.parameters
    assert "as_of" in sig_evidence.parameters
    hints_evidence = get_type_hints(AuthenticationPort.get_session_evidence)
    assert hints_evidence.get("return") is VerifiedSessionEvidence


def test_in_memory_adapter_method_signatures_match_port() -> None:
    """Verify InMemoryAuthAdapter exact signature compliance with AuthenticationPort."""
    for method_name in ["verify_token", "revoke_session", "get_session_evidence"]:
        port_method = getattr(AuthenticationPort, method_name)
        adapter_method = getattr(InMemoryAuthAdapter, method_name)

        port_sig = inspect.signature(port_method)
        adapter_sig = inspect.signature(adapter_method)

        for param_name, param in port_sig.parameters.items():
            if param_name == "self":
                continue
            assert param_name in adapter_sig.parameters, (
                f"Parameter '{param_name}' missing from InMemoryAuthAdapter.{method_name}"
            )


def test_identity_service_contract_and_attributes() -> None:
    """Verify IdentityService dependencies, attributes, and public interface."""
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    assert service.auth_port is adapter
    assert isinstance(service.token_policy, TokenValidationPolicy)
    assert isinstance(service.session_policy, SessionPolicy)

    assert hasattr(service, "authenticate_token")
    assert hasattr(service, "revoke_session")
    assert hasattr(service, "get_session_evidence")


def test_stable_error_codes_contract() -> None:
    """Verify standard domain error classes produce exact canonical error codes."""
    assert AuthenticationError("auth failed").code == "UNAUTHORIZED"
    assert TenancyViolationError("tenancy breach").code == "TENANCY_VIOLATION"
    assert ValidationError("invalid input").code == "VALIDATION_ERROR"
    assert AuthorizationError("access denied").code == "FORBIDDEN"
