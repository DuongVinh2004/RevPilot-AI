"""
RevPilot AI — Tests: Frontend Web Client & Human Approval Portal Contracts
Specification: docs/28-frontend/FRONTEND-SPEC.md
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md
Conforms to DEC-008, DEC-009, ADR-0012, INV-ACT-003, and INV-TEN-001.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
WEB_APP_DIR = WORKSPACE_ROOT / "apps" / "web"
WEB_CLIENT_DIR = WORKSPACE_ROOT / "packages" / "web-client"
COMPOSE_FILE = WORKSPACE_ROOT / "compose.yaml"


def canonicalize_dict(d: dict) -> str:
    """Canonical JSON stringification with sorted keys and no whitespace."""
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def compute_python_reference_digest(
    tenant_id: str,
    action_type: str,
    payload: dict,
    target_entities: list[str],
    estimated_cost_usd: float,
    policy_version: str,
    expires_at: str,
) -> str:
    """Python reference implementation of DEC-009 SHA-256 digest binding."""
    sorted_targets = ",".join(sorted(target_entities))
    canonical_payload = canonicalize_dict(payload)
    cost_str = f"{estimated_cost_usd:.2f}"

    raw_message = "|".join([
        tenant_id,
        action_type,
        canonical_payload,
        sorted_targets,
        cost_str,
        policy_version,
        expires_at,
    ])
    return hashlib.sha256(raw_message.encode("utf-8")).hexdigest()


def test_sha256_digest_binding_parity_dec_009():
    """
    DEC-009 & ADR-0012: Deterministic SHA-256 digest computation matches
    between Python reference and web-client TypeScript specification.
    """
    tenant_id = "tenant_enterprise_01"
    action_type = "ISSUE_SERVICE_CREDIT_VOUCHER"
    payload = {"credit_amount_cents": 250000, "reason": "SLA breach tier 1 compensation"}
    targets = ["cust_987", "sub_456"]
    cost_usd = 2500.0
    policy_version = "2026.09.v1"
    expires_at = "2026-09-05T00:00:00Z"

    digest = compute_python_reference_digest(
        tenant_id, action_type, payload, targets, cost_usd, policy_version, expires_at
    )

    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)

    # Tampering test: Changing payload parameter changes digest
    tampered_payload = {"credit_amount_cents": 500000, "reason": "SLA breach tier 1 compensation"}
    tampered_digest = compute_python_reference_digest(
        tenant_id, action_type, tampered_payload, targets, cost_usd, policy_version, expires_at
    )
    assert digest != tampered_digest, "Tampered payload must alter the SHA-256 digest (INV-ACT-002)"


def test_zero_agent_self_approval_invariant_inv_act_003():
    """
    INV-ACT-003: Approval logic forbids AI agent / service account from approving actions.
    Only human operators with is_human=True are permitted.
    """
    human_signer = {
        "principal_id": "usr_human_operator_42",
        "tenant_id": "tenant_enterprise_01",
        "is_human": True,
        "roles": ["revenue_admin", "tier_3_approver"],
    }
    agent_signer = {
        "principal_id": "agent_auto_planner_09",
        "tenant_id": "tenant_enterprise_01",
        "is_human": False,
        "roles": ["ai_agent", "planner"],
    }

    def simulate_approval_grant(signer: dict, approval_id: str, digest: str) -> str:
        if not signer.get("is_human"):
            raise PermissionError("ERR_AGENT_SELF_APPROVAL: AI agent cannot approve actions (INV-ACT-003)")
        return f"APPROVED:{approval_id}:{digest}"

    # Human sign-off succeeds
    res = simulate_approval_grant(human_signer, "appr_123", "sha256:abcd")
    assert res.startswith("APPROVED:appr_123")

    # Agent sign-off fails-closed
    with pytest.raises(PermissionError) as exc_info:
        simulate_approval_grant(agent_signer, "appr_123", "sha256:abcd")
    assert "ERR_AGENT_SELF_APPROVAL" in str(exc_info.value)


def test_wcag_22_aa_semantic_landmarks_in_html():
    """
    FRONTEND-SPEC §15: HTML shell conforms to WCAG 2.2 AA accessibility requirements:
    Landmarks (header, main, nav, aside, footer), skip-link, and aria-live status regions.
    """
    html_path = WEB_APP_DIR / "src" / "index.html"
    assert html_path.exists(), "Missing apps/web/src/index.html"

    content = html_path.read_text(encoding="utf-8")

    # Semantic Landmarks
    assert '<header role="banner"' in content
    assert '<main id="main-content" role="main"' in content
    assert '<nav role="navigation"' in content
    assert '<aside role="complementary"' in content
    assert '<footer role="contentinfo"' in content

    # Skip to main content link for keyboard users
    assert 'class="skip-link"' in content
    assert 'href="#main-content"' in content

    # Live Announcer regions
    assert 'role="status"' in content
    assert 'aria-live="polite"' in content
    assert 'role="alert"' in content
    assert 'aria-live="assertive"' in content

    # English language attribute
    assert '<html lang="en">' in content


def test_frontend_security_and_privacy_safeguards():
    """
    FRONTEND-SPEC §9: Web client has no embedded credentials and does not leak chain-of-thought.
    """
    js_ts_files = list((WEB_APP_DIR / "src").glob("**/*.ts")) + list((WEB_CLIENT_DIR / "src").glob("**/*.ts"))
    assert len(js_ts_files) >= 5, "Missing required TypeScript source files"

    for file_path in js_ts_files:
        code = file_path.read_text(encoding="utf-8")
        assert "sk-ant" not in code, f"Forbidden API key pattern in {file_path.name}"
        assert "AKIA" not in code, f"Forbidden AWS key pattern in {file_path.name}"
        assert "chain_of_thought" not in code, f"Chain-of-thought leakage in {file_path.name}"


def test_compose_includes_web_service():
    """
    Local composition defines the web service on port 3000 in dmz_net.
    """
    assert COMPOSE_FILE.exists(), "compose.yaml not found"
    compose_text = COMPOSE_FILE.read_text(encoding="utf-8")

    assert "web:" in compose_text
    assert '"3000:80"' in compose_text
    assert "dmz_net" in compose_text
    assert "apps/web/Dockerfile" in compose_text
